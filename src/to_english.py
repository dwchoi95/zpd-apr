"""Korean review draft -> English submission source. Each Korean paragraph line is replaced by the '% EN: ' line under
it, Korean-only comments are dropped, and the kotex line is removed. Usage: python3 paper/src/to_english.py paper/main.tex"""
import re
import sys

HANGUL = re.compile(r"[\uac00-\ud7a3]")
out = []
for line in open(sys.argv[1], encoding="utf-8").read().split("\n"):
    if line.startswith("% EN:"):
        assert out and HANGUL.search(out[-1]) and not out[-1].lstrip().startswith("%"), f"no Korean line above: {line[:60]}"
        english = line[len("% EN:"):]
        out[-1] = english[1:] if english.startswith(" ") else english
    elif not (HANGUL.search(line) and line.lstrip().startswith("%")):
        out.append(line)
src = re.sub(r"\\usepackage\{kotex\}[^\n]*\n", "", "\n".join(out), count=1)
leftover = [l for l in src.split("\n") if HANGUL.search(l) and not l.lstrip().startswith("%")]
assert not leftover, leftover[:3]
sys.stdout.write(src)
