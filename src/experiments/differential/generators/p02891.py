"""p02891 Connection and Disconnection: 1<=|S|<=100 lowercase, 1<=K<=1e9."""
import random
import string
import sys


def kind(seed):
    return "small" if seed % 3 == 1 else "max" if seed % 6 == 0 else "typical"


def generate(seed):
    r = random.Random(seed)
    k_ = kind(seed)
    if k_ == "small":
        length, k = r.randint(1, 6), r.randint(1, 5)
    elif k_ == "max":
        length, k = 100, r.choice([10**9, 10**9 - 1, 1])
    else:
        length, k = r.randint(1, 100), r.randint(1, 10 ** r.randint(1, 9))
    letters = string.ascii_lowercase[: r.choice([1, 2, 2, 3, 26])]
    mode = r.choice(["runs", "runs", "uniform", "same"])
    if mode == "same":
        s = r.choice(letters) * length
    elif mode == "uniform":
        s = "".join(r.choice(letters) for _ in range(length))
    else:
        out = []
        while len(out) < length:
            out += [r.choice(letters)] * r.randint(1, 6)
        s = "".join(out[:length])
        if r.random() < 0.4:  # same letter at both ends
            s = s[:-1] + s[0] if length > 1 else s
    return f"{s}\n{k}\n"


if __name__ == "__main__":
    sys.stdout.write(generate(int(sys.argv[1])))
