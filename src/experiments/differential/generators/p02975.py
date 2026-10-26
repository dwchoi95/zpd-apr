"""p02975 XOR Circle: 3<=N<=1e5, 0<=a_i<=1e9."""
import random
import sys


def kind(seed):
    return "small" if seed % 3 == 1 else "max" if seed % 6 == 0 else "typical"


def generate(seed):
    r = random.Random(seed)
    k_ = kind(seed)
    n = {"small": r.randint(3, 9), "typical": r.randint(3, 3000), "max": r.choice([10**5, 99999])}[k_]
    mode = r.choice(["zeros", "triple", "triple", "pair", "pair", "near", "random", "lowrandom"])
    vmax = (1 << 29) - 1  # x ^ y stays below 1e9
    if mode in ("triple", "pair", "near"):
        m = max(3, n - n % 3) if r.random() < 0.8 else n  # usually a multiple of 3
        x = r.randint(1, vmax)
        y = r.randint(1, vmax)
        third = m // 3
        if mode == "pair":
            a = [0] * third + [x] * (m - third)
        else:
            a = [x] * third + [y] * third + [x ^ y] * (m - 2 * third)
        if mode == "near":
            a[r.randrange(m)] = r.choice([0, x, y, r.randint(0, vmax)])
        n = m
    elif mode == "zeros":
        a = [0] * n
        if r.random() < 0.3:
            a[r.randrange(n)] = r.randint(1, 10**9)
    elif mode == "lowrandom":
        a = [r.randint(0, 3) for _ in range(n)]
    else:
        a = [r.randint(0, 10**9) for _ in range(n)]
    r.shuffle(a)
    return f"{n}\n{' '.join(map(str, a))}\n"


if __name__ == "__main__":
    sys.stdout.write(generate(int(sys.argv[1])))
