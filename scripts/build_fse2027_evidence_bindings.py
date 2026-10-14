"""Regenerate the literal evidence bindings that tie the manuscript to the result bridge.

A binding is a manuscript clause in which evidence-derived values are replaced by the
result-bridge command that produced them, so the verifier can expand the commands and
require the clause to appear verbatim in the paper.

The map below is curated, not inferred. Values alone cannot prove provenance, because
unrelated quantities share them: 9.8 is both a greedy-checkpoint and a stochastic-draw
contrast, 1.3 is both an exact-match rate and a near-duplicate rate. Each entry names
the clause by a locator phrase and the commands whose values that clause reports, and
the build fails when a value is absent from its clause, when a clause has moved, or
when a binding no longer expands back to the manuscript text.
"""
import argparse
import json
import re
from pathlib import Path

# Expanded by the verifier itself, so a clause holding one can never round-trip.
RESERVED = ('tool', 'progress', 'strict', 'answer')
BREAKS = ('. ', '; ', '\n')

CURATED = (
    ('the current-only terminal triple at',
     ['CurrentOnlyAnswerThreeSeenRR', 'CurrentOnlyAnswerThreeUnseenRR']),
    ('raises coverage from 50.4',
     ['CrossUserTargetSameUserSeenRR', 'CrossUserTargetOtherUserSeenRR',
      'CrossUserTargetSameUserUnseenRR', 'CrossUserTargetOtherUserUnseenRR']),
    ('terminal targets repair 155 trajectories',
     ['PairedJavaStudentRRCI', 'PairedJavaExerciseRRCI']),
    ('joint repairs, intermediate targets retain',
     ['PairedJavaJointRepairs', 'PairedJavaLexicalRetention', 'PairedJavaLineRetention']),
    ('Replacing greedy decoding by one stochastic draw costs',
     ['StochasticOneMinusGreedyOneSeenCI',
      'SameDrawThreeMinusOneSeen', 'SameDrawThreeMinusOneSeenCI']),
    ('the decoder collapses to',
     ['SweepTOnePointZeroSeenSingleRR', 'SweepTPointTwoSeenSingleRR',
      'SweepTOnePointZeroSeenRR', 'SweepTOnePointZeroUnseenRR',
      'SweepTOnePointFiveSeenRR', 'SweepTOnePointFiveUnseenRR']),
    ('the matched base-model three-draw union reaches only',
     ['BaseStochasticThreeSeenRR', 'BaseStochasticThreeUnseenRR',
      'AnswerStochasticMinusBaseSeen', 'AnswerStochasticMinusBaseSeenCI',
      'AnswerStochasticMinusBaseUnseen', 'AnswerStochasticMinusBaseUnseenCI']),
    ('replacing three draws of one checkpoint by one draw from each of three checkpoints',
     ['CheckpointStochasticMinusSameCheckpointSeenCI',
      'CheckpointStochasticMinusSameCheckpointUnseen',
      'CheckpointStochasticMinusSameCheckpointUnseenCI']),
    ('three greedy checkpoints gain',
     ['FactorialGreedyThreeMinusOneSeen', 'FactorialGreedyThreeMinusOneSeenCI',
      'FactorialGreedyThreeMinusOneUnseen', 'FactorialGreedyThreeMinusOneUnseenCI',
      'FactorialDistinctMinusSameSeen', 'FactorialDistinctMinusSameSeenCI',
      'FactorialDistinctMinusSameUnseen', 'FactorialDistinctMinusSameUnseenCI']),
    ('Absolute greedy-three coverage is',
     ['FactorialGreedyThreeSeenRR', 'FactorialGreedyThreeUnseenRR',
      'CurrentOnlyAnswerThreeSeenRR', 'CurrentOnlyAnswerThreeUnseenRR']),
    ('the primary five-fold cross-fitted mixed-minus-terminal contrast is',
     ['CrossFitMixedMinusAnswerNineSeenCI']),
    ('removing history instead improves frozen mixed and terminal RR by',
     ['PromptFrozenMixedCurrentMinusFullSeen', 'PromptFrozenAnswerNineCurrentMinusFullSeen',
      'PromptFrozenMixedCurrentMinusFullUnseen', 'PromptFrozenAnswerNineCurrentMinusFullUnseen']),
    ('turns the raw gap into',
     ['DifficultyMatchedUnseenMinusSeenCI']),
    ('with a distinct seed yields',
     ['SeenHiddenMixedHiddenConfirmation', 'SeenHiddenAnswerNineHiddenConfirmation']),
    ('the early, middle, and last thirds reach',
     ['AllPrefixSeenRR', 'AllPrefixUnseenRR',
      'AllPrefixEarlySeenRR', 'AllPrefixMiddleSeenRR', 'AllPrefixLastSeenRR',
      'AllPrefixEarlyUnseenRR', 'AllPrefixMiddleUnseenRR', 'AllPrefixLastUnseenRR']),
    ('At 1.5B parameters three checkpoints still gain',
     ['ScaleAnswerThreeMinusOneSeen', 'ScaleAnswerThreeMinusOneSeenCI',
      'ScaleMixedMinusAnswerNineSeenCI']),
    ('positive on four held-out exercises',
     ['CodeWorkoutProblemMixedMinusAnswerNine', 'CodeWorkoutProblemMixedMinusAnswerNineCI']),
    ('refitting with one exercise left out keeps the contrast between',
     ['ExerciseSensitivityLOOMinimum', 'ExerciseSensitivityLOOMaximum',
      'ExerciseSensitivityPerMinimum', 'ExerciseSensitivityPerMaximum']),
    ('agree with the canonical ones on',
     ['VerdictOrderStrictAgreementSeen', 'VerdictOrderProgressAgreementSeen']),
    ('retraining both relations under the binary verdict order changes intermediate-target RR by',
     ['VerdictOrderProgressCanonicalMinusAlternativeSeen']),
    ('near-duplicates above a 0.90 token-similarity threshold in',
     ['SeenOverlapMixedExactRate', 'SeenOverlapAnswerNineExactRate',
      'SeenOverlapMixedNearNinetyRate', 'SeenOverlapAnswerNineNearNinetyRate',
      'SeenOverlapMixedMedianSimilarity', 'SeenOverlapAnswerNineMedianSimilarity']),
)


def definitions(bridge: Path) -> dict[str, str]:
    text = bridge.read_text(encoding='utf-8')
    return {name: value for name, value in re.findall(r'\\newcommand\{\\(\w+)\}\{(.*)\}', text) if value}


def expand(template: str, defs: dict[str, str]) -> str:
    """Expand exactly as the verifier does, so a stored binding cannot pass here and fail there."""
    expanded = re.sub(r'\\([A-Za-z]+)\b', lambda m: defs.get(m[1], m[0]), template)
    return re.sub(r'(?<=[\d\]])\{\}', '', expanded)


def clause_for(text: str, locator: str) -> str:
    """The sentence or semicolon-delimited clause that holds the locator."""
    where = text.index(locator)
    start = max((text.rfind(mark, 0, where) + len(mark) for mark in BREAKS if mark in text[:where]), default=0)
    after = where + len(locator)
    end = min((pos for pos in (text.find(mark, after) for mark in BREAKS) if pos != -1), default=len(text))
    return text[start:end].strip()


def build(bridge: Path, paper: Path):
    defs = definitions(bridge)
    reserved = {name: f'\\textsc{{{name.capitalize()}}}' for name in RESERVED}
    text = paper.read_text(encoding='utf-8')
    bindings, problems = [], []
    for locator, names in CURATED:
        if text.count(locator) != 1:
            problems.append(f'locator occurs {text.count(locator)} times, expected once: {locator!r}')
            continue
        clause = clause_for(text, locator)
        if re.search(r'\\(' + '|'.join(RESERVED) + r')\b', clause):
            problems.append(f'clause expands a reserved command, so it cannot round-trip: {locator!r}')
            continue
        template = clause
        for name in sorted(names, key=lambda n: -len(defs.get(n, ''))):
            value = defs.get(name)
            if not value:
                problems.append(f'{name} is not defined by the result bridge')
                continue
            pattern = re.compile(r'(?<![\d.\w])' + re.escape(value) + r'(?![\d\w])')
            if not pattern.search(template):
                problems.append(f'{name}={value} does not occur in the clause at {locator!r}')
                continue
            template = pattern.sub('\\\\' + name, template, count=1)
        # The verifier requires the stored list to be exactly the bridge commands it finds.
        found = sorted(set(re.findall(r'\\([A-Za-z]+)\b', template)) & (defs.keys() | reserved.keys()))
        if found != sorted(names):
            problems.append(f'bound {found} but the entry claims {sorted(names)} at {locator!r}')
            continue
        if expand(template, {**defs, **reserved}) != clause:
            problems.append(f'binding does not expand back to the manuscript clause at {locator!r}')
            continue
        bindings.append({'template': template, 'commands': found})
    return {
        'schema_version': 1,
        'scope': 'Literal manuscript snippets validated against evidence-derived values; not a LaTeX input',
        'bindings': bindings,
    }, problems


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bridge', type=Path, default=Path('paper/fse2027-result-bridge.tex'))
    parser.add_argument('--paper', type=Path, default=Path('paper/main.tex'))
    parser.add_argument('--output', type=Path, default=Path('paper/main.evidence-bindings.json'))
    args = parser.parse_args()
    payload, problems = build(args.bridge, args.paper)
    if problems:
        raise SystemExit('evidence bindings are not consistent with the manuscript:\n  ' + '\n  '.join(problems))
    args.output.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    commands = sorted({c for row in payload['bindings'] for c in row['commands']})
    print(json.dumps({'bindings': len(payload['bindings']), 'commands': len(commands)}, indent=1))
