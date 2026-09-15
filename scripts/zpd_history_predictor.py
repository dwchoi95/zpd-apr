"""CPU history-gate engine; no CLI and no automatic fitting.

Real use requires a frozen implementation amendment, verified input provenance,
and train-only power analysis. This module does not perform inferential testing
or claim that a predictive signal establishes educational effectiveness.
"""
from __future__ import annotations

from collections import Counter
from difflib import SequenceMatcher
import io
import tokenize

import numpy as np


LABELS = ("AC", "WA", "CE", "RE", "RESOURCE", "OTHER")
SEEDS = (2027, 2028, 2029)
ALPHAS = (1e-5, 1e-4, 1e-3)
ARMS = ("C_F", "H_F", "S_F", "H_M", "U_M")
SPEC = {
    "version": "history-predictor-implementation-v1-proposed",
    "dtype": "float64", "epochs": 20, "hash_features_per_block": 2**18,
    "code_blocks": "token uni/bi and char 3-5; signed; individually L2",
    "block_weights": "equal, no final joint normalization",
    "history": "mean per-code vectors, nominal frequencies/transitions/last",
    "numeric": "log1p nonnegative nuisance and structural statistics",
    "token_edit": "1-SequenceMatcher(autojunk=False).ratio over lexical tokens",
    "optimizer": "SGD log_loss L2 optimal; manual epoch permutation",
    "weight": "inverse training user frequency, scaled to mean one",
    "selection": "mean-seed validation user-equal NLL; ties larger alpha",
}


def lexical_tokens(code):
    """Whitespace-independent lexical tokens; partial tokens retained on failure."""
    result, failed = [], False
    try:
        for tok in tokenize.generate_tokens(io.StringIO(code).readline):
            if tok.type == tokenize.ERRORTOKEN and tok.string.strip():
                failed = True
            if tok.type not in (tokenize.ENCODING, tokenize.ENDMARKER,
                                tokenize.NEWLINE, tokenize.NL,
                                tokenize.INDENT, tokenize.DEDENT):
                result.append(tok.string)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        failed = True
    return result, failed


def validate_rows(rows):
    seen, users = set(), {}
    for row in rows:
        if row["example_id"] in seen:
            raise ValueError("duplicate example_id")
        seen.add(row["example_id"])
        if row["split"] not in ("train", "valid", "test"):
            raise ValueError("unknown split")
        if users.setdefault(row["user_id"], row["split"]) != row["split"]:
            raise ValueError("user leakage between splits")
        if row["current_verdict"] not in LABELS or row["current_verdict"] == "AC":
            raise ValueError("current verdict must be canonical non-AC")
        if not row["history"]:
            raise ValueError("history must contain prior attempt")
        for key in ("history", "donor_history"):
            history = row.get(key)
            if history is None:
                continue
            if not history:
                raise ValueError("empty donor/history is not available")
            times = [h["timestamp"] for h in history]
            if any(a >= b for a, b in zip(times, times[1:])) or any(t >= row["timestamp"] for t in times):
                raise ValueError("future or unordered history")
            for h in history:
                if set(h) - {"code", "verdict", "timestamp"}:
                    raise ValueError("history feature allowlist violation")
                if h["verdict"] not in LABELS:
                    raise ValueError("noncanonical verdict")


def code_vectors(codes, n_features=2**18):
    from scipy.sparse import hstack
    from sklearn.feature_extraction import FeatureHasher
    from sklearn.preprocessing import normalize
    lexical, chars = [], []
    for code in codes:
        tokens, _ = lexical_tokens(code)
        lexical.append(Counter(["u:" + t for t in tokens] +
                               ["b:" + repr(pair) for pair in zip(tokens, tokens[1:])]))
        chars.append(Counter(code[i:i+n] for n in (3, 4, 5)
                             for i in range(max(0, len(code)-n+1))))
    hasher = FeatureHasher(n_features=n_features, alternate_sign=True, dtype=np.float64)
    return hstack([normalize(hasher.transform(lexical)),
                   normalize(hasher.transform(chars))], format="csr")


def nominal_history(history):
    result = np.zeros(6 + 36 + 6, dtype=np.float64)
    verdicts = [LABELS.index(h["verdict"]) for h in history]
    for verdict in verdicts:
        result[verdict] += 1 / len(verdicts)
    for a, b in zip(verdicts, verdicts[1:]):
        result[6 + 6*a + b] += 1 / max(1, len(verdicts)-1)
    result[42 + verdicts[-1]] = 1
    return result


def structural(row):
    h = row["history"] + [{"code": row["current_code"],
                             "verdict": row["current_verdict"],
                             "timestamp": row["timestamp"]}]
    edits = [1 - SequenceMatcher(None, lexical_tokens(a["code"])[0],
                                 lexical_tokens(b["code"])[0], autojunk=False).ratio()
             for a, b in zip(h, h[1:])]
    gaps = [b["timestamp"] - a["timestamp"] for a, b in zip(h, h[1:])]
    run = 0
    for a, b in reversed(list(zip(h, h[1:]))):
        if a["code"] != b["code"]:
            break
        run += 1
    return np.log1p([
        sum(x["verdict"] == row["current_verdict"] for x in h[:-1]),
        sum(a["verdict"] != b["verdict"] for a, b in zip(h, h[1:])),
        run, np.mean(edits), np.max(edits), edits[-1],
        np.mean(gaps), np.max(gaps), gaps[-1],
    ])


def features(rows, condition, n_features=2**18):
    """Never reads next_label or IDs. U requires prevalidated donor matching."""
    from scipy.sparse import csr_matrix, hstack
    if condition not in ("C", "H", "U", "S"):
        raise ValueError("unknown condition")
    nuisance = []
    for row in rows:
        verdict = [float(row["current_verdict"] == label) for label in LABELS]
        nuisance.append(verdict + [float(lexical_tokens(row["current_code"])[1])] +
                        list(np.log1p([len(row["current_code"]), len(row["history"]),
                                       row["timestamp"] - row["history"][0]["timestamp"]])))
    blocks = [code_vectors([r["current_code"] for r in rows], n_features),
              csr_matrix(nuisance)]
    if condition in ("H", "U"):
        histories = [r["history"] if condition == "H" else r.get("donor_history")
                     for r in rows]
        if any(not h for h in histories):
            raise ValueError("U unavailable; select fixed matched subset before fitting")
        unique = dict.fromkeys(x["code"] for h in histories for x in h)
        lookup = {code: i for i, code in enumerate(unique)}
        rr, cc, values = [], [], []
        for i, history in enumerate(histories):
            for code, count in Counter(x["code"] for x in history).items():
                rr.append(i)
                cc.append(lookup[code])
                values.append(count / len(history))
        pooling = csr_matrix((values, (rr, cc)), shape=(len(rows), len(unique)))
        blocks.extend([pooling @ code_vectors(list(unique), n_features),
                       csr_matrix([nominal_history(h) for h in histories])])
    elif condition == "S":
        blocks.append(csr_matrix([structural(r) for r in rows]))
    return hstack(blocks, format="csr", dtype=np.float64)


def user_equal_nll(labels, probabilities, users):
    losses = -np.log(np.clip(probabilities[np.arange(len(labels)), labels], 1e-15, 1))
    return float(np.mean([losses[np.asarray(users) == user].mean()
                          for user in sorted(set(users))]))


class FrozenGate:
    """One workflow instance selects on validation and opens test once.

    Durable test-consumption locking and source/donor manifests belong to the
    calling runner; this is deliberately not a standalone experiment launcher.
    """
    def __init__(self, rows, *, provenance_verified=False,
                 implementation_frozen=False, train_power_recorded=False,
                 n_features=2**18):
        validate_rows(rows)
        self.rows = rows
        self.ready = provenance_verified and implementation_frozen and train_power_recorded
        self.n_features = n_features
        self.selected = {}
        self.validation = {}
        self.test_opened = False

    def select(self, condition, progress_callback=None):
        from sklearn.linear_model import SGDClassifier
        if condition not in ARMS:
            raise ValueError("use frozen full/matched arm name")
        if not self.ready or self.test_opened or condition in self.selected:
            raise RuntimeError("unverified, repeated selection, or test already consumed")
        subsets = {s: [r for r in self.rows if r["split"] == s and
                       (not condition.endswith("_M") or r.get("donor_history") is not None)]
                   for s in ("train", "valid")}
        if not all(subsets.values()):
            raise ValueError("empty train/valid subset; not evaluable")
        train, valid = subsets["train"], subsets["valid"]
        xt, xv = [features(subsets[s], condition[0], self.n_features) for s in ("train", "valid")]
        yt, yv = [np.array([LABELS.index(r["next_label"]) for r in subsets[s]])
                  for s in ("train", "valid")]
        counts = Counter(r["user_id"] for r in train)
        weights = np.array([1/counts[r["user_id"]] for r in train])
        weights /= weights.mean()
        candidates = []
        completed = 0
        total = len(train) * len(ALPHAS) * len(SEEDS) * SPEC["epochs"]
        for alpha in ALPHAS:
            models, predictions = [], []
            for seed in SEEDS:
                model = SGDClassifier(loss="log_loss", penalty="l2", alpha=alpha,
                                      learning_rate="optimal", shuffle=False,
                                      random_state=seed)
                rng = np.random.default_rng(seed)
                for epoch in range(SPEC["epochs"]):
                    order = rng.permutation(len(train))
                    model.partial_fit(xt[order], yt[order], classes=np.arange(6),
                                      sample_weight=weights[order])
                    completed += len(train)
                    if progress_callback is not None:
                        progress_callback({"condition": condition, "alpha": alpha,
                                           "seed": seed, "epoch": epoch + 1,
                                           "completed_train_example_exposures": completed,
                                           "total_train_example_exposures": total,
                                           "unique_train_examples": len(train)})
                models.append(model)
                predictions.append(model.predict_proba(xv))
            seed_scores = [user_equal_nll(yv, p, [r["user_id"] for r in valid])
                           for p in predictions]
            candidates.append((float(np.mean(seed_scores)), -alpha, models, seed_scores))
        best = min(candidates, key=lambda c: c[:2])
        self.selected[condition] = best[2]
        self.validation[condition] = {"selected_alpha": -best[1],
                                     "train_example_ids": [r["example_id"] for r in train],
                                     "valid_example_ids": [r["example_id"] for r in valid],
                                     "candidates": [{"alpha": -c[1], "seed_nll": c[3]}
                                                    for c in candidates]}
        return self.validation[condition]

    def open_test_once(self):
        if self.test_opened or set(self.selected) != set(ARMS):
            raise RuntimeError("all conditions must be frozen; test can open once")
        self.test_opened = True
        results = {}
        for condition, models in self.selected.items():
            rows = [r for r in self.rows if r["split"] == "test" and
                    (not condition.endswith("_M") or r.get("donor_history") is not None)]
            if not rows:
                results[condition] = {"status": "not_evaluable"}
                continue
            x = features(rows, condition[0], self.n_features)
            ps = np.stack([model.predict_proba(x) for model in models])
            results[condition] = {"example_ids": [r["example_id"] for r in rows],
                                  "labels": [LABELS.index(r["next_label"]) for r in rows],
                                  "seed_probabilities": ps, "probabilities": ps.mean(axis=0)}
        return results
