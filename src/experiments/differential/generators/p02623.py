"""p02623 Tsundoku: 1<=N,M<=2e5, 1<=K<=1e9, 1<=A_i,B_i<=1e9."""
import random
import sys


def kind(seed):
    return "small" if seed % 3 == 1 else "max" if seed % 6 == 0 else "typical"


def generate(seed):
    r = random.Random(seed)
    k_ = kind(seed)
    if k_ == "small":
        n, m, hi = r.randint(1, 5), r.randint(1, 5), r.choice([3, 10, 100])
    elif k_ == "max":
        n, m, hi = 200000, 200000, r.choice([1, 10, 10**4, 10**9])
    else:
        n, m, hi = r.randint(1, 3000), r.randint(1, 3000), r.choice([10, 1000, 10**6, 10**9])
    a = [r.randint(1, hi) for _ in range(n)]
    b = [r.randint(1, hi) for _ in range(m)]
    mode = r.random()
    if mode < 0.15:
        k = 10**9
    elif mode < 0.25:
        k = r.randint(1, 10)
    elif mode < 0.6:
        # exact boundary: a prefix of A plus a prefix of B, optionally minus one
        i, j = r.randint(0, n), r.randint(0, m)
        k = sum(a[:i]) + sum(b[:j]) - r.choice([0, 0, 1])
    else:
        k = r.randint(1, sum(a) + sum(b))
    k = min(max(k, 1), 10**9)
    return f"{n} {m} {k}\n{' '.join(map(str, a))}\n{' '.join(map(str, b))}\n"


if __name__ == "__main__":
    sys.stdout.write(generate(int(sys.argv[1])))
