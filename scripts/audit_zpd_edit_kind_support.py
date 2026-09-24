"""Full320 source-only feasibility for fixed four-kind overlap; never fits.

Use authenticated current/prior/candidate source bytes and existing sample
moments only. The unchanged empirical predictions and repair labels are not read.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from itertools import combinations
import json
import math
from pathlib import Path
import tarfile

from scripts.diagnose_zpd_history_support import COMPLETE_SHA, FEATURE_SHA

SOURCE_TAR_SHA = '7dc5ed116d8e71cf0d85d584cee0e9d0fadac091871bab51a4676fa51e773d6e'
PREFIX = 'outputs/zpd-statement-sample-feedback-20260924/'
TAU = 1e-12  # Descriptive feature distinction only; no selection/gate change.


def checked(path, pin):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != pin:
        raise ValueError('input SHA differs: ' + str(path))
    return raw


def moment_vectors(similarities, moment):
    """Independent direct formula, weight/direction/kind/state flatten order."""
    eligible = [i for i, ok in enumerate(moment['mask']) if ok]
    current = moment['current_counts']
    q0 = [v / sum(current) for v in current] if current else [0.] * 4
    g, h, jm = [], [], []
    for w in moment['weights']:
        for direction in range(2):
            for kind in range(4):
                mean = math.fsum(w[i] * similarities[i][direction][kind] for i in eligible)
                for state in range(4):
                    delta = {i: (moment['paired_counts'][i][state] - current[state]) / sum(current)
                             for i in eligible}
                    g.append(mean * q0[state])
                    h.append(math.fsum(w[i] * similarities[i][direction][kind] * delta[i]
                                      for i in eligible))
                    jm.append(mean * math.fsum(w[i] * delta[i] for i in eligible))
    scale = math.sqrt(12.)
    return tuple(v / scale for v in g + h), tuple(v / scale for v in g + jm)


def projected(values):
    return tuple(math.fsum(values[block * 64 + w * 32 + d * 16 + k * 4 + state]
                           for k in range(4))
                 for block in range(2) for w in range(2) for d in range(2) for state in range(4))


def maxdiff(a, b):
    return max(abs(x-y) for x, y in zip(a, b, strict=True))


def audit(root, source_tar):
    checked(source_tar, SOURCE_TAR_SHA)
    source_names = ('scripts/zpd_repair_directed_history.py', 'scripts/zpd_history_action_encoder.py')
    with tarfile.open(source_tar) as tar:
        for name in source_names:
            if (root/name).read_bytes() != tar.extractfile(name).read():
                raise ValueError('frozen source differs: ' + name)
    from scripts import zpd_repair_directed_history as directed
    from scripts import zpd_edit_kind_history as kinds
    complete = json.loads(checked(root/PREFIX/'readiness-v1/COMPLETE.json', COMPLETE_SHA))
    manifest = json.loads(checked(root/PREFIX/'readiness-v1/manifest.json',
                                  complete['files_sha256']['manifest.json']))
    features = [json.loads(line) for line in checked(root/PREFIX/'readiness-v1/features.jsonl', FEATURE_SHA).splitlines()]
    pins = manifest['input_sha256']
    consumed = {}

    def read(relative):
        consumed[relative] = pins[relative]
        return checked(root/relative, pins[relative])

    roster = json.loads(read(PREFIX+'prepared-v1/roster.json'))
    sources = {s['submission_id']: s for s in roster['sources']}
    recipients = {r['example_id']: r for r in roster['recipients']}
    wanted = {r['spec']['bank_id'] for r in features}
    banks = {}
    for path in ('outputs/zpd-repair-development-20260918/run-v1/generation/banks.jsonl',
                 'outputs/zpd-repair-risk-development-20260923/run-v1/banks.jsonl'):
        for line in read(path).splitlines():
            bank = json.loads(line)
            if bank['bank_id'] not in wanted:
                continue  # Never analyze original-valid32 candidate contents.
            if bank['bank_id'] in banks:
                raise ValueError('duplicate candidate bank')
            banks[bank['bank_id']] = bank
    if len(features) != len(recipients) or len(features) != 320 or set(banks) != wanted:
        raise ValueError('full320 cohort differs')
    signatures = {}

    def signature(source):
        raw = bytes.fromhex(source['source_hex'])
        if hashlib.sha256(raw).hexdigest() != source['source_sha256']:
            raise ValueError('observed source bytes differ')
        key = (source['source_sha256'], source['language'])
        if key not in signatures:
            signatures[key] = directed.signature(raw.decode('utf-8'), source['language'])
        return signatures[key]

    profiles = []
    projection_error = 0.
    for row in features:
        spec = row['spec']; recipient = recipients[spec['example_id']]
        if any(recipient[k] != spec[k] for k in ('bank_id', 'problem_id', 'fold')):
            raise ValueError('recipient identity differs')
        bank = banks[spec['bank_id']]
        current_source = sources[recipient['current_source_id']]
        current = signature(current_source)
        if bank['current_source'].encode() != bytes.fromhex(current_source['source_hex']):
            raise ValueError('bank/current source differs')
        sequence = [signature(sources[s]) for s in recipient['prior_source_ids']] + [current]
        history = [directed.delta_signatures(a, b) for a, b in zip(sequence, sequence[1:])]
        codes = [bank['current_source']] + [a['source'] for a in bank['attempts'] if a['status'] == 'success']
        candidates = {hashlib.sha256(code.encode()).hexdigest(): code for code in codes}
        if set(candidates) != set(row['candidate_ids']):
            raise ValueError('candidate source coverage differs')
        refined, product = [], []
        old = [c['arms']['H'] for c in row['candidates']]
        for cid, c in zip(row['candidate_ids'], row['candidates'], strict=True):
            delta = directed.delta_signatures(current, directed.signature(candidates[cid]))
            moment = c['moments']['H']
            if len(history) != len(moment['mask']):
                raise ValueError('full history length differs')
            sims = []
            for i, past in enumerate(history):
                matched = kinds.match_kinds(delta, past)
                sims.append((matched.same, matched.reverse))
                pooled = directed.match(delta, past)
                if (maxdiff((pooled.same, pooled.reverse), moment['similarities'][i]) > TAU
                        or moment['mask'][i] and not matched.available):
                    raise ValueError('old similarity/availability differs')
            h, jm = moment_vectors(sims, moment)
            error = max(maxdiff(projected(h), c['arms']['H']),
                        maxdiff(projected(jm), c['arms']['Jm']))
            projection_error = max(projection_error, error)
            if error > TAU:
                raise ValueError('kind marginalization differs from old moments')
            refined.append(h); product.append(jm)
        pairs = list(combinations(range(len(old)), 2))
        split = sum(maxdiff(old[a], old[b]) == 0 and maxdiff(refined[a], refined[b]) > TAU for a, b in pairs)
        old_covariance = max(maxdiff(c['arms']['H'], c['arms']['Jm']) for c in row['candidates']) > TAU
        new_covariance = max(maxdiff(h, jm) for h, jm in zip(refined, product, strict=True)) > TAU
        profiles.append(dict(example_id=spec['example_id'], fold=spec['fold'], problem_id=spec['problem_id'],
                             candidates=len(old), pairs=len(pairs), old_equal_pairs_split=split,
                             old_covariance=old_covariance, kind_covariance=new_covariance))
    if sum(p['candidates'] for p in profiles) != 2544:
        raise ValueError('full2544 differs')
    def summarize(rows):
        return dict(banks=len(rows), candidates=sum(r['candidates'] for r in rows),
                    pairs=sum(r['pairs'] for r in rows), split_pairs=sum(r['old_equal_pairs_split'] for r in rows),
                    banks_with_split=sum(r['old_equal_pairs_split'] > 0 for r in rows),
                    old_covariance=sum(r['old_covariance'] for r in rows),
                    kind_covariance=sum(r['kind_covariance'] for r in rows),
                    newly_covariant=sum(r['kind_covariance'] and not r['old_covariance'] for r in rows),
                    lost_covariance=sum(r['old_covariance'] and not r['kind_covariance'] for r in rows))
    return dict(kind='edit_kind_source_only_support_v1', fitting=False, repair_labels_accessed=False,
                overall=summarize(profiles), folds={str(f): summarize([p for p in profiles if p['fold'] == f]) for f in range(5)},
                maximum_old_projection_error=projection_error, diagnostic_tau=TAU,
                consumed_input_sha256=consumed, readiness_complete_sha256=COMPLETE_SHA,
                profiles=profiles,
                source_sha256={n: hashlib.sha256((root/n).read_bytes()).hexdigest() for n in
                    (*source_names, 'scripts/zpd_edit_kind_history.py', 'scripts/audit_zpd_edit_kind_support.py')})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--source-tar', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.root, args.source_tar)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('profiles', 'consumed_input_sha256', 'source_sha256')}, sort_keys=True))


if __name__ == '__main__':
    main()
