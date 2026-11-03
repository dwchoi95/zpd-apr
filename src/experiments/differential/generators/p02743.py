"""p02743 Sqrt Inequality: 1<=a,b,c<=1e9."""
import math
import random
import sys

LIM = 10**9


def kind(seed):
    return "small" if seed % 3 == 1 else "max" if seed % 6 == 0 else "typical"


def generate(seed):
    r = random.Random(seed)
    k_ = kind(seed)
    hi = {"small": 20, "typical": 10 ** r.randint(2, 9), "max": LIM}[k_]
    mode = r.choice(["random", "square", "near", "near"])
    if mode == "random":
        a, b, c = (r.randint(max(1, hi // 2) if k_ == "max" else 1, hi) for _ in range(3))
    elif mode == "square":  # sqrt(a)+sqrt(b) = sqrt(c) exactly, then shifted by delta
        top = math.isqrt(hi)
        x = r.randint(1, max(1, top - 1))
        y = r.randint(1, max(1, top - x))
        a, b, c = x * x, y * y, (x + y) ** 2 + r.choice([-2, -1, 0, 0, 1, 2])
    else:  # c next to a + b + 2 sqrt(ab), where float evaluation can be wrong
        a = r.randint(1, max(1, hi // 4))
        b = r.randint(1, max(1, hi // 4))
        c = a + b + math.isqrt(4 * a * b) + r.choice([-1, 0, 1, 2])
    a, b, c = (min(max(v, 1), LIM) for v in (a, b, c))
    if r.random() < 0.5:
        a, b = b, a
    return f"{a} {b} {c}\n"


if __name__ == "__main__":
    sys.stdout.write(generate(int(sys.argv[1])))
