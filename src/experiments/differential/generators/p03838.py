"""p03838 Simple Calculator: |x|,|y|<=1e9, x != y."""
import random
import sys

LIM = 10**9


def kind(seed):
    return "small" if seed % 3 == 1 else "max" if seed % 6 == 0 else "typical"


def generate(seed):
    r = random.Random(seed)
    k_ = kind(seed)
    while True:
        if k_ == "small":
            x, y = r.randint(-5, 5), r.randint(-5, 5)
        elif k_ == "max":
            pool = [LIM, -LIM, LIM - 1, -LIM + 1, 0, 1, -1]
            x, y = r.choice(pool), r.choice(pool)
        else:
            x = r.randint(-LIM, LIM) // 10 ** r.randint(0, 8)
            y = r.randint(-LIM, LIM) // 10 ** r.randint(0, 8)
            mode = r.random()
            if mode < 0.2:
                y = -x
            elif mode < 0.3:
                x, y = r.choice([(0, y), (x, 0)])
            elif mode < 0.4:
                y = r.choice([x + 1, x - 1, -x + 1, -x - 1])
        if x != y and abs(x) <= LIM and abs(y) <= LIM:
            return f"{x} {y}\n"


if __name__ == "__main__":
    sys.stdout.write(generate(int(sys.argv[1])))
