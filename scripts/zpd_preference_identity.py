"""Explicit non-identifiable target equivalence; preserve every training row.

For identical prompt/target tokens, log pi(y)-log pi(y) is identically zero,
so the DPO loss is log(2), its gradient is exactly zero for any parameters.
This is not a claim that a native rejected submission was actually correct.
"""
import math
from scripts import zpd_preference_objective as strict

VERSION = 'paired_native_verdict_dpo_identity_v1'
IDENTITY_ISSUES = {'normalized_chosen_equals_rejected', 'token_identical_preference'}
encode_pair = strict.encode_pair
disable_dropout = strict.disable_dropout
sequence_logprob = strict.sequence_logprob
dpo_loss = strict.dpo_loss
sequential_coefficients = strict.sequential_coefficients


def contract():
    result = strict.contract()
    result.pop('identical_or_overflow')
    result.update(version=VERSION, identical='retain_constant_log2_loss_zero_gradient_same_denominator',
        overflow='hold_entire_pilot', identity_rule='exact_full_target_token_sequence_equality',
        native_verdicts_relabelled=False, strict_preference_claim_on_identical=False,
        identical_reference='same_frozen_reference_for_same_prompt_target',
        capacity_probe_selection='union_four_longest_plus_first_train_identity_and_first_strict')
    return result


def audit_pair(c, h, tokenizer, provenance):
    audit = strict.audit_pair(c, h, tokenizer, provenance)
    # Compare actual token arrays, not just digest equality or string heuristics.
    pairs = {a: encode_pair(row, tokenizer) for a, row in (('C', c), ('H', h))}
    equal = {a: p['chosen']['input_ids'] == p['rejected']['input_ids']
             and p['chosen']['prompt_tokens'] == p['rejected']['prompt_tokens'] for a, p in pairs.items()}
    strict.train.require(equal['C'] == equal['H'], 'paired identity classification differs')
    audit.update(identity_tie=equal['C'], raw_equal=c['current_code'] == c['target_code'],
        normalized_equal=c['current_code'].rstrip() == c['target_code'].rstrip(),
        original_issues=list(audit['issues']), preference_identifiable=not equal['C'])
    if equal['C']:
        strict.train.require(bool(IDENTITY_ISSUES.intersection(audit['issues'])), 'identity provenance absent')
        audit['issues'] = [x for x in audit['issues'] if x not in IDENTITY_ISSUES]
    else:
        strict.train.require(not IDENTITY_ISSUES.intersection(audit['issues']), 'false identity annotation')
    return audit


def longest_indices(audits):
    indices = set(strict.longest_indices(audits))
    # These are additional numerical probes, never training subset selection.
    for status in (True, False):
        index = next((i for i, a in enumerate(audits) if a['identity_tie'] is status), None)
        if index is not None: indices.add(index)
    return sorted(indices)


def probe_pair(model, pair):
    import torch
    same = (pair['chosen']['input_ids'] == pair['rejected']['input_ids'] and
            pair['chosen']['prompt_tokens'] == pair['rejected']['prompt_tokens'])
    if not same:
        return dict(strict.probe_pair(model, pair), identity_tie=False, preference_identifiable=True)
    # Shared node enforces the algebraic identity exactly, avoiding roundoff
    # from independently accumulating opposite BF16 gradients.
    model.zero_grad(set_to_none=True)
    value = sequence_logprob(model, pair['chosen'])
    reference = float(value.detach())
    loss = dpo_loss(value, value, reference, reference)
    loss.backward()
    gradients = [p.grad for p in model.parameters() if p.requires_grad and p.grad is not None]
    strict.train.require(gradients and all(bool(torch.isfinite(g).all()) and bool((g == 0).all()) for g in gradients),
                         'identical-target preference must have exact zero gradients')
    actual = float(loss.detach())
    strict.train.require(abs(actual - math.log(2)) < 1e-6, 'identity loss must be log(2)')
    return dict(initial_loss=actual, reference=dict(chosen=reference, rejected=reference),
        policy=dict(chosen=reference, rejected=reference), gradient_norm=0.0, identity_tie=True,
        preference_identifiable=False, optimizer_steps=0, actual_fit=False,
        moving_reference_allowed=False, retained_in_loss_denominator=True)
