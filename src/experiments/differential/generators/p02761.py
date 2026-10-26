"""p02761 Guess The Number: 1<=N<=3, 0<=M<=5, 1<=s_i<=N, 0<=c_i<=9."""
import random
import sys


def kind(seed):
    return "small" if seed % 3 == 1 else "max" if seed % 6 == 0 else "typical"


def generate(seed):
    r = random.Random(seed)
    k_ = kind(seed)
    if k_ == "small":
        n, m = r.randint(1, 3), r.randint(0, 2)
    elif k_ == "max":
        n, m = 3, 5
    else:
        n, m = r.randint(1, 3), r.randint(0, 5)
    mode = r.choice(["consistent", "consistent", "random", "leading"])
    if mode == "consistent":  # digits taken from one N-digit number
        num = str(r.randint(0 if n == 1 else 10 ** (n - 1), 10**n - 1))
        pairs = [(s, int(num[s - 1])) for s in (r.randint(1, n) for _ in range(m))]
    else:
        pairs = [(r.randint(1, n), r.randint(0, 9)) for _ in range(m)]
        if mode == "leading" and m > 0:
            pairs[r.randrange(m)] = (1, 0)
    return f"{n} {m}\n" + "".join(f"{s} {c}\n" for s, c in pairs)


if __name__ == "__main__":
    sys.stdout.write(generate(int(sys.argv[1])))
