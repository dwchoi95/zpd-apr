# One synthetic linear-algebra probe

This is a bounded resource/linear-residual check, not the joint solver, a fit
release, a convergence experiment, or evidence of repair gain. No empirical
input or label is opened by the probe. The array has 7,708 mirrored synthetic
rows and 4,131 columns; the row count covers the largest already reported
progress32 training-pair count, without using its feature or label values.
PCG64 seed2027 and the complete source fix the synthetic construction.

Source: `scripts/probe_zpd_joint_linear_algebra.py`.
SHA256: `4c0cd0f17e9759c70b38362d65ef26c3b6591c5abe4c46080e7ab50e15c3ac8c`.

Execution boundary: one clean committed snapshot on UbuntuServer; pinned
Python3.13.11/NumPy2.5.2/SciPy1.18.1, six fixed environment values, Linux
RLIMIT_AS soft/hard32GiB, external GNU timeout180 seconds with TERM then KILL
after5 seconds. No retry under this record. Inspect the owned process state on
completion/failure and preserve terminal output. This is not an empirical job.

## Independent static review received before execution

Reviewer: repair_structure_features, not the probe author. Scope: the exact
70-line source and one-operation claim; no execution by the reviewer.

> Static review: 이 한 번의 synthetic linear-algebra 측정 범위에 한해 GO,
> 차단 오류는 찾지 못했습니다. theta=0·offset=0에서
> gradient=.1 Xᵀw(.5−t), Hessian=I+.025 XᵀwX는 signed-logistic 목적과
> 일치하고 mirrored target/row 및 mass1900도 맞습니다. 32GiB는 NumPy
> import·배열할당 전에 설정, 6환경 사전검사/고정버전검사,
> Cholesky·triangular finite 검사와 ≤1e−12 residual fail-closed도 적합합니다.
> 단 180초 외부 watchdog/owned-process cleanup은 반드시 별도 적용해야 합니다.
> 큰 주의: isotropic N(0,1/4131)와 I ridge라 매우 좋은 조건의 한 theta=0
> 행렬입니다. 실제4131 feature의 scaling/상관/고차 Newton iterations·전체35fits
> runtime·gradient 수렴 가능성을 보장하지 않으며, 해당 제한은 현재
> complete_solver_test=False 범위와 맞습니다. 경험적 fit 승인으로 확대하면 안 됩니다.

The review is retained with its limitations. A successful timing probe does not
close the synthetic full-solver or method-selection gates of the candidate plan.
