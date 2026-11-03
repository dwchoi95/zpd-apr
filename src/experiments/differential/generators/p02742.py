"""p02742 Bishop: 1<=H,W<=1e9."""
import random
import sys


def kind(seed):
    return "small" if seed % 3 == 1 else "max" if seed % 6 == 0 else "typical"


def generate(seed):
    r = random.Random(seed)
    k_ = kind(seed)
    if k_ == "small":
        h, w = r.randint(1, 10), r.randint(1, 10)
    elif k_ == "max":
        h, w = r.choice([10**9, 10**9 - 1, 1]), r.choice([10**9, 10**9 - 1, 1, 2])
    else:
        h, w = r.randint(1, 10 ** r.randint(1, 9)), r.randint(1, 10 ** r.randint(1, 9))
        if r.random() < 0.2:
            h, w = r.choice([(1, w), (h, 1)])
    if r.random() < 0.5:
        h, w = w, h
    return f"{h} {w}\n"


if __name__ == "__main__":
    sys.stdout.write(generate(int(sys.argv[1])))
