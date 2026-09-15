"""Nominal evidence features from an explicitly observed chronological prefix.

This isolated prototype is not connected to v5. Callers must establish raw-prefix
provenance and the observation cutoff externally: timestamps cannot prove that
omitted submissions or future records were not supplied. No readiness, learning,
or ZPD inference is made. Replay stability is also an external prerequisite.
"""

from __future__ import annotations

from collections import Counter
import math
from typing import Any, Mapping, Sequence


_ROW_KEYS = {"submission_id", "timestamp", "code", "verdict", "testcase_evidence"}
_EVIDENCE_KEYS = {"universe_id", "protocol_id", "complete", "outcomes"}
_ALIASES = {"Accepted": "AC", "Wrong Answer": "WA", "Runtime Error": "RE",
            "Time Limit Exceeded": "TLE", "Memory Limit Exceeded": "MLE",
            "Compilation Error": "CE", "Compile Error": "CE"}
_KNOWN = {"AC", "WA", "RE", "TLE", "MLE", "CE"}


def _verdict(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError("verdict must be a nonempty string or None")
    return _ALIASES.get(value, value)


def _snapshot(row: Mapping[str, Any]) -> dict[str, Any]:
    raw = row.get("testcase_evidence")
    if raw is None:
        return {"status": "unknown", "reason": "missing_evidence", "outcomes": None}
    if not isinstance(raw, Mapping) or set(raw) != _EVIDENCE_KEYS:
        raise ValueError("testcase evidence requires exactly the documented keys")
    if not all(isinstance(raw[k], str) and raw[k] for k in ("universe_id", "protocol_id")):
        raise ValueError("nonempty universe_id and protocol_id required")
    if type(raw["complete"]) is not bool:
        raise ValueError("complete must be a boolean")
    if not isinstance(raw["outcomes"], Mapping):
        raise ValueError("outcomes must be a mapping")
    if any(not isinstance(k, str) or not k for k in raw["outcomes"]):
        raise ValueError("test identities must be nonempty strings")
    outcomes = {k: _verdict(v) for k, v in raw["outcomes"].items()}
    reason = ("incomplete_evidence" if not raw["complete"] else
              "empty_universe" if not outcomes else
              "unknown_test_verdict" if any(v not in _KNOWN for v in outcomes.values()) else None)
    return {"status": "known" if reason is None else "unknown", "reason": reason,
            "universe_id": raw["universe_id"], "protocol_id": raw["protocol_id"],
            "complete": raw["complete"], "outcomes": outcomes}


def _transition(before: Mapping[str, Any], after: Mapping[str, Any],
                old: Mapping[str, Any], new: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "verdict_transition": (_verdict(before["verdict"]), _verdict(after["verdict"])),
        "exact_same_code": before["code"] == after["code"],
        "test_status": "unknown", "new_passes": None, "lost_passes": None,
        "repeated_failed_cases": None, "test_transitions": None,
        "unchanged_code_execution_disagreement": None,
    }
    if old["status"] != "known" or new["status"] != "known":
        return result
    a, b = old["outcomes"], new["outcomes"]
    result.update(test_status="known",
                  new_passes=sorted(k for k in a if a[k] != "AC" and b[k] == "AC"),
                  lost_passes=sorted(k for k in a if a[k] == "AC" and b[k] != "AC"),
                  repeated_failed_cases=sorted(k for k in a if a[k] != "AC" and b[k] != "AC"),
                  test_transitions=[{"before": x, "after": y, "count": n}
                                    for (x, y), n in sorted(Counter((a[k], b[k]) for k in a).items())],
                  unchanged_code_execution_disagreement=(before["code"] == after["code"] and a != b))
    return result


def build_observed_prefix_state(prefix: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Return current-only, prior-only and boundary features without truncation.

    Each row requires submission_id, timestamp, code, verdict; the only optional
    field is testcase_evidence with universe_id, protocol_id, complete, outcomes.
    Extra keys (including labels, target code and full-trajectory length) fail.
    The last row is current. Missing evidence is unknown, not zero improvement.
    Explicitly incompatible universes/protocols fail, even for partial evidence.
    """
    if not prefix:
        raise ValueError("nonempty observed prefix required")
    seen_ids: set[str] = set()
    previous_time = -math.inf
    snapshots = []
    universe_protocol = None
    complete_keys = None
    observed_keys: set[str] = set()
    for row in prefix:
        if not isinstance(row, Mapping) or not (_ROW_KEYS - {"testcase_evidence"}) <= set(row) <= _ROW_KEYS:
            raise ValueError("unexpected or missing prefix fields")
        sid = row["submission_id"]
        if not isinstance(sid, str) or not sid or sid in seen_ids:
            raise ValueError("unique nonempty submission_id required")
        seen_ids.add(sid)
        timestamp = row["timestamp"]
        if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)) or not math.isfinite(timestamp):
            raise ValueError("finite timestamp required")
        if timestamp < previous_time:
            raise ValueError("timestamps must be nondecreasing")
        previous_time = timestamp
        if not isinstance(row["code"], str):
            raise ValueError("code must be a string")
        _verdict(row["verdict"])
        snapshot = _snapshot(row)
        snapshots.append(snapshot)
        if snapshot.get("universe_id") is not None:
            identity = (snapshot["universe_id"], snapshot["protocol_id"])
            if universe_protocol is not None and identity != universe_protocol:
                raise ValueError("inconsistent testcase universe or execution protocol")
            universe_protocol = identity
            keys = set(snapshot["outcomes"])
            observed_keys.update(keys)
            if snapshot["complete"]:
                if complete_keys is not None and keys != complete_keys:
                    raise ValueError("inconsistent complete testcase identities")
                complete_keys = keys
    if complete_keys is not None and not observed_keys <= complete_keys:
        raise ValueError("partial evidence contains out-of-universe testcase identities")

    transitions = [_transition(prefix[i - 1], prefix[i], snapshots[i - 1], snapshots[i])
                   for i in range(1, len(prefix))]
    prior = prefix[:-1]
    counts = Counter(_verdict(row["verdict"]) for row in prior)
    prior_transitions = transitions[:-1]
    nominal = Counter(t["verdict_transition"] for t in prior_transitions)
    current = prefix[-1]
    return {
        "schema_version": "observed-prefix-v1",
        "current": {"code_characters": len(current["code"]),
                    "verdict": _verdict(current["verdict"]), "execution": snapshots[-1]},
        "history": {
            "observed_prior_submissions": len(prior),
            "verdict_counts": dict(counts),
            "nominal_transition_counts": [{"before": a, "after": b, "count": n}
                                          for (a, b), n in nominal.items()],
            "adjacent_exact_code_repeats": sum(t["exact_same_code"] for t in prior_transitions),
            "adjacent_same_failed_verdict": sum(a == b and a in _KNOWN - {"AC"}
                                                for a, b in (t["verdict_transition"] for t in prior_transitions)),
            "transitions": prior_transitions,
        },
        "current_vs_history": {
            "prior_exact_code_matches": sum(row["code"] == current["code"] for row in prior),
            "last_transition": transitions[-1] if transitions else None,
        },
        "audit": {"timestamp_ties": sum(prefix[i]["timestamp"] == prefix[i - 1]["timestamp"]
                                         for i in range(1, len(prefix))),
                  "unknown_evidence_count": sum(s["status"] != "known" for s in snapshots)},
    }
