"""p03324 Ringo's Favorite Numbers: D in {0,1,2}, 1<=N<=100."""
import random
import sys


def kind(seed):
    return "small" if seed % 3 == 1 else "max" if seed % 6 == 0 else "typical"


def generate(seed):
    r = random.Random(seed)
    k_ = kind(seed)
    d = r.randint(0, 2)
    n = {"small": r.randint(1, 10), "typical": r.randint(1, 100), "max": r.choice([100, 100, 99])}[k_]
    return f"{d} {n}\n"


if __name__ == "__main__":
    sys.stdout.write(generate(int(sys.argv[1])))
