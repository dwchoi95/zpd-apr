# Artifact check of the public main branch (2026-10-31)

Authorized in `zpd-deadline-extension-20261023.json` (scope entry of 2026-10-31); nothing here is reported in the paper.

- A fresh clone of GitHub `main` (1e3a74b0) joined its three adapters (`adapters/answer-{2027,2028,2029}`) and passed
  `sha256sum -c adapters/SHA256SUMS`, locally and on UbuntuServer (the server cannot clone the private repository, so
  the local clone was copied to `.runtime/artifact-check-20261031/repo`).
- Unit `zpd-artifact-check-20261031` ran the README command (`run.py generate --prompt D --base-model
  Qwen/Qwen2.5-Coder-7B-Instruct --adapter adapters/answer-<seed> --batch-size 4 --max-new-tokens 4096`, then
  `run.py evaluate`) on the first 40 RQ1 inputs (16:58–17:05 KST, exit 0).
- Against the stored RQ1 runs (`outputs/histra-bench-20261023/eval`): generated code, raw generation, verdict, pass
  rate, and both TEDs identical on 40/40 inputs for each seed (repaired 10, 11, 8 as stored).
- `compose_answer_seed_control.py --forward-fallback` over the three evaluations reproduces `output/approaches/zpdpatch.jsonl`
  of the artifact on all 40 inputs (repaired, selected source, pass rate, TED, returned code).
