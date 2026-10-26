"""p03240 Ancient Pyramid: 1<=N<=100, distinct points in [0,100]^2, 0<=h_i<=1e9, (C_X, C_Y, H) unique."""
import random
import sys


def kind(seed):
    return "small" if seed % 3 == 1 else "max" if seed % 6 == 0 else "typical"


def solutions(points, limit=2):
    found = []
    pos = [p for p in points if p[2] > 0]
    for cx in range(101):
        for cy in range(101):
            if pos:
                x0, y0, h0 = pos[0]
                hs = [h0 + abs(x0 - cx) + abs(y0 - cy)]
            else:  # every H from 1 to the nearest distance fits
                near = min(abs(x - cx) + abs(y - cy) for x, y, _ in points)
                hs = list(range(1, min(near, limit) + 1))
            for hh in hs:
                if all(max(hh - abs(x - cx) - abs(y - cy), 0) == h for x, y, h in points):
                    found.append((cx, cy, hh))
                    if len(found) >= limit:
                        return found
    return found


def generate(seed):
    r = random.Random(seed)
    k_ = kind(seed)
    n = {"small": r.randint(2, 5), "typical": r.randint(2, 100), "max": 100}[k_]
    for attempt in range(2000):
        cx, cy = r.randint(0, 100), r.randint(0, 100)
        if k_ == "max":
            hgt = r.choice([10**9, 10**9 - r.randint(0, 200)])
        else:
            hgt = r.choice([r.randint(1, 30), r.randint(1, 200), r.randint(1, 10**9)])
        cells = r.sample(range(101 * 101), n)
        points = [(c // 101, c % 101) for c in cells]
        points = [(x, y, max(hgt - abs(x - cx) - abs(y - cy), 0)) for x, y in points]
        if len(solutions(points)) == 1:
            return f"{n}\n" + "".join(f"{x} {y} {h}\n" for x, y, h in points)
        if attempt % 50 == 49 and n < 100:
            n += 1
    raise RuntimeError(f"no unique pyramid for seed {seed}")


if __name__ == "__main__":
    sys.stdout.write(generate(int(sys.argv[1])))
