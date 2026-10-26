"""p02659 Multiplication 3: 0<=A<=1e15 integer, 0<=B<10 with exactly two digits after the decimal point."""
import random
import sys

# B values whose binary float is just below the decimal (e.g. 1.15, 0.29), plus extremes
TRICKY = [0, 1, 10, 29, 57, 58, 99, 100, 101, 110, 113, 115, 129, 201, 229, 255, 435, 457, 529, 557,
          729, 820, 955, 990, 995, 999]


def kind(seed):
    return "small" if seed % 3 == 1 else "max" if seed % 6 == 0 else "typical"


def generate(seed):
    r = random.Random(seed)
    k_ = kind(seed)
    if k_ == "small":
        a = r.randint(0, 100)
    elif k_ == "max":
        a = r.choice([10**15, 10**15 - 1, r.randint(9 * 10**14, 10**15), 999999999999999])
    else:
        a = r.randint(0, 10 ** r.randint(1, 15))
    cents = r.choice(TRICKY) if r.random() < 0.5 else r.randint(0, 999)
    return f"{a} {cents // 100}.{cents % 100:02d}\n"


if __name__ == "__main__":
    sys.stdout.write(generate(int(sys.argv[1])))
