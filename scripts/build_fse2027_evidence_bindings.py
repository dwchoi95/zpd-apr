"""Rebuild curated ICSE-SEET literal claim bindings from preserved evidence.

The historic filename is retained. CURATED lists contextual claim templates,
not numbers extracted from the manuscript. Evidence values expand each template;
missing text or drift fails closed. The JSON output is not a LaTeX input.
"""
import argparse
import json
import re
from pathlib import Path

CURATED = (
    'at \\CurrentOnlyAnswerThreeSeenRR\\% Seen and \\CurrentOnlyAnswerThreeUnseenRR\\% Unseen.',
    'Answer-9Choose3 & C & \\CurrentOnlyAnswerNineSeenRR & 35.41 & \\CurrentOnlyAnswerNineUnseenRR & 20.06',
    'Progress-minus-Answer RR is \\PairedTargetProgressMinusAnswerSeen points \\PairedTargetProgressMinusAnswerSeenCI on Seen and \\PairedTargetProgressMinusAnswerUnseen \\PairedTargetProgressMinusAnswerUnseenCI on Unseen',
    'Among \\PairedTargetJointRepairsSeen Seen and \\PairedTargetJointRepairsUnseen Unseen jointly repaired inputs, \\PairedTargetJointTEDRepairsSeen and \\PairedTargetJointTEDRepairsUnseen have defined source-to-repair TED for both methods.',
    'Answer-minus-Progress mean TED is \\PairedTargetAnswerMinusProgressTEDSeen \\PairedTargetAnswerMinusProgressTEDSeenCI and \\PairedTargetAnswerMinusProgressTEDUnseen \\PairedTargetAnswerMinusProgressTEDUnseenCI.',
    'Token retention improves by \\PairedTargetProgressMinusAnswerTokenRetentionSeen \\PairedTargetProgressMinusAnswerTokenRetentionSeenCI and \\PairedTargetProgressMinusAnswerTokenRetentionUnseen \\PairedTargetProgressMinusAnswerTokenRetentionUnseenCI points; line retention improves by \\PairedTargetProgressMinusAnswerLineRetentionSeen \\PairedTargetProgressMinusAnswerLineRetentionSeenCI and \\PairedTargetProgressMinusAnswerLineRetentionUnseen \\PairedTargetProgressMinusAnswerLineRetentionUnseenCI.',
    'replacement raises RR from \\CrossUserTargetSameUserSeenRR\\% to \\CrossUserTargetOtherUserSeenRR\\% on Seen and from \\CrossUserTargetSameUserUnseenRR\\% to \\CrossUserTargetOtherUserUnseenRR\\% on Unseen.',
    'Same-minus-peer intervals are \\CrossUserTargetSameMinusOtherSeenCI and \\CrossUserTargetSameMinusOtherUnseenCI',
    'Progress-minus-Answer intervals are \\PairedJavaStudentRRCI under student clustering and \\PairedJavaExerciseRRCI under exercise clustering.',
    'Among \\PairedJavaJointRepairs joint repairs, Progress targets increase lexical-token retention by \\PairedJavaLexicalRetention points and line retention by \\PairedJavaLineRetention points, with intervals \\PairedJavaLexicalStudentCI and \\PairedJavaLineStudentCI.',
    'Replacing greedy decoding by one stochastic draw costs 7.6 points \\StochasticOneMinusGreedyOneSeenCI, whereas execution-selecting three of those identical fixed draws contributes \\SameDrawThreeMinusOneSeen points \\SameDrawThreeMinusOneSeenCI on Seen.',
    'Through \\(T=1.0\\) the one-draw rate stays within \\SweepTOnePointZeroSeenSingleRR--\\SweepTPointTwoSeenSingleRR\\% on Seen, the three-draw union reaches \\SweepTOnePointZeroSeenRR/\\SweepTOnePointZeroUnseenRR\\%, and at \\(T=1.5\\) the decoder collapses to \\SweepTOnePointFiveSeenRR/\\SweepTOnePointFiveUnseenRR\\%.',
    'the matched base-model three-draw union reaches only \\BaseStochasticThreeSeenRR/\\BaseStochasticThreeUnseenRR\\%, so adaptation adds \\AnswerStochasticMinusBaseSeen points \\AnswerStochasticMinusBaseSeenCI on Seen and \\AnswerStochasticMinusBaseUnseen points \\AnswerStochasticMinusBaseUnseenCI on Unseen.',
    'changes RR by \\CheckpointStochasticMinusSameCheckpointSeen points \\CheckpointStochasticMinusSameCheckpointSeenCI on Seen and \\CheckpointStochasticMinusSameCheckpointUnseen points \\CheckpointStochasticMinusSameCheckpointUnseenCI on Unseen.',
    'Three greedy checkpoints gain \\FactorialGreedyThreeMinusOneSeen \\FactorialGreedyThreeMinusOneSeenCI and \\FactorialGreedyThreeMinusOneUnseen \\FactorialGreedyThreeMinusOneUnseenCI points over one, but under the matched stochastic decoder distinct checkpoints add only \\FactorialDistinctMinusSameSeen points \\FactorialDistinctMinusSameSeenCI and \\FactorialDistinctMinusSameUnseen points \\FactorialDistinctMinusSameUnseenCI.',
    'Absolute Seen/Unseen rates on that stack are \\FactorialGreedyOneSeenRR/\\FactorialGreedyOneUnseenRR\\% for one greedy checkpoint, \\FactorialGreedyThreeSeenRR/\\FactorialGreedyThreeUnseenRR\\% for three greedy checkpoints, \\FactorialSameThreeSeenRR/\\FactorialSameThreeUnseenRR\\% for a same-checkpoint stochastic triple, and \\FactorialDistinctThreeSeenRR/\\FactorialDistinctThreeUnseenRR\\% for a distinct-checkpoint triple, against \\CurrentOnlyAnswerThreeSeenRR/\\CurrentOnlyAnswerThreeUnseenRR\\% on the historical one.',
    'Terminal higher & \\PairedJavaExercisesTerminalHigher & Terminal higher & \\PairedJavaLexicalRetentionLossShare\\%',
    'Tied & \\PairedJavaExercisesTied & Tied & \\PairedJavaLexicalRetentionTieShare\\%',
    'Progress higher & \\PairedJavaExercisesProgressHigher & Progress higher & \\PairedJavaLexicalRetentionGainShare\\%',
    'Extra terminal repairs & \\PairedJavaExerciseDeficitTotal & Median gain & \\PairedJavaLexicalRetentionGainMedian',
    'Largest gap & \\PairedJavaExerciseDeficitMaximum & Retention range & \\PairedJavaLexicalRetentionMinimum / \\PairedJavaLexicalRetentionMaximum',
    'One exercise accounts for \\PairedJavaExerciseDeficitMaximum of the \\PairedJavaExerciseDeficitTotal additional terminal repairs, and there progress targets repair \\PairedJavaWorstExerciseProgressRepairs of \\PairedJavaWorstExerciseExamples trajectories against \\PairedJavaWorstExerciseTerminalRepairs.',
    'Line retention behaves the same, zero for \\PairedJavaLineRetentionTieShare\\% of students with maximum \\PairedJavaLineRetentionMaximum.',
    'the progress rule repairs \\PairedTargetProgressSeenRR\\% of Seen inputs and improves \\PairedTargetProgressSeenIR\\%, so a further \\PairedTargetProgressSeenImproveOnly points receive a program that advances without passing, against \\PairedTargetAnswerSeenRR\\% and \\PairedTargetAnswerSeenIR\\% for the terminal rule.',
    'The same two gaps are \\PairedTargetProgressUnseenImproveOnly and \\PairedTargetAnswerUnseenImproveOnly points on Unseen, and \\PairedJavaProgressImproveOnly against \\PairedJavaAnswerImproveOnly on Java, where terminal targets already repair \\PairedJavaAnswerRR\\% outright.',
    'Most students who receive a working repair from either rule get back the same amount of their own code, about a third get more, by a median of \\PairedJavaLexicalRetentionGainMedian points, and a few get less.',
    'Per-budget Seen rates are \\CurrentOnlyAnswerThreeTEDFiveSeenRR/22.5/4.8\\% at TED 5, \\CurrentOnlyAnswerThreeTEDTenSeenRR/32.4/8.0 at 10, \\CurrentOnlyAnswerThreeTEDTwentySeenRR/44.0/13.9 at 20, \\CurrentOnlyAnswerThreeTEDFortySeenRR/50.9/30.4 at 40, \\CurrentOnlyAnswerThreeTEDEightySeenRR/56.0/50.8 at 80, and \\CurrentOnlyAnswerThreeTEDOneSixtySeenRR/57.9/67.6 at 160',
    'On Unseen, Mixed versus current-only Answer-3Seed is 38.8\\% versus \\CurrentOnlyAnswerThreeTEDFiveUnseenRR\\% at 5, 48.0\\% versus \\CurrentOnlyAnswerThreeTEDTenUnseenRR\\% at 10, and 57.6\\% versus \\CurrentOnlyAnswerThreeTEDTwentyUnseenRR\\% at 20',
    'The gains are \\PromptFrozenMixedCurrentMinusFullSeen/\\PromptFrozenAnswerNineCurrentMinusFullSeen Seen points and \\PromptFrozenMixedCurrentMinusFullUnseen/\\PromptFrozenAnswerNineCurrentMinusFullUnseen Unseen points for Mixed/Answer, with all intervals excluding zero.',
    'The primary five-fold cross-fitted mixed-minus-terminal contrast is +\\CrossFitMixedMinusAnswerNineSeen points \\CrossFitMixedMinusAnswerNineSeenCI, compared with the non-cross-fitted +\\MixedMinusAnswerNineSeen \\MixedMinusAnswerNineSeenCI.',
    'changes the raw gap into \\DifficultyMatchedUnseenMinusSeen equal-problem points \\DifficultyMatchedUnseenMinusSeenCI.',
    'Repeating the procedure on all 328 Seen problems with a distinct seed yields \\SeenHiddenMixedHiddenConfirmation\\% and \\SeenHiddenAnswerNineHiddenConfirmation\\% confirmation',
    'current-only Answer-3Seed reaches \\AllPrefixSeenRR\\% and \\AllPrefixUnseenRR\\% RR. The early, middle, and last thirds reach \\AllPrefixEarlySeenRR\\%, \\AllPrefixMiddleSeenRR\\%, and \\AllPrefixLastSeenRR\\% on Seen and \\AllPrefixEarlyUnseenRR\\%, \\AllPrefixMiddleUnseenRR\\%, and \\AllPrefixLastUnseenRR\\% on Unseen.',
    'At 1.5B parameters three checkpoints still gain \\ScaleAnswerThreeMinusOneSeen points over one \\ScaleAnswerThreeMinusOneSeenCI, but mixed-minus-terminal is \\ScaleMixedMinusAnswerNineSeen \\ScaleMixedMinusAnswerNineSeenCI.',
    'positive on four held-out exercises (\\CodeWorkoutProblemMixedMinusAnswerNine points \\CodeWorkoutProblemMixedMinusAnswerNineCI) and inconclusive on held-out students (\\CodeWorkoutStudentMixedMinusAnswerNine \\CodeWorkoutStudentMixedMinusAnswerNineStudentCI).',
    'refitting with one exercise left out keeps the contrast between \\ExerciseSensitivityLOOMinimum and \\ExerciseSensitivityLOOMaximum points, and single exercises range from \\ExerciseSensitivityPerMinimum to \\ExerciseSensitivityPerMaximum points.',
    'Models retrained on them agree with the canonical ones on \\VerdictOrderStrictAgreementSeen\\% and \\VerdictOrderProgressAgreementSeen\\% of Seen repair decisions',
    'Retraining changes Progress RR by +\\VerdictOrderProgressCanonicalMinusAlternativeSeen Seen and \\VerdictOrderProgressCanonicalMinusAlternativeUnseen Unseen points in the canonical-minus-alternative direction.',
    'exact matches between a returned repair and a training-time accepted program occur in \\SeenOverlapMixedExactRate\\% and \\SeenOverlapAnswerNineExactRate\\% of selections, near-duplicates above a 0.90 token-similarity threshold in \\SeenOverlapMixedNearNinetyRate\\% and \\SeenOverlapAnswerNineNearNinetyRate\\%, and median maximum similarity to a same-problem training target is \\SeenOverlapMixedMedianSimilarity\\% and \\SeenOverlapAnswerNineMedianSimilarity\\%.',
)


def definitions(bridge: Path) -> dict[str, str]:
    return {name: value for name, value in re.findall(r'\\newcommand\{\\(\w+)\}\{(.*)\}', bridge.read_text()) if value}


def expand(template: str, defs: dict[str, str]) -> str:
    expanded = re.sub(r'\\([A-Za-z]+)\b', lambda m: defs.get(m[1], m[0]), template)
    return re.sub(r'(?<=[\d\]])\{\}', '', expanded)


def build(bridge: Path, paper: Path):
    defs = definitions(bridge)
    text = paper.read_text()
    bindings, problems = [], []
    for template in CURATED:
        commands = sorted(set(re.findall(r'\\([A-Za-z]+)\b', template)) & defs.keys())
        unknown = set(re.findall(r'\\([A-Z][A-Za-z]+)\b', template)) - defs.keys()
        if unknown:
            problems.append('undefined evidence commands: ' + ', '.join(sorted(unknown)))
        if not commands:
            problems.append('template has no evidence commands: ' + template)
        expanded = expand(template, defs)
        if text.count(expanded) != 1:
            values = ', '.join(name + '=' + defs[name] for name in commands)
            problems.append(f'literal snippet occurs {text.count(expanded)} times, expected once: {values}')
        bindings.append({'template': template, 'commands': commands})
    return {'schema_version': 1,
            'scope': 'ICSE-SEET literal manuscript assertions expanded from retained evidence; not a LaTeX input',
            'bindings': bindings}, problems


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bridge', type=Path, default=Path('paper/fse2027-result-bridge.tex'))
    parser.add_argument('--paper', type=Path, default=Path('paper/main.tex'))
    parser.add_argument('--output', type=Path, default=Path('paper/main.evidence-bindings.json'))
    args = parser.parse_args()
    payload, problems = build(args.bridge, args.paper)
    if problems:
        raise SystemExit('evidence bindings differ:\n  ' + '\n  '.join(problems))
    args.output.write_text(json.dumps(payload, indent=2) + '\n')
    print(json.dumps({'bindings': len(payload['bindings']),
                      'commands': len({c for r in payload['bindings'] for c in r['commands']})}))
