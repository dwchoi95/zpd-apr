"""Train-only crossfit variance planning. Never selects or opens a test model."""
from collections import defaultdict
import hashlib
from statistics import NormalDist

import numpy as np

from scripts.audit_zpd_history_support import match_donors
from scripts.zpd_history_predictor import LABELS, features, lexical_tokens, validate_rows

SPEC = {"folds": 5, "salt": "zpd-history-power-20260915", "alpha": 1e-4,
        "seed": 2027, "epochs": 20, "one_sided_alpha": .025, "power": .80,
        "selection": "none; fixed hyperparameters", "variance": "sample ddof=1 user means"}


def user_fold(user_id):
    return int(hashlib.sha256((SPEC["salt"] + ":" + str(user_id)).encode()).hexdigest(), 16) % 5


def summarize_difference(user_values, prospective_test_users):
    if not isinstance(prospective_test_users, int) or prospective_test_users < 0:
        raise ValueError("fixed prospective test user count required")
    values = np.array(list(user_values.values()), dtype=np.float64)
    variance = float(values.var(ddof=1)) if len(values) >= 2 else None
    z = NormalDist().inv_cdf(1 - SPEC["one_sided_alpha"]) + NormalDist().inv_cdf(SPEC["power"])
    mde = z * np.sqrt(variance / prospective_test_users) if variance is not None and prospective_test_users else None
    return {"user_count": len(values), "mean_difference": float(values.mean()) if len(values) else None,
            "sample_variance": variance, "prospective_test_user_count": prospective_test_users,
            "detectable_nll_difference": float(mde) if mde is not None else None,
            "status": "estimated" if mde is not None else "not_evaluable",
            "user_differences": dict(sorted(user_values.items()))}


def summaries(rows):
    return [{"example_id": r["example_id"], "user_id": r["user_id"],
             "problem_id": r["problem_id"], "split": "train", "timestamp": r["timestamp"],
             "current_verdict": r.get("matching_current_verdict", r["current_verdict"]),
             "prior_count": len(r["history"]),
             "prior_tokens": sum(len(lexical_tokens(h["code"])[0]) for h in r["history"])}
            for r in rows]


def fit_fixed(train, held, condition, *, n_features, progress_callback, fold, contrast):
    from sklearn.linear_model import SGDClassifier
    x, z = features(train, condition, n_features), features(held, condition, n_features)
    y = np.array([LABELS.index(r["next_label"]) for r in train])
    counts = defaultdict(int)
    for r in train:
        counts[r["user_id"]] += 1
    weights = np.array([1/counts[r["user_id"]] for r in train])
    weights /= weights.mean()
    model = SGDClassifier(loss="log_loss", penalty="l2", alpha=SPEC["alpha"],
                          learning_rate="optimal", shuffle=False, random_state=SPEC["seed"])
    rng = np.random.default_rng(SPEC["seed"])
    for epoch in range(SPEC["epochs"]):
        order = rng.permutation(len(train))
        model.partial_fit(x[order], y[order], classes=np.arange(len(LABELS)), sample_weight=weights[order])
        if progress_callback:
            progress_callback({"fold": fold, "contrast": contrast, "condition": condition, "epoch": epoch+1,
                               "completed_train_example_exposures": (epoch+1)*len(train),
                               "total_train_example_exposures": SPEC["epochs"]*len(train)})
    p = model.predict_proba(z)
    target = np.array([LABELS.index(r["next_label"]) for r in held])
    return -np.log(np.clip(p[np.arange(len(held)), target], 1e-15, 1))


def estimate_train_power(rows, *, prospective_test_users, prospective_matched_test_users,
                         provenance_verified=False, implementation_frozen=False,
                         n_features=2**18, progress_callback=None):
    """No valid/test records accepted, even for constructing fold donors.

    The caller supplies label-blind fixed test user counts, not test labels.
    Returned variance/MDE is planning evidence, never an automatic ready flag.
    """
    if not provenance_verified or not implementation_frozen:
        raise RuntimeError("provenance and implementation must be frozen before fitting")
    for count in (prospective_test_users, prospective_matched_test_users):
        summarize_difference({}, count)
    if any(r["split"] != "train" for r in rows):
        raise ValueError("power accepts train rows only")
    validate_rows(rows)
    by_id = {r["example_id"]: r for r in rows}
    records = summaries(rows)
    oof, reports = [], []
    for fold in range(5):
        train = [r for r in rows if user_fold(r["user_id"]) != fold]
        held = [r for r in rows if user_fold(r["user_id"]) == fold]
        if not train or not held:
            reports.append({"fold": fold, "status": "empty_fold", "train_rows": len(train), "held_rows": len(held)})
            continue
        allowed = {r["user_id"] for r in train}
        mapping = match_donors(records, allowed_donor_users=allowed)
        matched = {}
        for subset, members in (("train", train), ("held", held)):
            matched[subset] = []
            for r in members:
                donor = mapping[r["example_id"]]
                if donor is not None:
                    d = by_id[donor]
                    if d["user_id"] not in allowed or d["user_id"] == r["user_id"] or d["timestamp"] >= r["timestamp"]:
                        raise ValueError("invalid fold donor")
                    matched[subset].append(dict(r, donor_history=d["history"]))
        report = {"fold": fold, "status": "evaluated", "train_rows": len(train), "held_rows": len(held),
                  "matched_train_rows": len(matched["train"]), "matched_held_rows": len(matched["held"]),
                  "donor_users": sorted(allowed),
                  "held_users": sorted({r["user_id"] for r in held})}
        for contrast, a, b, tr, ho in (("C_H", "C", "H", train, held),
                                       ("U_H", "U", "H", matched["train"], matched["held"])):
            if not tr or not ho:
                report[contrast] = "not_evaluable"
                continue
            left, right = [fit_fixed(tr, ho, condition, n_features=n_features,
                                    progress_callback=progress_callback, fold=fold, contrast=contrast)
                           for condition in (a, b)]
            for r, l, h in zip(ho, left, right):
                oof.append({"example_id": r["example_id"], "user_id": r["user_id"],
                            "fold": fold, "contrast": contrast,
                            "baseline_nll": float(l), "history_nll": float(h), "difference": float(l-h)})
            report[contrast] = "evaluated"
        reports.append(report)
    result = {"spec": SPEC, "folds": reports, "oof_rows": oof,
              "scope": "train-only planning; no test labels and no automatic gate permission"}
    for contrast, count in (("C_H", prospective_test_users), ("U_H", prospective_matched_test_users)):
        users = defaultdict(list)
        losses = defaultdict(list)
        for row in oof:
            if row["contrast"] == contrast:
                users[row["user_id"]].append(row["difference"])
                losses[row["user_id"]].append((row["baseline_nll"], row["history_nll"]))
        result[contrast] = summarize_difference({u: float(np.mean(v)) for u, v in users.items()}, count)
        result[contrast]["per_user_losses"] = {
            u: {"baseline_nll": float(np.mean(v, axis=0)[0]),
                "history_nll": float(np.mean(v, axis=0)[1]), "rows": len(v)}
            for u, v in sorted(losses.items())}
    return result
