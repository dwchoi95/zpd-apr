# Artifact check of the rebuilt main tree (2026-11-03)

Authorized in `zpd-deadline-extension-20261023.json` (scope entry of 2026-11-03); nothing here is reported in the paper.
The tree checked is the main tree assembled for the repository cleanup (78 files under `src/`, `run.py`,
`requirements.txt`, `requirements-vllm.txt`, `docker/java`, `output.tar.xz`, `output/models` with twelve adapters split
into 48 parts), staged at `/private/tmp/claude-501/zpd-main` and copied to `UbuntuServer:.runtime/repro-main-20261103/source`.

## Data (`run.py build-data`)

- Mac, fresh venv from `requirements.txt` (first with lower bounds, then with the pinned versions):
  - `--benchmark rq1` from the local Project CodeNet copy: 1,807 of 1,807 files byte-identical to
    `results/histra-bench-20261023/data` (both environments).
  - `--benchmark seen-unseen`: 19,437 of 19,438 files byte-identical to `UbuntuServer:data-canonical-v5`; the other,
    `splits/summary.json`, differs only by two absolute local paths the old summary recorded. The 3,660 files only in
    `data-canonical-v5` are trajectories outside every split (the 4K filter).
- UbuntuServer, fresh venv, judge image built from `docker/java` (`zpdpatch-java:21`), `--benchmark codeworkout` from a
  TIKTOC layout (`test-case-query-results/`, `data/dataset_granular_all.zip`): every data file byte-identical to
  `archive/external/tiktoc/derived` and `outputs/split-90-10/canonical-v5/datasets/paired-java-control`; three summary
  JSONs differ only by recorded output paths or two fields the current code adds (`problem_overlap`, `split_unit`).

## Adapters (`run.py generate`, greedy, batch 4, 4,096 new tokens, 8 stored inputs each)

- Joined parts match `output/models/SHA256SUMS` (12/12), locally and on the server.
- Lower-bound `requirements.txt` (vLLM pulled torch 2.10.0, peft 0.21.2): 90/96 raw generations identical.
- Pinned `requirements.txt` (torch 2.14.0+cu130, transformers 4.57.6, peft 0.20.0, bitsandbytes 0.50.2, as `fse-env`
  since 2026-09-04; unit `zpd-repro-smoke-pinned-20261103`): 92/96 identical. The three RQ1 adapters reproduce 24/24
  (as on 2026-10-31). The four differences are on the nine canonical adapters' validation inputs, whose stored runs date
  from 2026-08-11, before `fse-env` was reinstalled with these versions (the earlier versions were not recorded); judged
  again, two of the four keep the stored outcome, one loses a repair and one gains one (94/96 outcomes identical).
- vLLM runs used a separate environment (`fse-vllm`: vllm 0.18.0, torch 2.10.0, transformers 4.57.6), hence
  `requirements-vllm.txt`; it was not reinstalled in this check.

Files: `.runtime/repro-main-20261103/{data-java,smoke,smoke-unpinned,venv,venv-unpinned,*.log}` on UbuntuServer.
