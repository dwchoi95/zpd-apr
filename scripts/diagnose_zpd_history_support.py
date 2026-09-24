"""Read-only, label-free support accounting for the sealed all320 readiness.

Categories describe covariance opportunity, not repair efficacy or causality.
No experiment modules, fitting, candidate execution, or repair labels are read.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

COMPLETE_SHA = 'e9ed6a38c44f56578ea85e02e5220c68c68906aff767abaa047a318f3259afad'
FEATURE_SHA = '96d0926f84b4082ba5a1a4d386ca1ff470c2d431a9ada17f4d656e6f5a9490d6'
CATEGORIES = ('zero_eligible', 'singleton', 'constant_feedback',
              'constant_similarity', 'potential_covariance')


def classify(moment):
    mask = moment['mask']
    paired, similarities = moment['paired_counts'], moment['similarities']
    if (not all(type(v) is bool for v in mask)
            or len(mask) != len(paired) or len(mask) != len(similarities)):
        raise ValueError('invalid full-position moment arrays')
    eligible = [i for i, value in enumerate(mask) if value]
    if any(paired[i] is None for i in eligible):
        raise ValueError('eligible transition lacks feedback')
    if not eligible:
        return CATEGORIES[0]
    if len(eligible) == 1:
        return CATEGORIES[1]
    if len({tuple(paired[i]) for i in eligible}) == 1:
        return CATEGORIES[2]
    if len({tuple(similarities[i]) for i in eligible}) == 1:
        return CATEGORIES[3]
    return CATEGORIES[4]


def profile(row):
    candidates = row['candidates']
    ids = row['candidate_ids']
    if not candidates or len(ids) != len(candidates) or len(set(ids)) != len(ids):
        raise ValueError('candidate coverage differs')
    moments = [c['moments']['H'] for c in candidates]
    if len({len(m['mask']) for m in moments}) != 1:
        raise ValueError('inconsistent full history positions')
    categories = [classify(m) for m in moments]
    # Priority partition: retain every candidate, including no-op/unavailable.
    category = max(categories, key=CATEGORIES.index)
    current = moments[0]['current_counts']
    if any(m['current_counts'] != current for m in moments):
        raise ValueError('candidate-dependent current feedback')
    if current is None:
        current_state = 'unavailable'
    else:
        if len(current) != 4 or current[1:3] != [0, 0] or sum(current) <= 0:
            raise ValueError('invalid current diagonal counts')
        current_state = ('mixed' if current[0] and current[3] else
                         'allpass' if current[3] else 'allfail')
    differences = []
    for c in candidates:
        h, jm = c['arms']['H'], c['arms']['Jm']
        if len(h) != 32 or len(jm) != 32:
            raise ValueError('expected accepted32 dimensions')
        differences.extend(abs(a - b) for a, b in zip(h, jm, strict=True))
    size = len(moments[0]['mask'])
    return dict(example_id=row['spec']['example_id'], fold=row['spec']['fold'],
                problem_id=row['spec']['problem_id'], candidate_count=len(ids),
                history_transitions=size, category=category,
                candidate_categories=dict(Counter(categories)),
                current_state=current_state,
                hs_identity=candidates[0]['moments']['HS']['permutation_indices'] == list(range(size)),
                h_jm_exact_equal=not any(differences),
                h_jm_max_abs_difference=max(differences))


def analyze(directory):
    complete_bytes = (directory / 'COMPLETE.json').read_bytes()
    features_bytes = (directory / 'features.jsonl').read_bytes()
    if hashlib.sha256(complete_bytes).hexdigest() != COMPLETE_SHA:
        raise ValueError('readiness COMPLETE pin differs')
    if hashlib.sha256(features_bytes).hexdigest() != FEATURE_SHA:
        raise ValueError('readiness feature pin differs')
    complete = json.loads(complete_bytes)
    if complete['files_sha256']['features.jsonl'] != FEATURE_SHA or complete['status'] != 'complete':
        raise ValueError('terminal readiness binding differs')
    rows = [json.loads(line) for line in features_bytes.splitlines()]
    profiles = [profile(row) for row in rows]
    if (len(profiles) != 320 or len({p['example_id'] for p in profiles}) != 320
            or sum(p['candidate_count'] for p in profiles) != 2544
            or len({p['problem_id'] for p in profiles}) != 23
            or {p['fold'] for p in profiles} != set(range(5))):
        raise ValueError('full320 coverage differs')
    candidate_categories = Counter()
    for p in profiles:
        candidate_categories.update(p['candidate_categories'])
    return dict(kind='source_only_history_support_diagnosis_v1',
                repair_labels_accessed=False, fitting_performed=False,
                input_complete_sha256=COMPLETE_SHA, input_features_sha256=FEATURE_SHA,
                script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                banks=320, candidates=2544, problems=23,
                bank_categories=dict(Counter(p['category'] for p in profiles)),
                candidate_categories=dict(candidate_categories),
                history_lengths=dict(Counter(p['history_transitions'] for p in profiles)),
                current_states=dict(Counter(p['current_state'] for p in profiles)),
                constant_feedback_current_states=dict(Counter(p['current_state'] for p in profiles
                    if p['category'] == 'constant_feedback')),
                hs_identity_banks=sum(p['hs_identity'] for p in profiles),
                h_jm_exact_equal_banks=sum(p['h_jm_exact_equal'] for p in profiles),
                h_jm_different_above_1e12=sum(p['h_jm_max_abs_difference'] > 1e-12 for p in profiles),
                h_jm_subthreshold_only=sum(0 < p['h_jm_max_abs_difference'] <= 1e-12 for p in profiles),
                profiles=profiles)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--readiness', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.readiness)
    # Exclusive creation; never update frozen inputs or an earlier diagnosis.
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'profiles'}, sort_keys=True))


if __name__ == '__main__':
    main()
