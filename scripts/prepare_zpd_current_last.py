"""Pinned all320 order-only layout diagnostic; no generation or execution.

Move only the top-level current_program member to the end of every user JSON.
Member text is copied, never reserialized, so nested text/order/escapes survive.
The complete original input contract remains intact except the user text and its
prompt hashes. New layout provenance belongs to the external preparation seal.
This is exposed development diagnosis, not an established method improvement.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path

VERSION = 'current_program_last_preparation_v1'
LAYOUT_VARIANT = 'current_program_last_v1'
BASE = Path('archive/zpd-transition-generation-20261012/prepared-v1')
PINS = {
    'inputs.json': 'd8b981633a7180828f35b9c7ad9b6a9b1beefdd07fad702e19b9d1cde692e8fd',
    'manifest.json': 'd23757d003573b4d77ba679f9c3c614a0a3926b33b9289de932bbf54651a9a07',
    'COMPLETE.json': 'fbcfe0ed515e0792fa5d7439e5869ed2025327dd7ca899eff9f9994c6f874ab7',
}
HASH_CONTRACT_SOURCE = 'scripts/zpd_public_transition_prompt.py'
HASH_CONTRACT_SHA256 = '722e8d2c6a9ecd1c1f91d4c116323bf1e820e08696edcd3a6e14cebd71b2633d'
SOURCE_FILES = ('scripts/prepare_zpd_current_last.py', 'tests/test_prepare_zpd_current_last.py')
ARMS = ('C', 'H', 'HS', 'U')
COUNTS = dict(recipients=320, users=320, problems=23, folds=5, prompts=1280, attempts=2560)


def require(value, message):
    if not value:
        raise ValueError(message)


def encoded(value):
    """Exact original prompt hash contract: compact sorted ASCII, no newline."""
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'duplicate JSON member: ' + key)
        result[key] = value
    return result


def _constant(value):
    raise ValueError('nonfinite JSON constant: ' + value)


DECODER = json.JSONDecoder(object_pairs_hook=_pairs, parse_constant=_constant)


def top_level_members(raw):
    """Return each top-level key and its exact unmodified JSON member text."""
    require(type(raw) is str and raw.startswith('{') and raw.endswith('}'),
            'exact JSON object text required')
    body = DECODER.decode(raw)
    require(type(body) is dict and body, 'nonempty JSON object required')
    def skip(index):
        while index < len(raw) and raw[index] in ' \t\r\n':
            index += 1
        return index
    result, start = [], 1
    while True:
        key, end = DECODER.raw_decode(raw, skip(start))
        colon = skip(end)
        require(type(key) is str and raw[colon] == ':', 'JSON member key required')
        _, end = DECODER.raw_decode(raw, skip(colon + 1))
        end = skip(end)
        require(raw[end] in ',}', 'JSON member delimiter required')
        result.append((key, raw[start:end]))
        if raw[end] == '}':
            require(end == len(raw) - 1, 'trailing JSON content forbidden')
            break
        start = end + 1
    require([k for k, _ in result] == list(body), 'exact top-level member coverage required')
    return result


def relocate_current_program(raw):
    members = top_level_members(raw)
    require('current_program' in dict(members), 'current_program member required')
    require(type(DECODER.decode(raw)['current_program']) is str, 'current program text required')
    ordered = [(k, v) for k, v in members if k != 'current_program']
    ordered += [(k, v) for k, v in members if k == 'current_program']
    result = '{' + ','.join(v for _, v in ordered) + '}'
    require(len(result) == len(raw) and DECODER.decode(result) == DECODER.decode(raw),
            'layout-only relocation changed information')
    return result


def transform(inputs):
    """Pure complete-cohort conversion; never mutate the caller's input."""
    require(inputs['counts'] == COUNTS and inputs['excluded_recipients'] == 0,
            'exact original all320 counts required; no exclusions')
    recipients = {r['example_id']: r for r in inputs['recipients']}
    require(len(recipients) == len(inputs['recipients']) == 320, 'unique all320 recipients required')
    prompts = {p['prompt_id']: p for p in inputs['prompts']}
    expected = {eid + ':' + arm for eid in recipients for arm in ARMS}
    require(len(prompts) == len(inputs['prompts']) == 1280 and set(prompts) == expected,
            'complete unique four-arm prompt population required')
    require(len(inputs['attempts']) == 2560
            and len({a['attempt_id'] for a in inputs['attempts']}) == 2560,
            'complete unique attempt population required')
    draws = Counter()
    for attempt in inputs['attempts']:
        p = prompts[attempt['prompt_id']]
        eid, arm, draw = attempt['example_id'], attempt['arm'], attempt['draw_index']
        require(type(draw) is int and draw in (0, 1) and arm in ARMS and eid in recipients,
                'valid frozen attempt slot required')
        require(p['example_id'] == eid and p['arm'] == arm and p['bank_id'] == attempt['bank_id']
                and p['seeds'][draw] == attempt['seed'] and p['prompt_sha256'] == attempt['prompt_sha256']
                and attempt['problem_id'] == recipients[eid]['problem_id']
                and attempt['fold'] == recipients[eid]['fold'], 'attempt prompt binding differs')
        draws[eid, arm, draw] += 1
    require(draws == Counter((eid, arm, draw) for eid in recipients for arm in ARMS for draw in (0, 1)),
            'exact two draws per arm required')
    result = deepcopy(inputs)
    new_hashes = {}
    for p in result['prompts']:
        eid, arm = p['example_id'], p['arm']
        require(eid in recipients and arm in ARMS and p['prompt_id'] == eid + ':' + arm,
                'prompt identity differs')
        row, messages, binding = recipients[eid], p['messages'], p['binding']
        require(len(messages) == 2 and messages[0]['role'] == 'system' and messages[1]['role'] == 'user'
                and messages[1]['content'] == p['user_json']
                and sha(encoded(messages)) == p['prompt_sha256'], 'original message/hash binding differs')
        require(binding['arm'] == arm and binding['current_submission_id'] == eid
                and binding['current_source_sha256'] == row['current_source_sha256']
                and p['bank_id'] == row['bank_id']
                and sha(row['current_source'].encode('utf-8')) == row['current_source_sha256']
                and DECODER.decode(p['user_json'])['current_program'] == row['current_source'],
                'original current-source binding differs')
        relocated = relocate_current_program(p['user_json'])
        require(relocated != p['user_json'], 'original current_program must not already be last')
        p['user_json'] = messages[1]['content'] = relocated
        p['prompt_sha256'] = sha(encoded(messages))
        new_hashes[p['prompt_id']] = p['prompt_sha256']
    for attempt in result['attempts']:
        attempt['prompt_sha256'] = new_hashes[attempt['prompt_id']]
    return result


def _read_pinned(path, pin):
    require(path.resolve(strict=True) == path and path.is_file(), 'canonical regular artifact required')
    raw = path.read_bytes()
    require(sha(raw) == pin, 'original artifact pin differs: ' + str(path))
    return DECODER.decode(raw.decode('utf-8'))


def load_original(project):
    project = Path(project).resolve(strict=True)
    values = {name: _read_pinned(project / BASE / name, pin) for name, pin in PINS.items()}
    complete = values['COMPLETE.json']
    require(complete['status'] == 'complete' and complete['counts'] == COUNTS
            and complete['files_sha256'] == {n: p for n, p in PINS.items() if n != 'COMPLETE.json'},
            'original preparation seal differs')
    require(sha((project / HASH_CONTRACT_SOURCE).read_bytes()) == HASH_CONTRACT_SHA256,
            'original prompt hash-contract source differs')
    return values['inputs.json']


def prepare(project, output):
    project, output = Path(project).resolve(strict=True), Path(output).absolute()
    require(output.resolve() == output and not output.exists() and not output.is_symlink(),
            'new canonical output required; no overwrite or resume')
    original = load_original(project)
    source_pins = {n: sha((project / n).read_bytes()) for n in SOURCE_FILES}
    inputs = transform(original)
    changes = [dict(prompt_id=old['prompt_id'], original_sha256=old['prompt_sha256'],
                    current_last_sha256=new['prompt_sha256'])
               for old, new in zip(original['prompts'], inputs['prompts'], strict=True)]
    facts = dict(kind=VERSION, layout_variant=LAYOUT_VARIANT, counts=COUNTS,
        original_inputs_sha256=PINS['inputs.json'],
        input_sha256={str(BASE / n): pin for n, pin in PINS.items()},
        source_sha256=source_pins, hash_contract_source_sha256={HASH_CONTRACT_SOURCE: HASH_CONTRACT_SHA256},
        changed_prompts=1280, updated_attempt_hashes=2560, excluded_recipients=0,
        history_truncated=False, tokenizer_counts_measured=False, tokenization_required_before_generation=True,
        generation_performed=False, execution_performed=False, fitting_performed=False,
        private_testcases_opened=False, model_promotion=False, method_improvement_established=False,
        cohort_status='exposed_adaptive_development_not_untouched_confirmation')
    manifest = dict(facts, transformation='relocate_only_top_level_current_program_to_last',
                    unchanged='all_other_input_values_order_and_exact_member_text', prompt_hash_changes=changes)
    artifacts = {'inputs.json': encoded(inputs) + b'\n', 'manifest.json': encoded(manifest) + b'\n'}
    load_original(project)
    require(all(sha((project / n).read_bytes()) == pin for n, pin in source_pins.items()), 'source changed')
    output.mkdir(parents=True, exist_ok=False)
    def write(name, raw):
        with (output / name).open('xb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    for name, raw in artifacts.items():
        write(name, raw)
    load_original(project)
    require(all(sha((project / n).read_bytes()) == pin for n, pin in source_pins.items()), 'source changed')
    complete = dict(facts, status='complete', files_sha256={n: sha(raw) for n, raw in artifacts.items()})
    write('COMPLETE.json', encoded(complete) + b'\n')
    return complete


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.project, args.output), sort_keys=True))


if __name__ == '__main__':
    main()
