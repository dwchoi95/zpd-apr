"""p03438 Sum Equality: 1<=N<=1e4, 0<=a_i,b_i<=1e9."""
import random
import sys

LIM = 10**9


def kind(seed):
    return "small" if seed % 3 == 1 else "max" if seed % 6 == 0 else "typical"


def margin(a, b):
    # operations available minus operations needed: k - sum ceil((b_i - a_i) / 2) over b_i > a_i
    return sum(b) - sum(a) - sum((y - x + 1) // 2 for x, y in zip(a, b) if y > x)


def steer(r, a, b, target):
    """Move the margin toward target; each move below changes it by exactly one per unit."""
    order = list(range(len(a)))
    r.shuffle(order)
    gap = target - margin(a, b)
    for i in order:
        if gap > 0 and b[i] < a[i]:  # raises k, need unchanged
            step = min(gap, a[i] - b[i])
            b[i] += step
            gap -= step
        elif gap < 0 and a[i] >= b[i]:
            step = min(-gap, LIM - a[i])
            a[i] += step
            gap += step


def generate(seed):
    r = random.Random(seed)
    k_ = kind(seed)
    if k_ == "small":
        n, hi = r.randint(1, 5), r.choice([3, 10])
    elif k_ == "max":
        n, hi = 10**4, r.choice([10, LIM])
    else:
        n, hi = r.randint(1, 1000), r.choice([10, 1000, LIM])
    a = [r.randint(0, hi) for _ in range(n)]
    b = [r.randint(0, hi) for _ in range(n)]
    if r.random() < 0.7:  # near the Yes/No boundary
        steer(r, a, b, r.choice([-2, -1, 0, 0, 1, 2]))
    return f"{n}\n{' '.join(map(str, a))}\n{' '.join(map(str, b))}\n"


if __name__ == "__main__":
    sys.stdout.write(generate(int(sys.argv[1])))
