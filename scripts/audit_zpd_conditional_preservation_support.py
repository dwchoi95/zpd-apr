"""Training-only support inventory for a proposed six-verdict no-op residual.

No fitting, scoring, reranking, source execution or new outcome collection.
Existing pairs and weights are reconstructed, then checked against sealed
refined-balanced models. All reported fold support is fitting-fold support.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import platform

from scripts.audit_zpd_repair_preservation_cv import equal, supervision, original_stratum, verify_files
from scripts.run_zpd_repair_structure_cv import load_training, assign_folds
from src.repair.pilot_contracts import canonical_hash, source_hash

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = ('AC','WA','CE','RE','RESOURCE','OTHER')
STRATA = ('known_ac','known_nonac','unknown')
PRESERVATION_COMPLETE = 'b23e99d5746ebbdbc5451707bb942a4bde02397c8d4a49591311c0b4f4047c80'
PRESERVATION_REPORT = '83120bfc7cf9daa513cf97b5b2cd6e3ed636e1b415d9d2f476d22fbcc6e58324'
DESIGN = ROOT/'analysis_protocols/zpd-conditional-preservation-next-design-20260924.md'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def read(path):
    with Path(path).open(encoding='utf-8') as stream:return json.load(stream)


def category(value):
    if type(value) is not str or not value:
        raise ValueError('nonempty observed nominal verdict required')
    if value in CATEGORIES:return value
    return {'Accepted':'AC','Wrong Answer':'WA','Compile Error':'CE','Compilation Error':'CE',
        'Runtime Error':'RE','Time Limit Exceeded':'RESOURCE','Memory Limit Exceeded':'RESOURCE'}.get(value,'OTHER')


def support_rows(examples,banks,records):
    by_id = {r['example_id']:r for r in records}
    if len(by_id) != len(records) or set(by_id) != {e.example_id for e in examples}:
        raise ValueError('exact fitting-prefix metadata coverage required')
    result = []
    for e in examples:
        if e.split != 'train':raise ValueError('only original train recipients allowed')
        r = by_id[e.example_id];bank = banks[e.bank_id];noop = source_hash(bank.current_source)
        if r['bank_id'] != e.bank_id or r['user_id'] != e.user_id or r['stratum'] not in STRATA:
            raise ValueError('supervision identity mismatch')
        count = Counter(noop_win_pairs=0,noop_loss_pairs=0,edited_only_pairs=0)
        for left,right,target in r['pairs']:
            if target not in (0,1) or left == right:raise ValueError('strict ordered target pair required')
            if noop in (left,right):
                preferred = left if target else right
                count['noop_win_pairs' if preferred == noop else 'noop_loss_pairs'] += 1
            else:count['edited_only_pairs'] += 1
        weight = r['row_weight']
        if type(weight) not in (int,float) or not math.isfinite(weight) or weight < 0:
            raise ValueError('finite nonnegative saved pair weight required')
        result.append(dict(example_id=e.example_id,user_id=e.user_id,bank_id=e.bank_id,
            problem_id=e.observation.problem_id,raw_nominal_verdict=e.observation.current.verdict,
            nominal_category=category(e.observation.current.verdict),current_stratum=r['stratum'],
            unknown_candidates=len(r['unknown_candidate_ids']),informative=bool(r['pairs']),
            noop_informative=bool(count['noop_win_pairs']+count['noop_loss_pairs']),
            noop_win=bool(count['noop_win_pairs']),noop_loss=bool(count['noop_loss_pairs']),
            unordered_pairs=len(r['pairs']),**count,
            pair_mass=2*len(r['pairs'])*weight,
            noop_win_mass=2*count['noop_win_pairs']*weight,
            noop_loss_mass=2*count['noop_loss_pairs']*weight,
            edited_only_mass=2*count['edited_only_pairs']*weight))
    return result


def aggregate(rows, *, include_mass=True):
    result = dict(prefixes=len(rows),users=len({r['user_id'] for r in rows}),
        problems=len({r['problem_id'] for r in rows}),problem_ids=sorted({r['problem_id'] for r in rows}),
        informative_prefixes=sum(r['informative'] for r in rows),
        noop_informative_prefixes=sum(r['noop_informative'] for r in rows),
        noop_win_prefixes=sum(r['noop_win'] for r in rows),noop_loss_prefixes=sum(r['noop_loss'] for r in rows),
        unknown_candidates=sum(r['unknown_candidates'] for r in rows),
        unordered_pairs=sum(r['unordered_pairs'] for r in rows),
        noop_win_pairs=sum(r['noop_win_pairs'] for r in rows),noop_loss_pairs=sum(r['noop_loss_pairs'] for r in rows),
        edited_only_pairs=sum(r['edited_only_pairs'] for r in rows))
    if include_mass:
        result.update({name:math.fsum(r[name] for r in rows) for name in
            ('pair_mass','noop_win_mass','noop_loss_mass','edited_only_mass')})
    return result


def table(rows, *, include_mass=True):
    return {category:{s:aggregate([r for r in rows if r['nominal_category'] == category and r['current_stratum'] == s],
                                  include_mass=include_mass) for s in STRATA} for category in CATEGORIES}


def summarize_support(rows):
    cells = table(rows)
    category_totals = {c:aggregate([r for r in rows if r['nominal_category'] == c]) for c in CATEGORIES}
    active = [c for c in CATEGORIES if category_totals[c]['noop_informative_prefixes']]
    no_positive = [c for c in active if not category_totals[c]['noop_win_prefixes']]
    no_known_ac = [c for c in active if not cells[c]['known_ac']['noop_win_prefixes']]
    positive_problems = {c:sorted({r['problem_id'] for r in rows if r['nominal_category'] == c
                                  and r['current_stratum'] == 'known_ac' and r['noop_win']}) for c in CATEGORIES}
    return dict(total=aggregate(rows),cells=cells,category_totals=category_totals,
        category_likelihood_rank=len(active),active_categories=active,
        zero_likelihood_columns=[c for c in CATEGORIES if c not in active],
        active_categories_without_noop_win=no_positive,active_categories_without_known_ac_noop_win=no_known_ac,
        known_ac_positive_problem_ids=positive_problems)


def ceiling(examples,banks,labels,predictions):
    by_id = {p['example_id']:p for p in predictions}
    if len(by_id) != len(examples) or set(by_id) != {e.example_id for e in examples}:
        raise ValueError('exact train320 saved prediction coverage required')
    counts = Counter()
    for e in examples:
        p = by_id[e.example_id];bank = banks[e.bank_id];noop = source_hash(bank.current_source)
        if p['bank_id'] != e.bank_id or p['choices']['noop'] != noop:
            raise ValueError('frozen baseline prediction bank mismatch')
        initial = original_stratum(labels[e.bank_id,noop]);chosen = labels[e.bank_id,p['choices']['structural_C']]
        known_ac = chosen['status'] == 'stable' and chosen['all_ac']
        counts['baseline_known_ac'] += known_ac
        counts[initial+'_originals'] += 1
        counts[initial+'_baseline_ac'] += known_ac
    return dict(counts,
        known_nonac_repair_ceiling=counts['known_nonac_baseline_ac'],
        rescueable_known_ac=counts['known_ac_originals']-counts['known_ac_baseline_ac'],
        optimistic_known_ac_ceiling=counts['known_nonac_baseline_ac']+counts['known_ac_originals']+counts['unknown_baseline_ac'],
        interpretation='Restricted baseline-or-noop action space only; optimistic structural bound, not a fitted result.')


def audit(project,run,*,production=True):
    project,run = Path(project).resolve(),Path(run).resolve()
    marker_path = run/'COMPLETE.json';marker_sha = sha(marker_path);marker = read(marker_path)
    if production and marker_sha != PRESERVATION_COMPLETE:raise ValueError('wrong frozen preservation family')
    if marker.get('status') != 'complete':raise ValueError('completed preservation run required')
    verify_files(run,marker['files_sha256'])
    required = {'folds.json','predictions.json','report.json'}|{f'fold-{f}/'+name for f in range(5)
               for name in ('cohort.json','refined_balanced.json','structural_C.json','COMPLETE.json')}
    if not required <= set(marker['files_sha256']):raise ValueError('consumed artifacts must be sealed')
    if production and sha(run/'report.json') != PRESERVATION_REPORT:raise ValueError('wrong preservation report')
    examples,banks,labels,bindings = load_training(project,production=production)
    folds = assign_folds(examples);equal(read(run/'folds.json'),folds,'fixed folds')
    reports = {};all_rows = {};repeat_counts = Counter()
    for f in range(5):
        directory = run/f'fold-{f}';foldmarker = read(directory/'COMPLETE.json')
        verify_files(directory,foldmarker['files_sha256'])
        cohort = read(directory/'cohort.json')
        train = [e for e in examples if folds['example_fold'][e.example_id] != f]
        held = [e for e in examples if folds['example_fold'][e.example_id] == f]
        equal(cohort['train_example_ids'],[e.example_id for e in train],'fitting IDs')
        equal(cohort['held_example_ids'],[e.example_id for e in held],'held IDs')
        bids = {e.bank_id for e in train};bs = {bid:banks[bid] for bid in bids};ls = {k:v for k,v in labels.items() if k[0] in bids}
        model = read(directory/'refined_balanced.json');reference = read(directory/'structural_C.json')
        if model['model_sha256'] != canonical_hash({k:v for k,v in model.items() if k != 'model_sha256'}):
            raise ValueError('model canonical seal mismatch')
        if model['cell'] != 'refined_balanced' or model['reference_model_sha256'] != reference['model_sha256']:
            raise ValueError('wrong frozen objective/model reference')
        meta = supervision(train,bs,ls,'refined_balanced')
        equal(model['training'],meta,'independently rebuilt training-only pairs and weights')
        rows = support_rows(train,bs,meta['prefixes'])
        reports[str(f)] = summarize_support(rows)
        for r in rows:
            identity = r['example_id'];repeat_counts[identity] += 1
            # Pair support is independent of fold weight. Do not pool repeated
            # fitting occurrences as extra observations or invent a full-fit mass.
            no_mass = {k:v for k,v in r.items() if not k.endswith('_mass')}
            if identity in all_rows:equal(all_rows[identity],no_mass,'cross-fold support invariance')
            all_rows[identity] = no_mass
    if set(repeat_counts.values()) != {4}:raise ValueError('each original train prefix must appear in four fitting folds')
    unique = list(all_rows.values())
    report = dict(kind='training_only_conditional_preservation_support_v1',fitting_performed=False,
        scoring_or_reranking_performed=False,new_outcomes_collected=False,heldout_outcome_files_opened=False,
        original64_32_physically_shared_disclosed=True,train_prefixes=len(examples),
        original_fold_sizes=folds['fold_sizes'],folds=reports,
        unique_population=aggregate(unique,include_mass=False),unique_cells=table(unique,include_mass=False),
        unique_raw_nominal_verdicts=dict(Counter(r['raw_nominal_verdict'] for r in unique)),
        unique_known_ac_ids=[r['example_id'] for r in unique if r['current_stratum'] == 'known_ac'],
        action_space_ceiling=ceiling(examples,banks,labels,read(run/'predictions.json')),
        preservation_complete_sha256=marker_sha,preservation_report_sha256=sha(run/'report.json'),
        design_sha256=sha(DESIGN),source_sha256={name:sha(ROOT/name) for name in
            ('scripts/audit_zpd_conditional_preservation_support.py','scripts/audit_zpd_repair_preservation_cv.py',
             'scripts/audit_zpd_history_action_cv.py','scripts/run_zpd_repair_structure_cv.py','src/repair/pilot_contracts.py')},
        runtime=dict(python=platform.python_version()),
        input_sha256=bindings,run_artifact_sha256=marker['files_sha256'],
        interpretation='Fitting-fold support only; each recipient reused in four folds. Regularization uniqueness is not data identifiability.')
    verify_files(run,marker['files_sha256'])
    if sha(marker_path) != marker_sha:raise ValueError('run changed during audit')
    for path,digest in bindings.items():
        if sha(path) != digest:raise ValueError('training input changed during audit')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--project',required=True,type=Path)
    parser.add_argument('--run',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args = parser.parse_args(argv)
    if args.output.exists():raise ValueError('new diagnostic output required')
    report = audit(args.project,args.run)
    args.output.mkdir(parents=True)
    with (args.output/'report.json').open('x',encoding='utf-8') as stream:
        json.dump(report,stream,sort_keys=True,indent=2,allow_nan=False);stream.write('\n')
    with (args.output/'COMPLETE.json').open('x',encoding='utf-8') as stream:
        json.dump(dict(status='complete',fitting_performed=False,files_sha256={'report.json':sha(args.output/'report.json')},
                       preservation_complete_sha256=report['preservation_complete_sha256']),stream,sort_keys=True);stream.write('\n')
    print(json.dumps(dict(train_prefixes=report['train_prefixes'],fold_ranks={f:r['category_likelihood_rank'] for f,r in report['folds'].items()},
        unique_raw_nominal_verdicts=report['unique_raw_nominal_verdicts'],action_space_ceiling=report['action_space_ceiling']),sort_keys=True))


if __name__ == '__main__':main()
