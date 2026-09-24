"""Post-completion joint4131 diagnosis: no fitter, scaler fit or experiment imports.

Only externally pinned completed archives and serialized raw/scaled feature
values are consumed. New numerical diagnostics remain provisional until a
separate reviewer reproduces them. No cohort filtering or gate alteration.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import tarfile

for _name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '1'
import numpy as np
from scipy import sparse
import scipy

PINS = dict(outer='f4d7249e12a879b2212678d2590cac62aea391915122901919f9b9b6b593440e',
    run='2e7c60d1378b4e3b1e0e5df574e2c9623203a5ab6c38b1deba4a5381e3db33ed',
    report='9ed572b17df7d254d052b58e4d4508901effa4d686809e5f6454a763b075e54a',
    audit='1142b78cd95cd59df6c60e647a4b17af481c895472321173fbdfc7707a07d7e1',
    prepared='71a9f8803895b9585364589554811c67c9a99969d16e6c5247716d643e21048e',
    source_tar='7dc5ed116d8e71cf0d85d584cee0e9d0fadac091871bab51a4676fa51e773d6e')
ARMS = ('H', 'Jm', 'HS', 'U', 'L', 'CF', 'C_joint')
GEOMETRY_TAU = 1e-12  # Descriptive sign categories only; never choice/gate tolerance.
SCORE_ATOL = 1e-10
SCORE_RTOL = 1e-10  # Existing independent-audit reassociation tolerance.


def require(value, message):
    if not value: raise ValueError(message)


def digest(raw): return hashlib.sha256(raw).hexdigest()
def encoded(value): return (json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False, indent=2)+'\n').encode()
def write_new(path, raw):
    with path.open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    return digest(raw)
def decode(raw):
    def pairs(values):
        result = {}
        for key, value in values:
            require(key not in result, 'duplicate JSON field'); result[key] = value
        return result
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
        parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def canonical(path):
    path = Path(path).absolute()
    require(path == path.resolve(), 'aliased path forbidden')
    return path


class Reader:
    def __init__(self, root): self.root, self.bindings = canonical(root), {}
    def read(self, name, pin):
        relative = Path(name)
        require(not relative.is_absolute() and '..' not in relative.parts and str(relative) == name, 'relative input path required')
        path = canonical(self.root/relative); raw = path.read_bytes()
        require(digest(raw) == pin and self.bindings.get(name, pin) == pin, 'input SHA differs: '+name)
        self.bindings[name] = pin
        return raw
    def json(self, name, pin): return decode(self.read(name, pin))
    def seal(self, name, pin):
        marker = self.json(name+'/COMPLETE.json', pin)
        require(marker.get('status') == 'complete' and type(marker.get('files_sha256')) is dict, 'completed seal required')
        base = self.root/name
        require(not (base/'FAILED.json').exists() and not any(base.glob('REJECTED_*')), 'failed input forbidden')
        for relative, expected in marker['files_sha256'].items(): self.read(name+'/'+relative, expected)
        return marker
    def recheck(self):
        for name, pin in self.bindings.items():
            require(digest(canonical(self.root/name).read_bytes()) == pin, 'consumed input changed: '+name)


def csr_array(row, n, width):
    require(set(row) == {'format','shape','data_dtype','index_dtype','data_hex','indices_hex','indptr_hex'}
        and row['format'] == 'csr' and row['shape'] == [n,width]
        and all(type(v) is int for v in row['shape']) and row['data_dtype'] == '<f8' and row['index_dtype'] == '<i8',
        'exact saved raw CSR schema required')
    arrays = {k: np.frombuffer(bytes.fromhex(row[k+'_hex']), dtype='<f8' if k == 'data' else '<i8')
              for k in ('data','indices','indptr')}
    d, idx, ptr = (arrays[k] for k in ('data','indices','indptr'))
    require(len(ptr) == n+1 and ptr[0] == 0 and ptr[-1] == len(d) == len(idx)
        and np.isfinite(d).all() and np.all(ptr[1:] >= ptr[:-1]) and np.all((idx >= 0)&(idx < width)), 'invalid CSR buffers')
    require(all(not np.any(np.diff(idx[a:b]) <= 0) for a,b in zip(ptr,ptr[1:])), 'noncanonical saved CSR')
    return sparse.csr_matrix((d,idx,ptr), shape=(n,width))


def matrices(raw, progress, scale, ids):
    """Use saved scale only: precisely numeric*(1/scale), then unchanged hash/phi."""
    n = len(ids)
    require(raw['candidate_ids'] == list(ids), 'raw candidate order differs')
    require(type(scale) is list and len(scale) == 3 and all(type(v) in (int,float) and math.isfinite(v) and v > 0 for v in scale), 'saved positive scale required')
    numeric = csr_array(raw['numeric'], n, 3)
    hashed = csr_array(raw['hashed'], n, 4096)
    current = sparse.hstack([numeric.multiply(1/np.asarray(scale)), hashed], format='csr')
    phi = {}
    for arm in ARMS[:-1]:
        row = progress[arm]
        require(set(row) == {'candidate_ids','dtype','shape','data_hex'} and row['candidate_ids'] == list(ids)
            and row['dtype'] == '<f8' and row['shape'] == [n,32], 'exact accepted32 identity required')
        value = np.frombuffer(bytes.fromhex(row['data_hex']), dtype='<f8')
        require(value.size == n*32 and np.isfinite(value).all(), 'finite accepted32 required')
        phi[arm] = value.reshape(n,32)
    require(all(np.array_equal(phi['H'][:,:16], v[:,:16]) for v in phi.values()) and not np.any(phi['CF'][:,16:]), 'G/CF identity differs')
    phi['C_joint'] = np.zeros((n,32),dtype=np.float64)
    return current, phi


def exact_classes(matrix):
    """Numerical exact equality, so +/-0 agree; no approximate merging."""
    groups = {}
    for i,row in enumerate(matrix): groups.setdefault(tuple(float(v) for v in row), []).append(i)
    return list(groups.values())


def known_ac(label): return label['status'] == 'stable' and label['all_ac'] is True
def unknown(label): return label['status'] == 'unknown'
def chosen(ids, scores): return min(ids, key=lambda cid: (-scores[cid],cid))
def sign(value): return 'positive' if value > GEOMETRY_TAU else 'negative' if value < -GEOMETRY_TAU else 'zero_within_tau'


def paired(left, right, noop, labels):
    value = dict(selected_candidate_changed=int(left != right), ac_gained=0, ac_lost=0,
        regression_prevented=0, regression_introduced=0, not_jointly_known=0,
        to_noop=0, from_noop=0, edited_to_edited=0, examples=1)
    if left != right: value['to_noop' if left == noop else 'from_noop' if right == noop else 'edited_to_edited'] = 1
    a,b = labels[left], labels[right]
    if unknown(a) or unknown(b): value['not_jointly_known'] = 1
    else:
        value.update(ac_gained=int(known_ac(a) and not known_ac(b)), ac_lost=int(known_ac(b) and not known_ac(a)),
            regression_prevented=int(a['loss'] == 0 and b['loss'] > 0), regression_introduced=int(a['loss'] > 0 and b['loss'] == 0))
    return value


def bank_diagnosis(prediction, current, phi, theta, labels):
    ids = tuple(prediction['candidate_scores']['H'])
    n = len(ids)
    require(current.shape == (n,4099) and theta.shape == (4131,) and np.isfinite(theta).all(), 'native joint dimensions required')
    full = np.concatenate([current.toarray(),phi['H']], axis=1)
    components = dict(current4099=np.asarray(current@theta[:4099]).ravel(),
        G16=phi['H'][:,:16]@theta[4099:4115], residual16=phi['H'][:,16:]@theta[4115:])
    # The complete sparse multiplication preserves the producer's column order;
    # independent component sums may differ by permitted reassociation roundoff.
    raw_scores = np.asarray(sparse.csr_matrix(full)@theta).ravel()
    saved = prediction['candidate_scores']['H']
    maximum = max(abs(float(raw_scores[i])-saved[cid]) for i,cid in enumerate(ids))
    require(all(math.isclose(float(raw_scores[i]),saved[cid],abs_tol=SCORE_ATOL,rel_tol=SCORE_RTOL) for i,cid in enumerate(ids)), 'recomputed H score differs')
    require(chosen(ids,dict(zip(ids,map(float,raw_scores)))) == prediction['choices']['H'], 'exact recomputed selected SHA differs')
    for i,cid in enumerate(ids):
        require(math.isclose(math.fsum(float(v[i]) for v in components.values()),saved[cid],abs_tol=SCORE_ATOL,rel_tol=SCORE_RTOL), 'component sum differs')
    shared = {cid:float(components['current4099'][i]+components['G16'][i]) for i,cid in enumerate(ids)}
    require(all(math.isclose(shared[cid],prediction['candidate_scores']['shared_H_CF'][cid],abs_tol=SCORE_ATOL,rel_tol=SCORE_RTOL) for cid in ids)
        and chosen(ids,shared) == prediction['choices']['shared_H_CF'], 'shared-H CF exact choice/score differs')
    classes = exact_classes(full)
    winners = [min((ids[i] for i in group)) for group in classes]
    ac = [cid for cid in ids if known_ac(labels[cid])]
    possible = [cid for cid in ids if known_ac(labels[cid]) or unknown(labels[cid])]
    h = prediction['choices']['H']; noop = prediction['choices']['noop']
    miss = bool(ac and not known_ac(labels[h]))
    alternative = min(ac, key=lambda cid:(-saved[cid],cid)) if ac else None
    margins = None
    if alternative is not None:
        hi,ai = ids.index(h),ids.index(alternative)
        margins = {key:float(v[hi]-v[ai]) for key,v in components.items()}
        margins.update(total=float(saved[h]-saved[alternative]), residual_direction=sign(margins['residual16']))
        require(math.isclose(math.fsum(margins[k] for k in components),margins['total'],abs_tol=SCORE_ATOL,rel_tol=SCORE_RTOL), 'margin additivity differs')
    equality = {a:bool(np.array_equal(phi['H'],phi[a])) for a in ARMS[1:]}
    transitions = {m:paired(h,c,noop,labels) for m,c in prediction['choices'].items() if m != 'H'}
    return dict(example_id=prediction['example_id'],problem_id=prediction['problem_id'],fold=prediction['fold'],
        bank_id=prediction['bank_id'],current_status='unknown' if unknown(labels[noop]) else 'known_ac' if known_ac(labels[noop]) else 'known_nonac',
        candidates=n, known_ac_candidates=len(ac), unknown_candidates=sum(unknown(v) for v in labels.values()),
        known_oracle=bool(ac),possible_oracle=bool(possible),known_ac_miss=miss,
        H_choice=h,H_known_ac=known_ac(labels[h]),H_unknown=unknown(labels[h]),
        exact_full4131_classes=len(classes),exact_current4099_classes=len(exact_classes(current.toarray())),
        class_sha_champions=winners,known_ac_class_champion=any(known_ac(labels[c]) for c in winners),
        class_blocked_known_miss=bool(miss and not any(known_ac(labels[c]) for c in winners)),
        best_H_score_known_ac=alternative,selected_minus_best_known_ac=margins,
        exact_H_feature_equal=equality,all_zero_progress=not bool(np.any(phi['H'])),
        residual_candidate_score_range=float(np.ptp(components['residual16'])),
        maximum_score_recompute_difference=maximum,paired=transitions,
        CF_refitted_vs_shared=paired(prediction['choices']['CF'],prediction['choices']['shared_H_CF'],noop,labels))


def aggregate(rows):
    counts = {key:sum(r[key] for r in rows) for key in ('known_oracle','possible_oracle','known_ac_miss','H_known_ac','H_unknown','class_blocked_known_miss','known_ac_class_champion','all_zero_progress')}
    counts.update(examples=len(rows),problems=len({r['problem_id'] for r in rows}),candidates=sum(r['candidates'] for r in rows),
        any_full4131_collision=sum(r['exact_full4131_classes'] < r['candidates'] for r in rows),
        any_current4099_collision=sum(r['exact_current4099_classes'] < r['candidates'] for r in rows))
    counts['miss_residual_direction'] = dict(Counter(r['selected_minus_best_known_ac']['residual_direction'] for r in rows if r['known_ac_miss']))
    counts['paired'] = {m:dict(sum((Counter(r['paired'][m]) for r in rows),Counter())) for m in rows[0]['paired']} if rows else {}
    counts['CF_refitted_vs_shared'] = dict(sum((Counter(r['CF_refitted_vs_shared']) for r in rows),Counter()))
    counts['exact_H_feature_equal'] = {a:sum(r['exact_H_feature_equal'][a] for r in rows) for a in ARMS[1:]}
    return counts


def diagnose(archive, source_tar):
    reader = Reader(archive)
    outer = reader.seal('supervised-v1', PINS['outer']); run = reader.seal('run-v1', PINS['run'])
    require(outer['experiment_complete_sha256'] == PINS['run'] and run['completed_fits'] == 35 and run['recipients'] == 320 and run['model_promotion'] is False, 'full sealed35/320 required')
    report = reader.json('run-v1/assessment/report.json',PINS['report'])
    audit = reader.json('supervised-v1/verified/report.json',PINS['audit'])
    require(audit['verified'] is True and (audit['models'],audit['methods'],audit['recipients']) == (35,14,320) and audit['gate'] == report['gate'], 'independent full audit/gate equality required')
    manifest = reader.json('run-v1/manifest.json',run['files_sha256']['manifest.json'])
    # Only the assessment body is needed: do not open/hash sibling training bodies.
    prep = reader.json('prepared-v1/COMPLETE.json',PINS['prepared'])
    label_pin = manifest['label_contracts']['assessment']['expected_sha256']
    require(prep['files_sha256']['assessment/all320-labels.json'] == label_pin, 'assessment external contract differs')
    envelope = reader.json('prepared-v1/assessment/all320-labels.json',label_pin)
    labels = {(v['bank_id'],v['candidate_id']):v for v in envelope['labels']}
    require(len(labels) == len(envelope['labels']) == 2544, 'all original unique candidate labels required')
    predictions = reader.json('run-v1/predictions.json',run['files_sha256']['predictions.json'])
    require(len(predictions) == len({p['example_id'] for p in predictions}) == 320, 'all320 unique predictions required')
    tar_path = canonical(source_tar); tar_raw = tar_path.read_bytes()
    require(digest(tar_raw) == PINS['source_tar'], 'authoritative execution source tar differs')
    jobs = {f:reader.json(f'jobs/fold-{f}.json',run['job_sha256'][str(f)]) for f in range(5)}
    with tarfile.open(tar_path) as archive_tar:
        for f,job in jobs.items():
            require(job['source_sha256'] == jobs[0]['source_sha256'], 'source closure differs across jobs')
            for name,pin in job['source_sha256'].items():
                member = archive_tar.getmember(name)
                require(member.isfile() and digest(archive_tar.extractfile(member).read()) == pin, 'executed source bytes differ: '+name)
    rows = []; coefficients = {}; seen = set()
    for f in range(5):
        job = jobs[f]; inp = job['inputs']
        require(inp['fold'] == f and inp['synthetic'] is False and len(inp['examples']) == 320, 'full own source capsule required')
        scaler = reader.json(f'run-v1/fold-{f}/SCALER.json',run['files_sha256'][f'fold-{f}/SCALER.json'])
        model = reader.json(f'run-v1/fold-{f}/H.json',run['files_sha256'][f'fold-{f}/H.json'])
        theta = np.asarray(model['joint_model']['coefficients'],dtype=np.float64)
        coefficients[str(f)] = {name:float(np.linalg.norm(theta[a:b])) for name,a,b in (('current4099',0,4099),('G16',4099,4115),('residual16',4115,4131))}
        for prediction in (p for p in predictions if p['fold'] == f):
            bid = prediction['bank_id']; saved = inp['banks'][bid]; ids = tuple(saved['candidate_ids'])
            require(bid not in seen and saved['bank_seal_sha256'] == prediction['bank_seal_sha256'], 'held bank duplicate/seal mismatch'); seen.add(bid)
            require(inp['assignment']['example_fold'][prediction['example_id']] == f
                and set(ids) == set(prediction['candidate_scores']['H']), 'held assignment/candidates differ')
            # JSON map insertion order is not the feature-row order.
            pred = dict(prediction,candidate_scores={m:{cid:s[cid] for cid in ids} for m,s in prediction['candidate_scores'].items()})
            require(set(pred['candidate_scores']) == set(pred['choices']) and all(
                all(type(v) in (int,float) and math.isfinite(v) for v in scores.values())
                and chosen(ids,scores) == pred['choices'][method] for method,scores in pred['candidate_scores'].items()),
                'sealed choice does not match exact candidate score SHA argmax')
            current,phi = matrices(inp['raw_current'][bid],{a:inp['interactions'][a][bid] for a in ARMS[:-1]},scaler['numeric_scale'],ids)
            bank_labels = {cid:labels[bid,cid] for cid in ids}
            rows.append(bank_diagnosis(pred,current,phi,theta,bank_labels))
        print(json.dumps(dict(phase='diagnosing',completed_examples=len(rows),total_examples=320)),flush=True)
    require(len(rows) == len(seen) == 320, 'complete population required')
    full = aggregate(rows)
    require(full['candidates'] == 2544 and full['problems'] == 23, 'population changed')
    for method,values in full['paired'].items():
        # Counter drops zero keys; exact original fields are restored for comparison.
        expected = report['primary_transitions'][method]
        require({k:values.get(k,0) for k in expected} == expected, 'paired counts differ from sealed assessment')
    output = dict(kind='joint4131_completed_posthoc_diagnosis_v1',verification_status='provisional_pending_independent_review',
        fitting_performed=False,scaler_fitting_performed=False,experiment_modules_imported=False,exclusions=0,
        scientific_gate=dict(report['gate']),full=full,rows=rows,
        folds={str(f):aggregate([r for r in rows if r['fold'] == f]) for f in range(5)},
        current_status_subgroups={s:aggregate([r for r in rows if r['current_status'] == s]) for s in ('known_ac','known_nonac','unknown')},
        equal_feature_strata={a:{str(equal):aggregate([r for r in rows if r['exact_H_feature_equal'][a] is equal])
            for equal in (False,True)} for a in ARMS[1:]},
        coefficient_norms=coefficients,maximum_score_recompute_difference=max(r['maximum_score_recompute_difference'] for r in rows),
        inherited_assessment_summary=report['full'],inherited_architecture_diagnostic=report['architecture_diagnostic'],
        provenance=dict(input_sha256=dict(reader.bindings),execution_source_tar_sha256=PINS['source_tar'],
            execution_source_sha256=jobs[0]['source_sha256'],diagnostic_source_sha256=digest(Path(__file__).read_bytes()),
            diagnostic_tests_sha256=digest((Path(__file__).resolve().parents[1]/'tests/test_zpd_joint_progress_diagnosis.py').read_bytes()),
            runtime=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,platform=platform.platform())),
        scope=dict(class_ceiling='Exact full4131 classes with SHA champions are necessary, not simultaneously attainable.',
            geometry_tau=GEOMETRY_TAU,score_reassociation_atol=SCORE_ATOL,score_reassociation_rtol=SCORE_RTOL,
            selected_candidate_tolerance=False,old_fixed_base_radius_reused=False,causal_mechanism_identified=False,
            fresh_outcomes_opened=False,training_label_bodies_opened=False,independent_full_audit_repeated=False))
    reader.recheck();require(digest(tar_path.read_bytes()) == PINS['source_tar'], 'source tar drift')
    return output,reader


def main(argv=None):
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--archive',type=Path,required=True);parser.add_argument('--source-tar',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args(argv)
    output=canonical(args.output)
    require(not output.exists() and not output.is_relative_to(canonical(args.archive)), 'new separate diagnostic output required')
    result,reader=diagnose(args.archive,args.source_tar)
    output.mkdir(parents=True)
    try:
        raw=encoded(result);write_new(output/'report.json',raw)
        reader.recheck();require(digest(canonical(args.source_tar).read_bytes()) == PINS['source_tar'], 'source tar drift before seal')
        require(digest((output/'report.json').read_bytes()) == digest(raw), 'diagnostic output drift')
        write_new(output/'COMPLETE.json',encoded(dict(status='complete',verification_status='provisional_pending_independent_review',
            files_sha256={'report.json':digest(raw)},fitting_performed=False,exclusions=0)))
    except BaseException as error:
        marker=output/'COMPLETE.json'
        if marker.exists():marker.rename(output/'REJECTED_COMPLETE.json')
        write_new(output/'FAILED.json',encoded(dict(status='failed',error_type=type(error).__name__,error=str(error))))
        raise
    print(json.dumps(dict(phase='complete',output=str(output),full=result['full'])),flush=True)


if __name__=='__main__':main()
