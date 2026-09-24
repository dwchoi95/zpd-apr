"""Single synthetic dense linear-algebra probe; no empirical inputs or fitting.

This is not the joint solver or a release. It measures one Hessian assembly and
Cholesky direction at 4,131 columns. No files are opened or written by this code.
Run only under the specified Linux 32-GiB boundary and pinned environment.
"""
import json
import math
import os
import platform
import resource
import time

LIMIT = 32 * 1024**3
ENV = dict(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1',
           NUMEXPR_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1',
           JE_ARROW_MALLOC_CONF='background_thread:false')


def main():
    if platform.system() != 'Linux' or any(os.environ.get(k) != v for k, v in ENV.items()):
        raise RuntimeError('fixed Linux environment required')
    resource.setrlimit(resource.RLIMIT_AS, (LIMIT, LIMIT))
    import numpy as np
    import scipy
    from scipy.linalg import cholesky, solve_triangular
    if (platform.python_version(), np.__version__, scipy.__version__) != ('3.13.11', '2.5.2', '1.18.1'):
        raise RuntimeError('fixed runtime required')
    started = time.monotonic()
    rows, columns = 7708, 4131
    rng = np.random.Generator(np.random.PCG64(2027))
    original = rng.standard_normal((rows // 2, columns), dtype=np.float64) / math.sqrt(columns)
    x = np.empty((rows, columns), dtype=np.float64)
    x[0::2], x[1::2] = original, -original
    del original
    targets = np.empty(rows, dtype=np.float64)
    targets[0::2] = rng.integers(0, 2, rows // 2)
    targets[1::2] = 1.0 - targets[0::2]
    weight = 1900.0 / rows
    gradient = 0.1 * (x.T @ (weight * (0.5 - targets)))
    print(json.dumps(dict(phase='synthetic_arrays_ready', elapsed=time.monotonic()-started)), flush=True)
    then = time.monotonic()
    hessian = np.eye(columns) + x.T @ ((0.025 * weight) * x)
    hessian = 0.5 * hessian + 0.5 * hessian.T
    assembly = time.monotonic() - then
    del x
    print(json.dumps(dict(phase='hessian_ready', assembly_seconds=assembly)), flush=True)
    then = time.monotonic()
    factor = cholesky(hessian, lower=True, check_finite=True)
    intermediate = solve_triangular(factor, -gradient, lower=True, check_finite=True)
    direction = solve_triangular(factor.T, intermediate, lower=False, check_finite=True)
    solve = time.monotonic() - then
    residual = float(np.max(np.abs(hessian @ direction + gradient)))
    denominator = float(np.linalg.norm(hessian, ord=np.inf) * np.max(np.abs(direction)) + np.max(np.abs(gradient)))
    normalized = residual / denominator
    if not math.isfinite(normalized) or normalized > 1e-12:
        raise RuntimeError('fixed normalized linear residual failed')
    print(json.dumps(dict(kind='synthetic_joint_dense_linear_algebra_probe_v1', rows=rows,
        columns=columns, seed=2027, empirical_inputs_opened=False, fitting_performed=False,
        complete_solver_test=False, assembly_seconds=assembly, solve_seconds=solve,
        total_seconds=time.monotonic()-started, normalized_solve_residual=normalized,
        max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        address_space_limits=list(resource.getrlimit(resource.RLIMIT_AS)), environment=ENV)), flush=True)


if __name__ == '__main__':
    main()
