#!/usr/bin/env python3
"""Recover the English LaTeX source from a Korean reading copy of the manuscript.

The reading copy keeps every English paragraph verbatim as a ``% `` comment under
its Korean translation, so stripping the Korean lines and uncommenting restores the
build source exactly. Comments that were already in the source are left alone.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

HANGUL = re.compile(r'[가-힣]')
MARKER = '%!ko-review'          # header lines the reading copy adds, dropped on recovery


def english(text: str) -> str:
    """Drop Korean lines and uncomment the English paragraph that follows each one."""
    out, pending = [], False
    for line in text.split('\n'):
        if line.startswith(MARKER):
            continue
        if HANGUL.search(line) and not line.startswith('%'):
            pending = True                      # a translation line; its English follows
            continue
        if pending:
            if not line.startswith('% '):
                raise ValueError(f'translated line is not followed by a commented paragraph: {line[:60]!r}')
            out.append(line[2:])
            pending = False
            continue
        out.append(line)
    if pending:
        raise ValueError('file ends with a translation that has no English paragraph')
    return '\n'.join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('paper/main.tex'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(english(args.source.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'wrote {args.output} from {args.source}')


if __name__ == '__main__':
    main()
