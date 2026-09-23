"""Pure, versioned full-history features and immediate-edit event labels.

Targets never enter encode_observation: it accepts only current/prior sources,
nominal verdicts, authentic timestamps and an arm. C0/Cn keys are identical across
arms; H/HS only add ``history:`` keys. The U caller supplies validated donor
history to H, then replaces common Cn keys with the recipient's authentic Cn
features. No learned vocabulary, fitting, I/O, source execution or truncation.

AST family events are subtree-signature changes, not minimal semantic edits.
Ordered-relation changes include typed field/list-position and adjacency changes;
neither representation proves semantic correctness or educational benefit.
All counts/sizes/durations use log1p; proportions/recency means remain bounded.
Bounded memoization evicts/recomputes entries, never drops historical records.
"""
from __future__ import annotations

import ast
from collections import Counter
from functools import lru_cache
import hashlib
import io
import json
import math
import random
import re
import tokenize
from typing import NamedTuple

import numpy as np

ENCODER_VERSION = 'full_history_immediate_edit_v1'
AST_FEATURE_VERSION = (3, 10)
SHUFFLE_SALT = 'zpd-history-action-order-20260923-v1'
NUISANCE_PREFIX = 'nuisance:'
NUISANCE_KEYS = (
    'nuisance:prior_count_log1p', 'nuisance:elapsed_seconds_log1p',
    'nuisance:prior_source_bytes_log1p', 'nuisance:prior_token_count_log1p')
ARMS = ('C0', 'Cn', 'H', 'HS')
FAMILY_EVENTS = (
    'arithmetic_edit', 'comparison_edit', 'boolean_edit', 'branch_edit',
    'loop_edit', 'binding_edit', 'call_edit', 'indexing_container_edit',
    'function_return_edit', 'exception_edit', 'import_edit')
EVENTS = ('exact_repeat', 'token_equivalent_surface_change', 'language_switch',
          'parse_recovery', 'parse_loss', *FAMILY_EVENTS,
          'ordered_ast_relation_change', 'other_lexical_change')
EVENT_INDEX = {name: index for index, name in enumerate(EVENTS)}
FAMILY_NODE_TYPES = {
    'arithmetic_edit': (ast.BinOp, ast.AugAssign),
    'comparison_edit': (ast.Compare,),
    'boolean_edit': (ast.BoolOp,),
    'branch_edit': (ast.If, ast.IfExp, ast.Match, ast.match_case),
    'loop_edit': (ast.For, ast.AsyncFor, ast.While, ast.comprehension),
    'binding_edit': (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.NamedExpr,
                     ast.Delete, ast.Global, ast.Nonlocal),
    'call_edit': (ast.Call,),
    'indexing_container_edit': (ast.Subscript, ast.Slice, ast.Attribute, ast.List,
        ast.Tuple, ast.Set, ast.Dict, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp),
    'function_return_edit': (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda,
                            ast.Return, ast.Yield, ast.YieldFrom),
    'exception_edit': (ast.Try, ast.ExceptHandler, ast.Raise, ast.Assert),
    'import_edit': (ast.Import, ast.ImportFrom),
}
VERDICTS = frozenset({'AC', 'WA', 'CE', 'RE', 'RESOURCE', 'OTHER'})


class _Source(NamedTuple):
    byte_length: int
    raw_tokens: tuple
    python_tokens: tuple | None
    parses: bool
    units: tuple
    families: tuple
    ordered: tuple


def _code_bytes(code):
    if type(code) is not str:
        raise TypeError('available exact UTF-8 source string required')
    try:
        return code.encode('utf-8')
    except UnicodeError as error:
        raise ValueError('source must roundtrip exact UTF-8 bytes') from error


def _language(language):
    if type(language) is not str or not language:
        raise ValueError('explicit nonempty source language required')
    return language


def _verdict(verdict):
    if type(verdict) is not str or not verdict:
        raise ValueError('explicit observed nominal verdict required')
    if verdict in VERDICTS:
        return verdict
    return {'Accepted': 'AC', 'Wrong Answer': 'WA', 'Compile Error': 'CE',
        'Compilation Error': 'CE', 'Runtime Error': 'RE',
        'Time Limit Exceeded': 'RESOURCE', 'Memory Limit Exceeded': 'RESOURCE'}.get(verdict, 'OTHER')


def _python_tokens(data):
    """Lexical Python equivalence retains indentation and logical line breaks.

    Comments/nonlogical NL/format whitespace are ignored. INDENT/DEDENT and
    logical NEWLINE retain their type but not whitespace spelling. ERRORTOKEN
    makes equivalence unavailable; byte fallback is not Python tokenization.
    """
    result = []
    try:
        encoding, _ = tokenize.detect_encoding(io.BytesIO(data).readline)
        # Some Python tokenizer runtimes replace undecodable bytes internally;
        # explicitly forbid that before claiming successful token equivalence.
        data.decode(encoding, errors='strict')
        for token in tokenize.tokenize(io.BytesIO(data).readline):
            if token.type == tokenize.ERRORTOKEN:
                return None
            if token.type in (tokenize.ENCODING, tokenize.ENDMARKER, tokenize.COMMENT, tokenize.NL):
                continue
            text = '' if token.type in (tokenize.INDENT, tokenize.DEDENT, tokenize.NEWLINE) else token.string
            result.append((token.type, text))
    except (tokenize.TokenError, SyntaxError, UnicodeError, LookupError):
        return None
    return tuple(result)


def _local_node(node):
    # Program identifiers/literals are source content, not submission/user IDs.
    fields = []
    for name, value in ast.iter_fields(node):
        if not isinstance(value, (ast.AST, list)):
            fields.append(name+'='+repr(value).encode('utf-8').hex())
        elif isinstance(value, (ast.operator, ast.unaryop, ast.boolop, ast.cmpop, ast.expr_context)):
            fields.append(name+'='+type(value).__name__)
    return type(node).__name__ + ('|'+'|'.join(fields) if fields else '')


def _families(node):
    result = [name for name, types in FAMILY_NODE_TYPES.items() if isinstance(node, types)]
    if isinstance(node, ast.UnaryOp):
        result.append('boolean_edit' if isinstance(node.op, ast.Not) else 'arithmetic_edit')
    return result


def _subtree_fingerprints(tree):
    """Iterative internal comparisons; these hashes never become model features.

    Canonical ordered child/field content is hashed only to count equal AST
    subtrees for event labels, avoiding recursive ast.dump and quadratic strings.
    These are not source identities or learned vocabulary keys.
    """
    result = {}
    pending = [(tree, False)]
    while pending:
        node, visited = pending.pop()
        if not visited:
            pending.append((node, True))
            pending.extend((child, False) for child in ast.iter_child_nodes(node))
            continue
        fields = []
        def atom(value):
            return ['node', result[id(value)]] if isinstance(value, ast.AST) else ['scalar', repr(value)]
        for name, value in ast.iter_fields(node):
            fields.append([name, ['list', [atom(item) for item in value]] if isinstance(value, list) else atom(value)])
        payload = json.dumps([type(node).__name__, fields], ensure_ascii=True, separators=(',', ':')).encode()
        result[id(node)] = hashlib.sha256(payload).hexdigest()
    return result


@lru_cache(maxsize=4096)
def _source(code, language):
    data = _code_bytes(code)
    _language(language)
    raw = tuple(re.findall(rb'[A-Za-z_][A-Za-z_0-9]*|[0-9]+|[^\s]', data))
    units = Counter('token:'+token.hex() for token in raw)
    python_tokens = _python_tokens(data) if language == 'Python' else None
    tree = None
    if language == 'Python':
        try:
            tree = ast.parse(data, mode='exec', feature_version=AST_FEATURE_VERSION)
        except (SyntaxError, ValueError, UnicodeError, LookupError, RecursionError):
            pass
    family_counts = {name: Counter() for name in FAMILY_EVENTS}
    ordered = Counter()
    if tree is None:
        # Complete byte-token order, including CR/LF, remains available even
        # when a language is non-Python or Python's tokenizer/parser fails.
        fallback = ['BOS'] + [token.hex() for token in re.findall(
            rb'[A-Za-z_][A-Za-z_0-9]*|[0-9]+|[\r\n]|[^\s]', data)] + ['EOS']
        for length in (2, 3):
            units.update('fallback:'+str(length)+':'+':'.join(fallback[i:i+length])
                         for i in range(len(fallback)-length+1))
    else:
        subtree_fingerprints = _subtree_fingerprints(tree)
        for node in ast.walk(tree):
            parent = type(node).__name__
            units['ast:node:'+_local_node(node)] += 1
            families = _families(node)
            if families:
                signature = subtree_fingerprints[id(node)]
                for family in families:
                    family_counts[family][signature] += 1
            for field, value in ast.iter_fields(node):
                if isinstance(value, ast.AST):
                    ordered['field:'+parent+'.'+field+'=>'+_local_node(value)] += 1
                elif isinstance(value, list):
                    children = [(index, child) for index, child in enumerate(value) if isinstance(child, ast.AST)]
                    for index, child in children:
                        ordered['field:'+parent+'.'+field+'['+str(index)+']=>'+_local_node(child)] += 1
                    for (_, left), (_, right) in zip(children, children[1:]):
                        ordered['adjacent:'+parent+'.'+field+':'+_local_node(left)+'=>'+_local_node(right)] += 1
        units.update({'ast:ordered:'+name: count for name, count in ordered.items()})
    return _Source(len(data), raw, python_tokens, tree is not None,
        tuple(sorted(units.items())),
        tuple(tuple(sorted(family_counts[name].items())) for name in FAMILY_EVENTS),
        tuple(sorted(ordered.items())))


def encode_edit(current_code: str, next_code: str, current_language: str = 'Python',
                next_language: str = 'Python') -> tuple[np.ndarray, np.ndarray]:
    """Fixed binary immediate-action labels and explicit applicability masks.

    Exact repeat and language switch always apply to available sources. Token-
    equivalent surface change requires two successful Python tokenizations.
    Parse recovery/loss require two declared-Python endpoints (not two parses).
    AST family/relation labels require both parses. Other lexical change is
    residual/unclassified changed token sequence: Python tokens when available,
    otherwise complete raw-byte lexical tokens. It is not a semantic claim.
    Missing sources must be handled as all-unavailable by the caller, not '' here.
    """
    before, after = _source(current_code, current_language), _source(next_code, next_language)
    values = np.zeros(len(EVENTS), dtype=float)
    mask = np.zeros(len(EVENTS), dtype=bool)
    def set_event(name, value, applicable=True):
        index = EVENT_INDEX[name]
        mask[index] = applicable
        values[index] = float(bool(value)) if applicable else 0.
    same_python = current_language == next_language == 'Python'
    token_available = same_python and before.python_tokens is not None and after.python_tokens is not None
    both_parse = same_python and before.parses and after.parses
    set_event('exact_repeat', current_code == next_code)
    set_event('language_switch', current_language != next_language)
    set_event('token_equivalent_surface_change', current_code != next_code
              and token_available and before.python_tokens == after.python_tokens, token_available)
    set_event('parse_recovery', not before.parses and after.parses, same_python)
    set_event('parse_loss', before.parses and not after.parses, same_python)
    for index, family in enumerate(FAMILY_EVENTS):
        set_event(family, before.families[index] != after.families[index], both_parse)
    set_event('ordered_ast_relation_change', before.ordered != after.ordered, both_parse)
    lexical_changed = (before.python_tokens != after.python_tokens if token_available
                       else before.raw_tokens != after.raw_tokens)
    classified = any(values[EVENT_INDEX[name]] for name in (*FAMILY_EVENTS, 'ordered_ast_relation_change'))
    set_event('other_lexical_change', lexical_changed and not classified)
    return values, mask


@lru_cache(maxsize=8192)
def _transition(before_code, after_code, before_language, after_language):
    before, after = _source(before_code, before_language), _source(after_code, after_language)
    old, new = Counter(dict(before.units)), Counter(dict(after.units))
    delta = tuple(sorted((key, new[key]-old[key]) for key in old.keys() | new.keys() if new[key] != old[key]))
    values, mask = encode_edit(before_code, after_code, before_language, after_language)
    return delta, tuple(values), tuple(mask)


def permutation_indices(length, shuffle_key):
    """Fixed counterfactual prior permutation; identity draws are not resampled."""
    if type(length) is not int or length < 0 or type(shuffle_key) is not str:
        raise ValueError('nonnegative length and string shuffle key required')
    seed = int.from_bytes(hashlib.sha256((SHUFFLE_SALT+'|'+shuffle_key).encode()).digest(), 'big')
    indices = list(range(length))
    random.Random(seed).shuffle(indices)
    return tuple(indices)


def describe_permutation(history, shuffle_key):
    indices = permutation_indices(len(history), shuffle_key)
    return dict(indices=indices, identity=indices == tuple(range(len(history))), records=len(history))


def _validate_observation(current_code, current_verdict, history, current_timestamp, arm):
    _code_bytes(current_code)
    _verdict(current_verdict)
    if arm not in ARMS or type(history) is not list:
        raise ValueError('C0/Cn/H/HS and explicit full prior-history list required')
    times = []
    for row in history:
        if type(row) is not dict or set(row) != {'code', 'verdict', 'timestamp', 'language'}:
            raise ValueError('strict observed-only history schema required; no target/ID fields')
        _code_bytes(row['code'])
        _verdict(row['verdict'])
        _language(row['language'])
        times.append(row['timestamp'])
    times.append(current_timestamp)
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in times):
        raise ValueError('finite authentic timestamps required')
    if any(left >= right for left, right in zip(times, times[1:])):
        raise ValueError('strict authentic past/current chronology required before shuffling')


def _base_features(current_code, current_verdict):
    source = _source(current_code, 'Python')
    result = {'current:verdict:'+_verdict(current_verdict): 1.,
        'current:byte_length_log1p': math.log1p(source.byte_length),
        'current:token_count_log1p': math.log1p(len(source.raw_tokens)),
        'current:parse_success': float(source.parses),
        'current:parse_fallback': float(not source.parses),
        'current:tokenization_available': float(source.python_tokens is not None),
        'current:tokenization_unavailable': float(source.python_tokens is None)}
    result.update({'current:unit:'+name: math.log1p(count) for name, count in source.units})
    return result


def encode_observation(current_code: str, current_verdict: str, history: list[dict],
                       current_timestamp: float, arm: str, shuffle_key: str = '') -> dict[str, float]:
    """Current-only/shared-nuisance/full-authentic/order-counterfactual features.

    Every prior source and adjacent transition through anchored current is used.
    Recency weights are reciprocal *positions*, never counterfactual timestamps.
    HS preserves authentic elapsed-time nuisance and all original record bytes.
    No timestamp, shuffle key, source hash or observation identity is a key.
    """
    _validate_observation(current_code, current_verdict, history, current_timestamp, arm)
    if type(shuffle_key) is not str:
        raise ValueError('string shuffle key required')
    result = _base_features(current_code, current_verdict)
    if arm == 'C0':
        return result
    length = len(history)
    elapsed = current_timestamp-history[0]['timestamp'] if history else 0.
    if not math.isfinite(elapsed):
        raise ValueError('non-finite observed elapsed duration')
    prior_bytes = [_code_bytes(row['code']) for row in history]
    nuisance = (length, elapsed, sum(map(len, prior_bytes)), sum(len(re.findall(
        rb'[A-Za-z_][A-Za-z_0-9]*|[0-9]+|[^\s]', code)) for code in prior_bytes))
    result.update({key: math.log1p(value) for key, value in zip(NUISANCE_KEYS, nuisance)})
    if arm == 'Cn':
        return result
    prior = ([history[index] for index in permutation_indices(length, shuffle_key)] if arm == 'HS' else history)
    current = dict(code=current_code, verdict=current_verdict, timestamp=current_timestamp, language='Python')
    sequence = [*prior, current]
    verdicts = [_verdict(row['verdict']) for row in sequence]
    prior_count = Counter(verdicts[:-1])
    denominator = max(1, length)
    for verdict in sorted(VERDICTS):
        result['history:verdict_fraction:'+verdict] = prior_count[verdict]/denominator
    result['history:non_python_fraction'] = sum(row['language'] != 'Python' for row in prior)/denominator
    result['history:parse_unavailable_fraction'] = sum(not _source(row['code'], row['language']).parses for row in prior)/denominator
    result['history:tokenization_unavailable_fraction'] = sum(_source(row['code'], row['language']).python_tokens is None for row in prior)/denominator
    result['history:current_verdict_prior_fraction'] = prior_count[verdicts[-1]]/denominator
    if prior:
        result['history:last_verdict:'+verdicts[-2]] = 1.
    matches = [index for index, row in enumerate(prior) if row['code'] == current_code]
    result['history:current_source_prior_fraction'] = len(matches)/denominator
    result['history:current_seen_before'] = float(bool(matches))
    result['history:current_recurrence_distance_inverse'] = 1/(length-matches[-1]) if matches else 0.
    source_run = verdict_run = 0
    for row in reversed(prior):
        if row['code'] != current_code:
            break
        source_run += 1
    for verdict in reversed(verdicts[:-1]):
        if verdict != verdicts[-1]:
            break
        verdict_run += 1
    result['history:current_source_trailing_repeat_log1p'] = math.log1p(source_run)
    result['history:current_verdict_trailing_repeat_log1p'] = math.log1p(verdict_run)
    result['history:distinct_source_fraction'] = len({row['code'] for row in sequence})/len(sequence)
    weights = [1/(length-index) for index in range(length)]
    weight_sum = sum(weights) or 1.
    observed = np.zeros(len(EVENTS)); positive = np.zeros(len(EVENTS))
    recency_observed = np.zeros(len(EVENTS)); recency_positive = np.zeros(len(EVENTS))
    repeated = reversed_edits = 0
    patterns, seen_deltas = Counter(), set()
    for index, (before, after) in enumerate(zip(sequence, sequence[1:])):
        delta, values, mask = _transition(before['code'], after['code'], before['language'], after['language'])
        weight = weights[index]/weight_sum
        pair = verdicts[index]+'=>'+verdicts[index+1]
        for prefix, amount in (('history:verdict_transition_fraction:', 1/denominator),
                               ('history:recency_verdict_transition_fraction:', weight)):
            result[prefix+pair] = result.get(prefix+pair, 0.)+amount
        value_array, mask_array = np.asarray(values), np.asarray(mask, dtype=float)
        observed += mask_array; positive += value_array*mask_array
        recency_observed += weight*mask_array; recency_positive += weight*value_array*mask_array
        pattern = (delta, values, mask)
        repeated += patterns[pattern] > 0
        if delta and tuple((name, -value) for name, value in delta) in seen_deltas:
            reversed_edits += 1
        patterns[pattern] += 1
        seen_deltas.add(delta)
        for name, change in delta:
            key = ('add:' if change > 0 else 'remove:')+name
            size = math.log1p(abs(change))
            mean_key, weighted_key = 'history:mean_delta:'+key, 'history:recency_delta:'+key
            result[mean_key] = result.get(mean_key, 0.)+size/denominator
            result[weighted_key] = result.get(weighted_key, 0.)+weight*size
            if index == length-1:
                result['history:last_delta:'+key] = size
    result['history:repeated_transition_fraction'] = repeated/denominator
    result['history:reverse_edit_fraction'] = reversed_edits/denominator
    for index, name in enumerate(EVENTS):
        result['history:event_observed_fraction:'+name] = float(observed[index]/denominator)
        result['history:event_frequency:'+name] = float(positive[index]/observed[index]) if observed[index] else 0.
        result['history:recency_event_frequency:'+name] = float(recency_positive[index]/recency_observed[index]) if recency_observed[index] else 0.
    if not all(type(key) is str and type(value) is float and math.isfinite(value) for key, value in result.items()):
        raise ValueError('encoder produced non-finite/non-float features')
    return result
