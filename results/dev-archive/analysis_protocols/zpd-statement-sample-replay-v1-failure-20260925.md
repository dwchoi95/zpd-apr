# Empirical replay v1: failed before READY,2026-09-25

Status: **FAILED, zero submitted sources/cases executed; no feedback or fit**.
Do not rerun or overwrite this attempt. All prior scientific negatives remain.

## Exact release and clean execution

- Source commit a9200df03b87b1189bf9d50856edcc1c654f9d65;
  tree db663cf8f374876edee2636d4cc312f83d6c33d5.
- Source bundle d4adcb9c22cf057650fd40443b42dbb5e7c0b76724b9247d95e418074ea29ecd.
- Local /private/tmp/zpd-statement-replay.31pk7X/source; remote canonical
  .runtime/statement-sample-replay-20260924-v1.
- Release a59419280a54c2adbfc5ea2be236f44bf06dbce411066b35b0673569764bc4e3.
- Controller/execution runtime e099309749438d36e5d938290cdfa16e0ee0a9267f4368b3ea7af199a4dde11a.
- Local910 ZPD tests257.135s +19 pilot tests0.008s PASS; server910 tests124.073s
  +19 pilot tests0.005s PASS. Both trees stayed clean. All46 sources,87 parent
  bindings, configuration/release and runtime passed checks before/after tests.
- Local test-log SHAs dd81efee4b34fd66866d89febc37e45764495900665a6c04f217aa22a4a5651f
  and d8905a2a05c44c0b0f8d0262f2b2a02a7dd092f51f56a279cd5445181fc0e706;
  server caaeaab28bc368d7668e821065af778acfeaf4811846373337502306b6421552
  and77e5ff021d745c11d320e0918b4a1600dba10daa4adae6bda0bea8e7d65747e9.

An initial outer shell command used an unquoted =session target, which zsh
rejected before tmux creation or any execution/output. Explicit quoting and
bash fixed that shell-only issue. Fresh-path/preflight checks were repeated;
exactly one actual service attempt followed at01:04:30 KST.

## Actual failure and retained evidence

Service zpd-statement-samples-replay-20260924-v1.service started main1916716 at
monotonic1754689976671 and exited status2 at1754690624447. Journal reports
`unexpected processes or threads at ready/keeper barrier` before any READY.
No GO, replay-v1 directory, source journal or case result exists. The coordinator
waited its fixed30-second READY deadline and saved FAILED; no fitting occurred.

Under outputs/zpd-statement-sample-feedback-20260924:

- replay-supervised-v1/manifest.json SHA
  b37d2f5a4be59d31a3e018860591f77e2ae2f8ac9039efedd4b1ed51e836e80d.
- replay-supervised-v1/FAILED.json SHA
  52712fcc8dce456ffb54368efe12f522e6a7ca176e0a77a7f575800f056e5a03.
- replay-launcher-v1.log SHA
  6476027a3a184ab9b4ea2585176565aea8cd6aec5b465ad00a5ad25bc7e534c2.
- replay-v1-unit-journal.log SHA
  0089d2d1e5d020c3b6d0046611cf2b19ebfbf409eee10952bf4748e5f812b469.
- replay-v1-manual-cleanup.log SHA
  67b77c609e9604c7723d767d80c73946ea746469c59504860d7a34b3d6bda89e.

These files were synchronized nondeleting. The original coordinator also
reports a cleanup error: no first live snapshot existed and the now-empty
reported ControlGroup could not establish the original owned cgroup. Do not
retroactively claim producer cleanup or invent an old cgroup path.

Root later checked exact unit/ExecStart/working directory/start+exit times,
failed status/MainPID0/empty reported group and absence of /proc/1916716, then
stopped only that already exited owned unit. The separate log retains pre/post
metadata. This removes no artifacts and does not establish missing historical
live accounting. The tmux coordinator session had already exited automatically.

## Import-only diagnosis; no empirical data

Fresh controller probes after five BLAS settings showed: baseline/numpy/scipy
each one main thread; importing sklearn adds pandas/pyarrow and jemalloc_bg_thd.
Exact production module import likewise creates that thread. The loaded
PyArrow25.0.1 library is libarrow.so.2500 and contains the actual configuration
name JE_ARROW_MALLOC_CONF. Generic MALLOC_CONF=background_thread:false,
ARROW_JEMALLOC_CONF=background_thread:false and ARROW_DEFAULT_MEMORY_POOL=system
all left the thread present. The latter changed the default pool but did not
prevent allocator initialization; it is not adopted.

JE_ARROW_MALLOC_CONF=background_thread:false before import leaves exactly the
main thread, including after the unchanged runtime-identity commands. The
default pool remains mimalloc and Arrow remains25.0.1. These root-run OS/import
diagnostics opened no prepared bodies or candidate/label data and ran no unit
or submitted program. Independent reviewer SSH was blocked; its static import
analysis is independent, but these server observations are not its own run.

The bounded correction is prospective AppendixC of the replay protocol. It
keeps exact-singleton and all resource/evaluation rules, pins the actual loaded
Arrow binaries additionally, and requires a reviewed fresh release/unit/output.
Neither this diagnosis nor passing synthetic tests demonstrates repair benefit.
