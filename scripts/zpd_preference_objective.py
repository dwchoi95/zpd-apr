"""Final-AC versus observed failed-current preference, with no held-out labels.

The pilot constructs no new supervision target and never changes a parameter.
Sequence log probabilities include every completion token and EOS, not prompts.
"""
from __future__ import annotations
import math
from scripts import train_zpd_paired_history as train

VERSION = 'paired_native_verdict_dpo_capacity_v1'
BETA = 0.1


def contract():
    return dict(version=VERSION, chosen='existing_final_native_AC', rejected='same_observed_native_nonAC_current',
        objective='negative_log_sigmoid_beta_reference_adjusted_sequence_log_odds', beta=BETA,
        reference='matching_frozen_C_or_H_SFT_adapter', normalization='sum_all_target_tokens_including_one_eos',
        target_contract='rstrip_separate_tokenization_then_one_eos', dropout=0.0, microbatch_pairs=1,
        sequential_backward=True, optimizer_steps=0, fit=False, parameter_search=False,
        validation_used_for_updates=False, generation=False, private_evaluation=False,
        filtering=False, truncation=False, identical_or_overflow='hold_entire_pilot', model_promotion=False)


def encode_pair(row, tokenizer):
    positive = train.encode_record(row, tokenizer)
    negative = train.encode_record(dict(row, target_code=row['current_code']), tokenizer)
    n = positive['prompt_tokens']
    train.require(positive['input_ids'][:n] == negative['input_ids'][:n]
                  and n == negative['prompt_tokens'], 'preference prompt changed')
    return dict(chosen=positive, rejected=negative)


def audit_pair(c, h, tokenizer, provenance):
    """All pairs retained. Infeasibility is a global HOLD, never an exclusion."""
    for field in ('example_id', 'trajectory_id', 'user_id', 'problem_id', 'current_code', 'target_code'):
        train.require(c[field] == h[field], 'C/H preference identity differs: ' + field)
    train.require(c['example_id'] == provenance['example_id']
        and c['trajectory_id'] == provenance['trajectory_id']
        and c['user_id'] == provenance['user_id'] and c['problem_id'] == provenance['problem_id']
        and c['current_code'] == provenance['current']['source']
        and c['target_code'] == provenance['target_code']
        and train.sha(c['target_code'].encode()) == provenance['target_sha256']
        and provenance['current']['timestamp'] < provenance['target_timestamp'], 'prepared provenance differs')
    encoded = {a: encode_pair(r, tokenizer) for a, r in (('C', c), ('H', h))}
    issues = []
    if c['current_code'].rstrip() == c['target_code'].rstrip():
        issues.append('normalized_chosen_equals_rejected')
    audit = dict(example_id=c['example_id'], trajectory_id=c['trajectory_id'],
        current_sha256=train.sha(c['current_code'].encode()), target_sha256=provenance['target_sha256'], arms={})
    for arm, pair in encoded.items():
        audit['arms'][arm] = {}
        for label, feature in pair.items():
            tokens = dict(prompt_tokens=feature['prompt_tokens'], target_tokens=feature['output_tokens'],
                full_tokens=feature['full_tokens'], target_token_ids_sha256=feature['target_token_ids_sha256'],
                messages_sha256=feature['messages_sha256'])
            audit['arms'][arm][label] = tokens
            if tokens['prompt_tokens'] > 4096 or tokens['target_tokens'] > 4096 or tokens['full_tokens'] > 8192:
                issues.append(arm + ':' + label + ':overflow')
    for label in ('chosen', 'rejected'):
        train.require(audit['arms']['C'][label]['target_token_ids_sha256'] ==
                      audit['arms']['H'][label]['target_token_ids_sha256'], 'preference target tokens differ')
    if audit['arms']['C']['chosen']['target_token_ids_sha256'] == audit['arms']['C']['rejected']['target_token_ids_sha256']:
        if 'normalized_chosen_equals_rejected' not in issues: issues.append('token_identical_preference')
    audit['issues'] = issues
    return audit


def longest_indices(audits):
    """At most four train-only indices: max full length for each arm/side."""
    train.require(bool(audits) and not any(a['issues'] for a in audits), 'all-row feasible audit required')
    chosen = set()
    for arm in train.ARMS:
        for side in ('chosen', 'rejected'):
            chosen.add(max(range(len(audits)), key=lambda i: (
                audits[i]['arms'][arm][side]['full_tokens'], -i)))
    return sorted(chosen)


def dpo_loss(chosen, rejected, reference_chosen, reference_rejected, beta=BETA):
    import torch.nn.functional as F
    train.require(math.isfinite(beta) and beta > 0, 'positive finite beta required')
    return -F.logsigmoid(beta * ((chosen - rejected) - (reference_chosen - reference_rejected)))


def sequential_coefficients(chosen, rejected, reference_chosen, reference_rejected, beta=BETA):
    """Exact chain-rule coefficients; no graph retained between two sequences."""
    import torch
    values = [chosen, rejected, reference_chosen, reference_rejected]
    train.require(all(math.isfinite(float(v)) for v in values) and math.isfinite(beta) and beta > 0,
                  'finite preference scores and positive beta required')
    margin = beta * ((float(chosen) - float(rejected)) - (float(reference_chosen) - float(reference_rejected)))
    scale = beta * torch.sigmoid(torch.tensor(-margin, dtype=torch.float64)).item()
    return -scale, scale


def sequence_logprob(model, feature):
    import torch
    import torch.nn.functional as F
    n = feature['prompt_tokens']; target = feature['input_ids'][n:]
    train.require(n > 0 and target, 'nonempty prompt/target required')
    device = model.get_input_embeddings().weight.device
    ids = torch.tensor([feature['input_ids']], device=device)
    # Non-reentrant checkpointing recomputes each FP32 CE chunk in backward.
    # This avoids retaining a vocabulary-sized FP32 tensor for every target token.
    output = model(input_ids=ids, attention_mask=torch.ones_like(ids), use_cache=False,
                   logits_to_keep=len(target) + 1)
    logits = output.logits[0, :-1]
    train.require(logits.shape[0] == len(target), 'causal target offset differs')
    labels = torch.tensor(target, device=device)
    def logp(part, gold):
        return -F.cross_entropy(part.float(), gold, reduction='sum')
    parts = []
    from torch.utils.checkpoint import checkpoint
    for start in range(0, len(target), 32):
        x, y = logits[start:start+32], labels[start:start+32]
        parts.append(checkpoint(logp, x, y, use_reentrant=False) if torch.is_grad_enabled() else logp(x, y))
    value = torch.stack(parts).sum()
    train.require(bool(torch.isfinite(value)), 'nonfinite sequence log probability')
    return value


def disable_dropout(model):
    import torch
    for module in model.modules():
        if isinstance(module, torch.nn.Dropout): module.p = 0.0


def probe_pair(model, pair):
    """Initial policy=reference. Four detached forwards + two backwards, no step.

    The two reference forwards are valid only in this no-update capacity pilot.
    A real trainer must preserve/cache the ORIGINAL reference, not moving policy.
    """
    import torch
    with torch.no_grad():
        reference = {s: float(sequence_logprob(model, pair[s])) for s in ('chosen', 'rejected')}
        policy = {s: float(sequence_logprob(model, pair[s])) for s in ('chosen', 'rejected')}
    train.require(all(abs(reference[s] - policy[s]) < 1e-5 for s in policy), 'initial reference/policy mismatch')
    coefficients = sequential_coefficients(policy['chosen'], policy['rejected'], reference['chosen'], reference['rejected'])
    model.zero_grad(set_to_none=True)
    for side, coefficient in zip(('chosen', 'rejected'), coefficients, strict=True):
        value = sequence_logprob(model, pair[side])
        train.require(abs(float(value.detach()) - policy[side]) < 1e-3, 'backward score differs from detached pass')
        (coefficient * value).backward()
        del value
    grads = [p.grad for p in model.parameters() if p.requires_grad and p.grad is not None]
    train.require(grads and all(bool(torch.isfinite(g).all()) for g in grads), 'missing/nonfinite preference gradients')
    norm = math.sqrt(sum(float(g.float().square().sum()) for g in grads))
    train.require(norm > 0 and math.isfinite(norm), 'zero/nonfinite preference gradient norm')
    return dict(initial_loss=math.log(2), reference=reference, policy=policy, gradient_norm=norm,
                optimizer_steps=0, actual_fit=False, moving_reference_allowed=False)
