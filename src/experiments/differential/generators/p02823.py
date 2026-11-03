"""p02823 Table Tennis Training: 2<=N<=1e18, 1<=A<B<=N."""
import random
import sys


def kind(seed):
    return "small" if seed % 3 == 1 else "max" if seed % 6 == 0 else "typical"


def generate(seed):
    r = random.Random(seed)
    k_ = kind(seed)
    if k_ == "small":
        n = r.randint(2, 10)
    elif k_ == "max":
        n = r.choice([10**18, 10**18 - 1])
    else:
        n = r.randint(2, 10 ** r.randint(1, 18))
    mode = r.choice(["random", "random", "edge"])
    if mode == "edge":  # friends next to the ends or to each other
        a = min(r.choice([1, 2, n - 1, r.randint(1, n - 1)]), n - 1)
        b = r.choice([n, n - 1, a + 1, a + 2, r.randint(a + 1, n)])
        b = min(max(b, a + 1), n)
    else:
        a = r.randint(1, n - 1)
        b = r.randint(a + 1, n)
    return f"{n} {a} {b}\n"


if __name__ == "__main__":
    sys.stdout.write(generate(int(sys.argv[1])))
