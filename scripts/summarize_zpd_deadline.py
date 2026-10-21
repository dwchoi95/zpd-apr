"""Read completed artifacts only; print a deadline inventory, never run experiments.

No fitting, generation, execution, selection, gate recomputation, or file writes.
The caller may preserve stdout as a new analysis artifact. Historical gates are
copied verbatim, not replaced with a common post-hoc acceptance rule.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = "outputs/split-90-10/canonical-v5/analysis/"
OLD_REPORTS = {
    "development_valid32": "outputs/zpd-repair-development-20260918/run-v1/fit/report.json",
    "replication128": "outputs/zpd-repair-replication-20260921/run-v1/assessment/report.json",
    "pairwise_selected32_and_exposed128": "outputs/zpd-repair-pairwise-20260922/run-v1/report.json",
    "pairwise_new128": "outputs/zpd-repair-pairwise-replication-20260922/run-v1/assessment/report.json",
    "risk_three_separate_cohorts": "outputs/zpd-repair-risk-development-20260923/run-v1/fit/report.json",
    "structural_fixed_bank320": "outputs/zpd-repair-structure-cv-20260923/run-v1/report.json",
    "preservation_fixed_bank320": "outputs/zpd-repair-preservation-20260924/run-v1/report.json",
    "directed_history_fixed_bank320": "outputs/zpd-repair-directed-history-20260924/run-v2/assessment/report.json",
    "feedback_fixed_bank320": "outputs/zpd-repair-feedback-20260924/run-v1/assessment/report.json",
    "statement_progress_fixed_bank320": "outputs/zpd-repair-statement-progress-20260925/run-v1/assessment/report.json",
    "joint4131_fixed_bank320": "archive/zpd-joint-progress-run-20260925/run-v1/assessment/report.json",
    "bank_topset_fixed_bank320": "archive/zpd-bank-topset-run-20260925/run-v1/report.json",
    "public_execution_fixed_bank320": "archive/zpd-public-candidates-20261012/result/run-v1/report.json",
    "initial_transition_two_slots320": "archive/zpd-transition-generation-20261012/completed-private-v1/private-v1/evaluation/report.json",
    "history_action_c1_not_rr": "outputs/zpd-history-action-20260923/run-v1/report.json",
    "history_action_c2_not_rr": "outputs/zpd-history-action-blocked-20260924/run-v1/report.json",
    "history_action_c3_not_rr": "outputs/zpd-history-feedback-coupling-20260924/run-v1/report.json",
}


def read(relative):
    return json.loads((ROOT / relative).read_bytes())


def sha(relative):
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def metric_nodes(value, path=""):
    """Retain complete aggregate count blocks, never individual predictions."""
    if not isinstance(value, dict):
        return []
    if isinstance(value.get("counts"), dict) and any(
        k in value["counts"] for k in ("stable_ac", "rr_lower_bound")
    ):
        metrics = value.get("metrics") or {}
        return [{"json_path": path, "examples": value.get("examples", metrics.get("examples")),
                 "counts": value["counts"]}]
    metrics = value.get("metrics") or value
    if "rr_lower_bound" in metrics and "examples" in metrics:
        n = metrics["examples"]
        counts = {k: n * metrics[k] for k in ("rr_lower_bound", "rr_upper_bound",
                  "regression_rate_lower_bound", "regression_rate_upper_bound", "unknown", "noop")
                  if k in metrics}
        assert all(abs(v - round(v)) < 1e-7 for v in counts.values())
        return [{"json_path": path, "examples": n, "counts": {k: round(v) for k, v in counts.items()},
                 "counts_derived_from_reported_instance_rates": True}]
    return [row for key, child in value.items()
            if key not in {"predictions", "decisions", "folds", "fold_results", "problem_results",
                           "original_status_subgroups", "current_status_subgroups",
                           "current_status_subgroup_folds", "strata"}
            for row in metric_nodes(child, path + "/" + key)]


def original_gates(value, path=""):
    if not isinstance(value, dict):
        return []
    return ([{"json_path": path + "/" + k, "value": v} for k, v in value.items()
             if k in {"gate", "decision", "component_gate", "development_gate", "original_gate"}]
            + [g for k, v in value.items() if k in {"frozen_original", "matched_execution"}
               for g in original_gates(v, path + "/" + k)])


def parent_report_binding(relative):
    """Check available direct manifest links; absence is disclosed, not PASS."""
    report = ROOT / relative
    bindings = []
    for parent in list(report.parents)[:4]:
        if not parent.is_relative_to(ROOT):
            break
        for marker in ("COMPLETE.json", "VERIFIED_COMPLETE.json", "STAGE_COMPLETE.json"):
            certificate = parent / marker
            if not certificate.is_file():
                continue
            value = json.loads(certificate.read_bytes())
            files = value.get("files_sha256", {})
            name = str(report.relative_to(parent))
            if name in files:
                assert files[name] == sha(relative), f"report seal drift: {relative}"
                bindings.append({"certificate": str(certificate.relative_to(ROOT)),
                                 "sha256": sha(certificate.relative_to(ROOT)), "report_digest_matched": True})
    return bindings


def recent_path(family):
    if family == "zpd-paired-history-run-20261015":
        return "archive/zpd-paired-history-20261015-recovery/original-family/COORDINATOR_FAILED.json"
    if family == "zpd-transition-diagnosis-20261013":
        return "archive/zpd-transition-generation-20261013/completed-replay-v1/diagnosis-complete-v1/report.json"
    base = "archive/" + family
    if family in ("zpd-current-last-20261013", "zpd-full-source-20261014"):
        return base + "/completed-v1/REPORT.json"
    if "diagnosis" in family:
        return base + "/diagnosis-complete-v1/report.json"
    return base + "/REPORT.json"


def build():
    policy = read("analysis_protocols/zpd-deadline-20261021.json")
    live = read("analysis_protocols/zpd-deadline-live-audit-20261021.json")
    snapshot = read("analysis_protocols/zpd-deadline-observer-20261021.json")
    assert policy["new_experiments_after_deadline"] is False
    assert not live["active_units"].strip() and not live["gpu_processes"].strip()
    assert live["matching_live_experiment_processes"] == []
    older = {}
    for label, relative in OLD_REPORTS.items():
        data = read(relative)
        older[label] = {"source": relative, "sha256": sha(relative),
                        "direct_report_bindings": parent_report_binding(relative),
                        "aggregates": metric_nodes(data), "original_gates": original_gates(data)}
        if label.endswith("not_rr"):
            older[label]["nll"] = {k: v["user_equal_masked_nll"] for k, v in data["results"].items()}
            older[label]["oof_prefixes"] = data["total_oof_supported"]
    recent = []
    for row in snapshot["experiments"]:
        relative = recent_path(row["family"])
        data = read(relative)
        entry = {"family": row["family"], "state": row["state"], "source": relative,
                 "sha256": sha(relative), "live_verified_certificate_sha256": row.get("certificate_sha256"),
                 "source_report_bindings": parent_report_binding(relative), "observed_results": row.get("results"),
                 "original_gates": original_gates(data), "counts": data.get("counts"),
                 "fold_counts": {k: metric_nodes(v) for k, v in data.get("folds", {}).items()},
                 "current_status_counts": {k: metric_nodes(v) for k, v in data.get("current_status_subgroups", {}).items()}}
        # Preserve failure reason and do not convert readiness into repair success.
        if row["state"] == "error":
            entry["retained_failure"] = data
        if "performance_measured" in data:
            entry["performance_measured"] = data["performance_measured"]
        recent.append(entry)
    paper_names = ["fse2027-result-bridge.json", "fse2027-current-only-deployment-ladder.json",
                   "fse2027-current-only-factorial-corrected.json", "fse2027-paired-java-control.json"]
    paper = {name: {"source": PAPER + name, "sha256": sha(PAPER + name)} for name in paper_names}
    ladder = read(PAPER + paper_names[1])
    paper[paper_names[1]]["methods"] = {
        s: {m: {k: v[k] for k in ("examples", "problems", "rr", "problem_balanced_rr")}
            for m, v in cell["methods"].items()} for s, cell in ladder["splits"].items()}
    report_notes = sorted({p for pattern in ("zpd-*result*.json", "zpd-*result*.md", "zpd-*decision*.md",
                                            "zpd-*completion*.md", "zpd-*status*.md")
                           for p in (ROOT / "analysis_protocols").glob(pattern)
                           if "deadline" not in p.name})
    failures = sorted({p for base in ("outputs", "archive")
                       for directory in (ROOT / base).glob("zpd-*") if directory.is_dir()
                       for p in directory.rglob("*FAILED*.json")})
    return {"version": "deadline_saved_evidence_inventory_v1", "deadline": policy["deadline"],
            "no_new_experiment": True, "new_gate_or_ranker": False,
            "recommendation": {"canonical_release": "retain canonical-v5; no new ZPD promotion",
                               "existing_deployment_reference": "current-only Answer-3Seed, historical Transformers stack",
                               "not_a_pass_of_new_C_H_HS_U_gate": True},
            "comparison_boundaries": ["Paper Seen997 and Unseen250 are separate populations.",
                                      "Java181 and exercise-heldout304 are separate populations.",
                                      "Pilot32 and the two128 replications are separate populations.",
                                      "Fixed-bank320 uses up to8 draws, 2544 memberships; new-generation320 uses2 slots/arm.",
                                      "Public-execution selection adds execution cost; full-source runs use different execution blocks.",
                                      "NLL, training loss, readiness and oracle availability are not selected repair RR.",
                                      "Historical 4-of-5 and later 5-of-5 gates remain exactly as originally declared."],
            "live_audit": {"source": "analysis_protocols/zpd-deadline-live-audit-20261021.json",
                           "sha256": sha("analysis_protocols/zpd-deadline-live-audit-20261021.json")},
            "paper_historical_results": paper, "older_separate_experiments": older,
            "recent_families": recent,
            "retained_failure_markers": [{"source": str(p.relative_to(ROOT)),
                                          "sha256": sha(p.relative_to(ROOT)),
                                          "status": "historical_failure_not_overwritten"} for p in failures],
            "paper_analysis_file_index": [{"source": str(p.relative_to(ROOT)),
                                            "sha256": sha(p.relative_to(ROOT))}
                                           for p in sorted((ROOT / PAPER).glob("*.json"))],
            "result_decision_document_index": [{"path": str(p.relative_to(ROOT)),
                                                 "sha256": sha(p.relative_to(ROOT))} for p in report_notes]}


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
