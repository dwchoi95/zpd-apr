"""Fixed edit/copy-balanced CE; targets, prompts, roster and EOS stay unchanged."""
from __future__ import annotations

from difflib import SequenceMatcher
from statistics import median

from scripts import train_zpd_paired_history as training

VERSION = 'edit_copy_balanced_ce_v1'


def contract():
    return dict(version=VERSION, alignment='SequenceMatcher_autojunk_false_on_token_ids',
        current_normalization='none', target_normalization='rstrip',
        deletion='next_target_token_or_last_token', code_edit_mass=0.5,
        code_copy_mass=0.5, degenerate='uniform_if_either_stratum_empty',
        eos_weight=1.0, prompt_weight=0.0, total_mass='code_tokens_plus_one_eos',
        hyperparameter_search=False)


def edit_indices(current, target):
    changed = set()
    for tag, _, _, start, end in SequenceMatcher(None, current, target, autojunk=False).get_opcodes():
        if tag == 'equal':
            continue
        changed.update(range(start, end))
        if start == end and target:
            changed.add(min(start, len(target) - 1))
    return sorted(changed)


def target_weights(code_tokens, changed):
    training.require(type(code_tokens) is int and code_tokens >= 0
        and type(changed) is list and all(type(i) is int and 0 <= i < code_tokens for i in changed)
        and changed == sorted(set(changed)), 'invalid edit alignment')
    count = len(changed)
    if count in (0, code_tokens):
        return [1.0] * (code_tokens + 1)
    edited = set(changed)
    return [code_tokens / (2 * (count if i in edited else code_tokens - count))
            for i in range(code_tokens)] + [1.0]


def expected_weights(report, pin):
    training.require(report.get('objective') == contract() and report.get('edit_token_weight') is None,
                     'fixed balanced objective required')
    weights = target_weights(pin['target_tokens'] - 1, pin['edit_indices'])
    training.require(training.sha(training.encoded(weights)) == pin['target_loss_weights_sha256'],
                     'balanced target weight pin differs')
    return weights


def paired_preflight(c_records, h_records, tokenizer, **caps):
    result = training.paired_preflight(c_records, h_records, tokenizer, **caps)
    report = result['report']
    report.update(objective=contract(), edit_token_weight=None)
    total = edits = zero = all_edit = 0
    fractions = []
    for index, (record, pin) in enumerate(zip(c_records, report['per_example'], strict=True)):
        target = result['encoded']['C'][index]['input_ids'][pin['arms']['C']['prompt_tokens']:-1]
        changed = edit_indices(training._tokens(tokenizer, record['current_code']), target)
        weights = target_weights(len(target), changed)
        pin.update(edit_indices=changed, target_loss_weights_sha256=training.sha(training.encoded(weights)))
        for arm in training.ARMS:
            result['encoded'][arm][index]['loss_weights'] = [0.0] * pin['arms'][arm]['prompt_tokens'] + weights
        total += len(target); edits += len(changed)
        zero += not changed; all_edit += bool(target) and len(changed) == len(target)
        fractions.append(len(changed) / len(target) if target else 0.0)
    report['objective_audit'] = dict(examples=len(c_records), code_tokens=total,
        changed_or_deletion_boundary_tokens=edits, copy_mass_fraction=1-edits/total if total else None,
        median_edit_fraction=median(fractions), zero_edit=zero, all_edit=all_edit)
    report['encoded_sha256'] = {a: training.sha(training.encoded(result['encoded'][a])) for a in training.ARMS}
    training.validate_preflight(result)
    return result
