"""Assert every generated input (seeds 1-100) satisfies its statement's constraints. Trusted code only."""
import importlib.util
import math
import re
import sys
from pathlib import Path

GEN = Path(__file__).resolve().parent / "generators"


def load(problem):
    spec = importlib.util.spec_from_file_location(problem, GEN / f"{problem}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ints(line):
    return list(map(int, line.split()))


def check(problem, text):
    assert text.endswith("\n")
    lines = text.split("\n")[:-1]
    if problem == "p02623":
        n, m, k = ints(lines[0]); a, b = ints(lines[1]), ints(lines[2])
        assert len(lines) == 3 and 1 <= n <= 2 * 10**5 and 1 <= m <= 2 * 10**5 and 1 <= k <= 10**9
        assert len(a) == n and len(b) == m and all(1 <= v <= 10**9 for v in a + b)
    elif problem == "p02659":
        a, b = lines[0].split(); assert len(lines) == 1
        assert re.fullmatch(r"\d\.\d\d", b) and 0 <= int(a) <= 10**15 and str(int(a)) == a
    elif problem == "p02686":
        n = int(lines[0]); s = lines[1:]
        assert len(s) == n and 1 <= n <= 10**6 and sum(map(len, s)) <= 10**6
        assert all(x and set(x) <= set("()") for x in s)
    elif problem == "p02694":
        assert len(lines) == 1 and 101 <= int(lines[0]) <= 10**18
    elif problem == "p02742":
        h, w = ints(lines[0]); assert len(lines) == 1 and 1 <= h <= 10**9 and 1 <= w <= 10**9
    elif problem == "p02743":
        v = ints(lines[0]); assert len(lines) == 1 and len(v) == 3 and all(1 <= x <= 10**9 for x in v)
    elif problem == "p02761":
        n, m = ints(lines[0]); assert len(lines) == m + 1 and 1 <= n <= 3 and 0 <= m <= 5
        for line in lines[1:]:
            s, c = ints(line); assert 1 <= s <= n and 0 <= c <= 9
    elif problem == "p02823":
        n, a, b = ints(lines[0]); assert len(lines) == 1 and 2 <= n <= 10**18 and 1 <= a < b <= n
    elif problem == "p02891":
        s, k = lines; assert 1 <= len(s) <= 100 and re.fullmatch("[a-z]+", s) and 1 <= int(k) <= 10**9
    elif problem == "p02975":
        n = int(lines[0]); a = ints(lines[1])
        assert len(lines) == 2 and 3 <= n <= 10**5 and len(a) == n and all(0 <= v <= 10**9 for v in a)
    elif problem == "p03240":
        n = int(lines[0]); pts = [tuple(ints(x)) for x in lines[1:]]
        assert len(pts) == n and 1 <= n <= 100 and len({p[:2] for p in pts}) == n
        assert all(0 <= x <= 100 and 0 <= y <= 100 and 0 <= h <= 10**9 for x, y, h in pts)
        assert len(load("p03240").solutions(pts)) == 1
    elif problem == "p03324":
        d, n = ints(lines[0]); assert len(lines) == 1 and d in (0, 1, 2) and 1 <= n <= 100
    elif problem == "p03438":
        n = int(lines[0]); a, b = ints(lines[1]), ints(lines[2])
        assert len(lines) == 3 and 1 <= n <= 10**4 and len(a) == len(b) == n
        assert all(0 <= v <= 10**9 for v in a + b)
    elif problem == "p03838":
        x, y = ints(lines[0]); assert len(lines) == 1 and x != y and abs(x) <= 10**9 and abs(y) <= 10**9
    else:
        raise KeyError(problem)


if __name__ == "__main__":
    problems = sys.argv[1:] or sorted(p.stem for p in GEN.glob("p*.py"))
    for problem in problems:
        gen = load(problem)
        for seed in range(1, 101):
            check(problem, gen.generate(seed))
        print(problem, "ok")
