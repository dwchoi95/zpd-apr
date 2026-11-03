"""p02686 Bracket Sequencing: 1<=N<=1e6, total length <=1e6, each S_i non-empty over ( and )."""
import random
import sys


def kind(seed):
    return "small" if seed % 3 == 1 else "max" if seed % 6 == 0 else "typical"


def balanced(r, pairs):
    # A random arrangement with equal counts, rotated after its lowest prefix, is a bracket sequence.
    s = ["("] * pairs + [")"] * pairs
    r.shuffle(s)
    h, low, cut = 0, 0, 0
    for i, c in enumerate(s):
        h += 1 if c == "(" else -1
        if h < low:
            low, cut = h, i + 1
    return s[cut:] + s[:cut]


def generate(seed):
    r = random.Random(seed)
    k_ = kind(seed)
    length = {"small": r.randint(1, 12), "typical": r.randint(1, 3000), "max": 10**6}[k_]
    mode = r.choice(["yes", "yes", "swap", "flip", "random", "deep"])
    pairs = max(1, length // 2)
    if mode == "random":
        s = [r.choice("()") for _ in range(length)]
    elif mode == "deep":
        d = r.randint(1, pairs)
        s = balanced(r, pairs - d)
        at = r.randint(0, len(s))
        s = s[:at] + ["("] * d + [")"] * d + s[at:]
    else:
        s = balanced(r, pairs)
        if mode == "swap":  # equal counts, but one ( moved after one )
            opens = [i for i, c in enumerate(s) if c == "("]
            closes = [i for i, c in enumerate(s) if c == ")"]
            i, j = r.choice(opens), r.choice(closes)
            s[i], s[j] = s[j], s[i]
        elif mode == "flip":  # unequal counts
            i = r.randrange(len(s))
            s[i] = "(" if s[i] == ")" else ")"
    total = len(s)
    if r.random() < 0.15:
        n = total  # one character per string
    else:
        n = r.randint(1, min(total, r.choice([1, 2, 5, 20, 1000, 10**6])))
    cuts = sorted(r.sample(range(1, total), n - 1)) if n > 1 else []
    bounds = [0] + cuts + [total]
    text = "".join(s)
    pieces = [text[bounds[i]:bounds[i + 1]] for i in range(n)]
    r.shuffle(pieces)
    return f"{n}\n" + "\n".join(pieces) + "\n"


if __name__ == "__main__":
    sys.stdout.write(generate(int(sys.argv[1])))
