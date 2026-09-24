"""Independent exact-fraction witnesses for the additive C_joint gate only."""
import copy
from fractions import Fraction
import random
import unittest

from scripts import zpd_joint_progress_assessment as joint
from scripts import zpd_repair_progress_assessment as previous
from tests.test_zpd_joint_progress_assessment import fixture


def facts(rows,labels,method):
    n=len(rows)
    if not n:return None
    selected=[labels[p['bank_id'],p['choices'][method]] for p in rows]
    a=sum(l['status']=='stable' and l['all_ac'] for l in selected)
    r=sum(l['status']=='stable' and l['loss']>0 for l in selected)
    u=sum(l['status']=='unknown' for l in selected)
    return (Fraction(a,n),Fraction(r,n),Fraction(r+u,n))


def reference_compare(rows,labels,strict=True):
    if not rows:return dict(evaluable=False,passed=False,checks={})
    groups=[[p for p in rows if p['problem_id']==q] for q in sorted({p['problem_id'] for p in rows})]
    pooled={m:facts(rows,labels,m) for m in ('H','C_joint')}
    equal={m:tuple(sum((facts(g,labels,m)[i] for g in groups),Fraction())/len(groups) for i in range(3)) for m in pooled}
    checks={}
    for name,values in (('pooled',pooled),('equal_problem',equal)):
        h,c=values['H'],values['C_joint']
        checks[name+'_ac']=h[0]>c[0] if strict else h[0]>=c[0]
        checks[name+'_regression_lower']=h[1]<=c[1]
        checks[name+'_regression_upper']=h[2]<=c[2]
    return dict(evaluable=True,passed=all(checks.values()),checks=checks)


class JointAssessmentIndependentTests(unittest.TestCase):
    def test_seeded_exact_fraction_new_conjunction_and_fixed_unknown_denominators(self):
        rng=random.Random(20260925)
        for case in range(80):
            cohort,predictions,labels=fixture()
            for row in predictions:
                ids=next(c['candidate_ids'] for c in cohort if c['example_id']==row['example_id'])
                for method in joint.METHODS:
                    if method!='noop':row['choices'][method]=rng.choice(ids)
            # Unequal problem sizes are deliberate: equal-problem is not pooled.
            for k in range(case%7):
                c=copy.deepcopy(cohort[1]);p=copy.deepcopy(predictions[1]);old=c['bank_id']
                for v in (c,p):v.update(example_id='copy-'+str(k),user_id='copy-user-'+str(k),bank_id='copy-bank-'+str(k))
                for cid in c['candidate_ids']:labels[c['bank_id'],cid]=dict(labels[old,cid],bank_id=c['bank_id'])
                cohort.append(c);predictions.append(p)
            report=joint.assess(cohort,predictions,labels)
            nonac=[];ac=[]
            for p in predictions:
                current=labels[p['bank_id'],p['choices']['noop']]
                if current['status']=='stable':(ac if current['all_ac'] else nonac).append(p)
            checks=dict(full_check=reference_compare(predictions,labels),known_nonac_check=reference_compare(nonac,labels),
                known_ac_check=reference_compare(ac,labels,False),
                nonworse_full_folds=sum(facts([p for p in predictions if p['fold']==f],labels,'H')[0]>=
                    facts([p for p in predictions if p['fold']==f],labels,'C_joint')[0] for f in range(5)),required_nonworse_folds=4)
            checks['passed']=all(checks[k]['passed'] for k in ('full_check','known_nonac_check','known_ac_check')) and checks['nonworse_full_folds']>=4
            with self.subTest(case=case):
                self.assertEqual(report['gate']['joint_current_check'],checks)
                self.assertEqual(report['gate']['passed'],report['inherited_progress_gate']['passed'] and checks['passed'])
                self.assertEqual(report['full']['examples'],len(cohort))
                self.assertEqual(report['full']['results']['C_joint']['fractions']['ac_lower']['value'],float(facts(predictions,labels,'C_joint')[0]))
                self.assertEqual(report['exclusions'],0)

    def test_changing_cjoint_preserves_every_inherited_fold_and_subgroup_cell(self):
        cohort,predictions,labels=fixture();old=previous.assess(cohort,joint.project_progress(predictions),labels)
        for choice in ('ac','bad','regression','unknown','noop'):
            values=copy.deepcopy(predictions)
            for p in values:p['choices']['C_joint']=choice
            result=joint.assess(cohort,values,labels)
            self.assertEqual(result['inherited_progress_gate'],old['gate'])
            pairs=[(result['full'],old['full'])]
            pairs.extend((result['folds'][f],old['folds'][f]) for f in old['folds'])
            for name in old['current_status_subgroups']:
                pairs.append((result['current_status_subgroups'][name],old['current_status_subgroups'][name]))
                pairs.extend((result['current_status_subgroup_folds'][name][f],old['current_status_subgroup_folds'][name][f]) for f in old['folds'])
            for actual,expected in pairs:
                self.assertEqual(actual['examples'],expected['examples'])
                self.assertEqual(actual['problems'],expected['problems'])
                for m in previous.METHODS:
                    self.assertEqual(actual['results'][m],expected['results'][m])
                    if expected['equal_problem'] is not None:self.assertEqual(actual['equal_problem'][m],expected['equal_problem'][m])
                    for problem in expected['problem_results']:self.assertEqual(actual['problem_results'][problem][m],expected['problem_results'][problem][m])


if __name__=='__main__':unittest.main()
