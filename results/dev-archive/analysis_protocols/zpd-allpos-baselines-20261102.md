# allpos-baselines-20261102-v1

Authorized 2026-11-02 by the user ("MENTORED와 LSGen_GPT 빼고 일단 돌려봐. 모두 병렬로 최대한 빠르게."); recorded in
zpd-deadline-extension-20261023.json.

- Question: does a baseline that repairs toward a correct program return, at every failing submission s_i of a trajectory,
  a patch larger than the step the student took next (s_i -> s_{i+1})? Section II-B only; RQ1-RQ4 stay unchanged.
- Inputs: the HISTRA benchmark (14 problems, 1,764 trajectories); every failing submission except the last, whose patches
  are already stored (output/approaches of HISTRA, re-judged in histra-bench-20261023-v1).
- Tools and settings: HISTRA's runners unchanged (src/experiments/run_refactory.py, run_brafar.py, common.py) with the
  pinned upstream commits and histra.patch (Refactory f05583a5, -o -m -b -s 100, CAP 300 s; Brafar d764a069, -s 100,
  CAP 300 s); the same references (other students' accepted programs) and tests. A driver calls each runner's run() with
  the trajectory cut at s_i, so s_i is the buggy program. LSGen with Qwen2.5-Coder-7B-Instruct follows if time allows.
- Machine: UbuntuServer, source snapshot .runtime/allpos-baselines-20261102-v1/source, systemd-run --user units.
- Output: one row per (problem, user, position) with buggy, next submission, patch, seconds, status; copied back to
  results/allpos-baselines-20261102 with a MANIFEST.sha256. Interrupted runs are kept and marked incomplete.

## Run log
- 2026-11-02 21:33 KST: allpos-refactory (POOL=20) and allpos-brafar (POOL=8) started; 21:58 allpos-vllm (Qwen2.5-Coder-7B-Instruct,
  port 8011) and allpos-lsgen-qwen (validation POOL=6; LSGen's own 10 LLM workers) started after one-trajectory smoke tests.
- 22:17 KST: allpos-brafar killed by the kernel OOM killer (unit memory peak 174.7 GB) after 3,073 of 5,168 rows; the rows
  written so far are kept. 22:33 KST: allpos-brafar and allpos-refactory (stopped at 1,393 rows) restarted from the same
  snapshot under `ulimit -v 16000000` per process; the driver resumes from the written rows, so only in-flight jobs rerun.
- Load stays near 30-36 on 32 cores; HISTRA notes that Brafar's internal and LSGen's validation timeouts depend on load
  (run_brafar.py, run_lsgen.py), so timeout counts are reported with the results.
