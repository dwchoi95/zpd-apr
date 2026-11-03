"""p02694 1%: 101<=X<=1e18."""
import random
import sys

BALANCES = []
_b = 100
while _b < 10**18:
    _b += _b // 100
    BALANCES.append(_b)


def kind(seed):
    return "small" if seed % 3 == 1 else "max" if seed % 6 == 0 else "typical"


def generate(seed):
    r = random.Random(seed)
    k_ = kind(seed)
    if k_ == "small":
        x = r.randint(101, 200)
    elif k_ == "max":
        x = r.choice([10**18, 10**18 - 1, BALANCES[-2], BALANCES[-2] + 1, r.randint(10**17, 10**18)])
    else:
        x = r.randint(101, 10 ** r.randint(3, 18))
    if k_ != "max" and r.random() < 0.4:  # exactly a balance, or one above it
        x = r.choice(BALANCES[:-1]) + r.choice([0, 1])
    return f"{min(max(x, 101), 10**18)}\n"


if __name__ == "__main__":
    sys.stdout.write(generate(int(sys.argv[1])))
