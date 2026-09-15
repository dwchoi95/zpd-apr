"""Post-result donor balance audit, with durable per-pair AST distance records."""
import argparse
import ast
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import statistics

from scripts.analyze_patch_locality import source_tokens


def read(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def stats(values):
    values = sorted(x for x in values if x is not None)
    return {"n": len(values), "mean": statistics.fmean(values) if values else None, "median": statistics.median(values) if values else None, "p95": values[min(len(values)-1, int(.95*len(values)))] if values else None}


def distance(job):
    from src.repair.evaluate import tree_edit_distance
    key, current, own, peer = job
    return {"example_id": key, "same_ast_ted": tree_edit_distance(current, own), "peer_ast_ted": tree_edit_distance(current, peer)}


def features(rows):
    def nodes(code):
        try:
            return sum(1 for _ in ast.walk(ast.parse(code)))
        except (SyntaxError, ValueError):
            return None
    return {"records": len(rows), "target_chars": stats([len(r["target_code"]) for r in rows]), "target_tokens": stats([len(source_tokens(r["target_code"])) for r in rows]), "target_ast_nodes": stats([nodes(r["target_code"]) for r in rows]), "unique_target_code_fraction": len({hashlib.sha256(r["target_code"].encode()).hexdigest() for r in rows}) / len(rows) if rows else None}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    report = {"role": "post-result distribution audit; no matching or outcome changes", "splits": {}}
    for split in ("train", "valid"):
        pool = read(args.root / f"{split}-progress.jsonl")
        same = read(args.root / "cross-user-target-control" / f"{split}-same-user.jsonl")
        peer = read(args.root / "cross-user-target-control" / f"{split}-cross-user.jsonl")
        peer_by_id = {r["example_id"]: r for r in peer}
        used_sources = {r["history"][-1]["submission_id"] for r in same}
        excluded = [r for r in pool if r["history"][-1]["submission_id"] not in used_sources]
        cache = args.output.with_name(f"peer-ast-{split}.jsonl")
        done = {r["example_id"]: r for r in read(cache)} if cache.exists() else {}
        jobs = [(r["example_id"], r["history"][-1]["code"], r["target_code"], peer_by_id[r["example_id"]]["target_code"]) for r in same if r["example_id"] not in done]
        with ProcessPoolExecutor(max_workers=args.workers) as executor, cache.open("a") as sink:
            futures = [executor.submit(distance, job) for job in jobs]
            for future in as_completed(futures):
                row = future.result()
                done[row["example_id"]] = row
                sink.write(json.dumps(row) + "\n")
                sink.flush()
        report["splits"][split] = {"before": features(pool), "excluded": features(excluded), "same": features(same), "peer": features(peer), "same_token_distance": stats([r["target_token_edit_distance"] for r in same]), "peer_token_distance": stats([r["matched_target_token_edit_distance"] for r in peer]), "same_ast_distance": stats([r["same_ast_ted"] for r in done.values()]), "peer_ast_distance": stats([r["peer_ast_ted"] for r in done.values()])}
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
