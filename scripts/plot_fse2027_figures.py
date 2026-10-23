"""Render the FSE 2027 result figures from recorded evidence.

Every value is read from the frozen analysis JSONs, never typed in by hand.
Series identity is encoded by line style and marker first, colour second, so the
figures stay readable in print and under colour-vision deficiency.
"""
import argparse
import json
import re
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BUDGETS = (5, 10, 20, 40, 80, 160)
ACCENT, SECOND, BASE = '#1F6F6B', '#8A6D1F', '#767676'


def style():
    plt.rcParams.update({
        'font.family': 'serif',
        'font.serif': ['Linux Libertine O', 'Libertinus Serif', 'Times New Roman', 'DejaVu Serif'],
        'font.size': 7, 'axes.labelsize': 7, 'axes.titlesize': 7,
        'xtick.labelsize': 6.5, 'ytick.labelsize': 6.5, 'legend.fontsize': 6.5,
        'axes.linewidth': 0.5, 'xtick.major.width': 0.5, 'ytick.major.width': 0.5,
        'lines.linewidth': 1.0, 'lines.markersize': 3.4,
        'grid.color': '#CCCCCC', 'grid.linewidth': 0.4, 'grid.linestyle': ':',
        'legend.frameon': False, 'savefig.bbox': 'tight', 'savefig.pad_inches': 0.01,
        'pdf.fonttype': 42,
    })


def budget_series(lsgen_path, ladder_path):
    budget = json.loads(Path(lsgen_path).read_text())['per_budget']
    ladder = json.loads(Path(ladder_path).read_text())['splits']['seen']['budget_frontier']
    current = {int(row['budget']): row['current_only_answer_3seed']['rr'] for row in ladder}
    pct = lambda x: round(100 * x, 1)
    return {
        'ZPDPatch': [pct(budget[str(b)]['budget_indexed_unconstrained']['repair_rate']) for b in BUDGETS],
        'Current $A_3$': [pct(current[b]) for b in BUDGETS],
        'LSGen': [pct(budget[str(b)]['lsgen']['repair_rate']) for b in BUDGETS],
    }


def reach_series(step_path, lsgen_path):
    """Student demonstrated reach and LSGen repairs within each declared budget."""
    reach = json.loads(Path(step_path).read_text())['splits']['seen']['demonstrated_reach']
    budget = json.loads(Path(lsgen_path).read_text())['per_budget']
    pct = lambda x: round(100 * x, 1)
    return {
        "Students' own step within $B$": [pct(reach['share_within_budget'][str(b)]) for b in BUDGETS],
        'LSGen returns within $B$': [pct(budget[str(b)]['lsgen']['repair_rate']) for b in BUDGETS],
    }


def reach_figure(series, out):
    fig, ax = plt.subplots(figsize=(3.33, 1.95))
    marks = [('o', '-', ACCENT), ('^', ':', BASE)]
    for (name, values), (marker, dash, colour) in zip(series.items(), marks):
        ax.plot(BUDGETS, values, marker=marker, linestyle=dash, color=colour, label=name,
                markerfacecolor='white', markeredgewidth=0.8)
    students, lsgen = list(series.values())
    gap = students[2] - lsgen[2]
    ax.annotate(f'{gap:.1f} points at $B=20$', xy=(20, (students[2] + lsgen[2]) / 2), xytext=(5.6, 52),
                arrowprops=dict(arrowstyle='-', lw=0.4, color='#444444'), fontsize=6.5, color='#444444')
    ax.set_xscale('log', base=2)
    ax.set_xticks(BUDGETS)
    ax.set_xticklabels([str(b) for b in BUDGETS])
    ax.set_xlabel('Declared edit budget $B$ (AST nodes)')
    ax.set_ylabel('Share of the 997 inputs (%)')
    ax.set_ylim(0, 100)
    ax.grid(axis='y')
    ax.set_axisbelow(True)
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    ax.legend(loc='upper left', handlelength=2.2)
    fig.savefig(out)
    plt.close(fig)


def breadth_series(bridge_path):
    bridge = json.loads(Path(bridge_path).read_text())
    temps = bridge['breadth_controls']['temperatures']
    sweep = {s: bridge['breadth_controls']['splits'][s]['temperature_sweep'] for s in ('seen', 'unseen')}
    ks = bridge['answer_breadth_cost_curve']['reported_k']
    curve = {s: bridge['answer_breadth_cost_curve']['splits'][s] for s in ('seen', 'unseen')}
    pct = lambda x: round(100 * x, 1)

    def cell(split, t):
        cells = sweep[split]
        for key in (f'{t:g}', f'{t:.1f}', str(t)):
            if key in cells:
                return cells[key]
        raise KeyError(f'temperature {t} missing from {sorted(cells)}')

    return {
        'temperatures': temps,
        'union': {s: [pct(cell(s, t)['union']['rr']) for t in temps] for s in sweep},
        'single': {s: [pct(cell(s, t)['single_draw_expectation']['mean_rr']) for t in temps] for s in sweep},
        'k': ks,
        'k_union': {s: [pct(curve[s][str(k)]['union_repair_rate']) for k in ks] for s in curve},
        'k_calls': {s: [round(curve[s][str(k)]['mean_sequential_candidates_invoked'], 2) for k in ks] for s in curve},
    }


# Both ZPDPatch portfolios carry the system name; the series keys stay as the verifier reads them.
LEGEND = {'ZPDPatch': 'ZPDPatch (Mixed)', 'Current $A_3$': 'ZPDPatch (Answer)'}


def budget_figure(series, out):
    fig, ax = plt.subplots(figsize=(3.33, 2.0))
    marks = [('o', '-', ACCENT), ('s', '--', SECOND), ('^', ':', BASE)]
    for (name, values), (marker, dash, colour) in zip(series.items(), marks):
        ax.plot(BUDGETS, values, marker=marker, linestyle=dash, color=colour,
                label=LEGEND.get(name, name),
                markerfacecolor='white', markeredgewidth=0.8)
    gap = series['ZPDPatch'][2] - series['LSGen'][2]
    ax.annotate(f'$+${gap:.1f} points', xy=(20, series['ZPDPatch'][2]), xytext=(21, 26),
                arrowprops=dict(arrowstyle='-', lw=0.4, color='#444444'), fontsize=6.5, color='#444444')
    ax.set_xscale('log', base=2)
    ax.set_xticks(BUDGETS)
    ax.set_xticklabels([str(b) for b in BUDGETS])
    ax.set_xlabel('Maximum structural edit budget $B$ (AST nodes)')
    ax.set_ylabel('Seen repair rate (%)')
    ax.set_ylim(0, 75)
    ax.grid(axis='y')
    ax.set_axisbelow(True)
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    ax.legend(loc='upper left', handlelength=2.2)
    fig.savefig(out)
    plt.close(fig)


def breadth_figure(data, out):
    fig, axes = plt.subplots(2, 1, figsize=(3.33, 3.6), constrained_layout=True)
    left, right = axes
    for split, colour, marker in (('seen', ACCENT, 'o'), ('unseen', BASE, '^')):
        label = 'Seen' if split == 'seen' else 'Unseen'
        left.plot(data['temperatures'], data['union'][split], marker=marker, linestyle='-', color=colour,
                  markerfacecolor='white', markeredgewidth=0.8, label=f'{label}, three draws')
        left.plot(data['temperatures'], data['single'][split], marker=marker, linestyle='--', color=colour,
                  markerfacecolor=colour, markeredgewidth=0.8, label=f'{label}, one draw')
    left.set_xlabel('Decoding temperature $T$')
    left.set_ylabel('Repair rate (%)')
    left.set_ylim(0, 90)
    left.set_title('(a) Breadth under a fixed decoder')
    left.legend(loc='lower left', ncol=2, columnspacing=0.8, handlelength=1.6, fontsize=5.8)

    for split, colour, marker in (('seen', ACCENT, 'o'), ('unseen', BASE, '^')):
        label = 'Seen' if split == 'seen' else 'Unseen'
        right.plot(data['k'], data['k_union'][split], marker=marker, linestyle='-', color=colour,
                   markerfacecolor='white', markeredgewidth=0.8, label=label)
        for k, rate, calls in zip(data['k'], data['k_union'][split], data['k_calls'][split]):
            if k in (3, 20):
                right.annotate(f'{calls:.2f} calls', xy=(k, rate), xytext=(0, -9 if split == 'seen' else 5),
                               textcoords='offset points', ha='center', fontsize=6, color='#444444')
    right.set_xscale('log', base=2)
    right.set_xticks(data['k'])
    right.set_xticklabels([str(k) for k in data['k']])
    right.set_xlabel('Candidate budget $k$ (draws at $T=0.8$)')
    right.set_ylabel('Union repair rate (%)')
    right.set_ylim(30, 95)
    right.set_title('(b) Coverage and cost of additional draws')
    right.legend(loc='lower right', handlelength=1.6)

    for ax in axes:
        ax.grid(axis='y')
        ax.set_axisbelow(True)
        for side in ('top', 'right'):
            ax.spines[side].set_visible(False)
    fig.savefig(out)
    plt.close(fig)


def breadth_compact_figure(data, out):
    """One panel for Section IV-D: what more draws buy and what they cost."""
    fig, ax = plt.subplots(figsize=(3.33, 1.85))
    for split, colour, marker in (('seen', ACCENT, 'o'), ('unseen', BASE, '^')):
        label = 'Seen' if split == 'seen' else 'Unseen'
        ax.plot(data['k'], data['k_union'][split], marker=marker, linestyle='-', color=colour,
                markerfacecolor='white', markeredgewidth=0.8, label=label)
        for k, rate, calls in zip(data['k'], data['k_union'][split], data['k_calls'][split]):
            if k in (3, 20):
                ax.annotate(f'{calls:.2f} calls', xy=(k, rate), xytext=(0, -9 if split == 'seen' else 5),
                            textcoords='offset points', ha='center', fontsize=6, color='#444444')
    ax.set_xscale('log', base=2)
    ax.set_xticks(data['k'])
    ax.set_xticklabels([str(k) for k in data['k']])
    ax.set_xlabel('Candidate budget $k$ (draws at $T=0.8$)')
    ax.set_ylabel('Union repair rate (%)')
    ax.set_ylim(35, 92)
    ax.grid(axis='y')
    ax.set_axisbelow(True)
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    ax.legend(loc='lower right', handlelength=1.6)
    fig.savefig(out)
    plt.close(fig)



def bridge_macros(path):
    """Read the checked-in result bridge so figure values are the paper's values."""
    text = Path(path).read_text()
    macros = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", text))
    def point(name):
        return float(macros[name])
    def interval(name):
        lo, hi = macros[name].strip('[]').split(',')
        return float(lo), float(hi)
    return point, interval


ABLATION = (
    ('Fine-tuning vs. base model', 'AnswerStochasticMinusBase'),
    ('Three fixed draws vs. one', 'SameDrawThreeMinusOne'),
    ('Three greedy checkpoints vs. one', 'FactorialGreedyThreeMinusOne'),
    ('Serialized history removed', 'PromptFrozenMixedCurrentMinusFull'),
    ('Mixed targets vs. Answer only', 'MixedMinusAnswerNine'),
    ('Distinct checkpoints vs. one', 'CheckpointStochasticMinusSameCheckpoint'),
)


def ablation_series(bridge_tex):
    point, interval = bridge_macros(bridge_tex)
    rows = []
    for label, stem in ABLATION:
        row = {'label': label}
        for split in ('Seen', 'Unseen'):
            try:
                row[split] = (point(stem + split), interval(stem + split + 'CI'))
            except KeyError:
                row[split] = None
        rows.append(row)
    return rows


def replication_series(bridge_tex, portfolios_path):
    point, interval = bridge_macros(bridge_tex)
    zero = json.loads(Path(portfolios_path).read_text())
    zero = zero['splits']['unseen']['primary_method']['comparisons']['zero_shot']['paired'][0]
    pct = lambda x: round(100 * x, 1)
    lo, hi = zero['cluster_bootstrap_95ci']
    return [
        ('Held-out problems', pct(zero['left_minus_right_instance_weighted']), (pct(lo), pct(hi))),
        ('Smaller model (1.5B)', point('ScaleAnswerThreeMinusOneSeen'), interval('ScaleAnswerThreeMinusOneSeenCI')),
        ('Java, exercises held out', point('CodeWorkoutProblemMixedMinusAnswerNine'),
         interval('CodeWorkoutProblemMixedMinusAnswerNineExerciseCI')),
        ('Java, students held out', point('CodeWorkoutStudentMixedMinusAnswerNine'),
         interval('CodeWorkoutStudentMixedMinusAnswerNineStudentCI')),
    ]


def forest(ax, rows, offsets, colours, markers):
    """Draw one point-and-interval row per entry, newest convention: zero line, no grid clutter."""
    for y, row in enumerate(rows):
        for (split, offset), colour, marker in zip(offsets, colours, markers):
            cell = row[split] if isinstance(row, dict) else None
            if cell is None:
                continue
            value, (lo, hi) = cell
            ax.plot([lo, hi], [y + offset] * 2, color=colour, linewidth=0.9, solid_capstyle='butt')
            ax.plot(value, y + offset, marker=marker, color=colour, markerfacecolor='white',
                    markeredgewidth=0.9, markersize=3.6, label=split if y == 0 else None)
    ax.axvline(0, color='#444444', linewidth=0.6)
    ax.set_yticks(range(len(rows)))
    ax.invert_yaxis()
    ax.grid(axis='x')
    ax.set_axisbelow(True)
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)


def ablation_figure(rows, out):
    fig, ax = plt.subplots(figsize=(2.78, 1.75))
    forest(ax, rows, (('Seen', -0.17), ('Unseen', 0.17)), (ACCENT, SECOND), ('o', 's'))
    ax.set_yticklabels([row['label'] for row in rows])
    ax.set_xlabel('Change in repair rate (points, 95% CI)')
    ax.set_xlim(-6, 33)
    ax.legend(loc='lower right', handlelength=1.4)
    fig.savefig(out)
    plt.close(fig)


def replication_figure(rows, out):
    fig, ax = plt.subplots(figsize=(3.05, 1.3))
    for y, (_, value, (lo, hi)) in enumerate(rows):
        ax.plot([lo, hi], [y, y], color=ACCENT, linewidth=0.9, solid_capstyle='butt')
        ax.plot(value, y, marker='o', color=ACCENT, markerfacecolor='white',
                markeredgewidth=0.9, markersize=3.6)
    ax.axvline(0, color='#444444', linewidth=0.6)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([row[0] for row in rows])
    ax.invert_yaxis()
    ax.grid(axis='x')
    ax.set_axisbelow(True)
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    ax.set_xlabel('Contrast (points, 95% CI)')
    ax.set_xlim(-3, 21)
    fig.savefig(out)
    plt.close(fig)


def check(series, data, reach):
    """Guard against evidence drift: values must match the reported numbers."""
    assert reach["Students' own step within $B$"] == [10.7, 18.5, 30.9, 51.2, 73.4, 90.3], reach
    assert reach['LSGen returns within $B$'] == [4.8, 8.0, 13.9, 30.4, 50.8, 67.6], reach
    assert series['ZPDPatch'] == [22.5, 32.4, 44.0, 50.9, 56.0, 57.9], series['ZPDPatch']
    assert series['LSGen'] == [4.8, 8.0, 13.9, 30.4, 50.8, 67.6], series['LSGen']
    assert series['Current $A_3$'] == [16.9, 28.5, 40.3, 51.4, 61.0, 66.8], series['Current $A_3$']
    assert data['union']['seen'][3] == 57.6 and data['single']['seen'][3] == 42.5
    assert data['k_union']['seen'][-1] == 74.8 and data['k_calls']['seen'][-1] == 7.44
    assert data['k_union']['seen'][0] == 41.0 and data['k_union']['unseen'][-1] == 84.0


def check_effects(ablation, replication):
    """The forest plots must carry the bridge's own point estimates."""
    seen = [row['Seen'][0] for row in ablation]
    assert seen == [27.2, 15.1, 9.8, 8.8, 1.7, -0.1], seen
    unseen = [row['Unseen'][0] if row['Unseen'] else None for row in ablation]
    assert unseen == [6.4, 10.9, 10.8, 7.6, 0.0, 2.4], unseen
    assert [round(value, 1) for _, value, _ in replication] == [12.8, 13.4, 3.9, 0.6], replication


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    analysis = Path('outputs/split-90-10/canonical-v5/analysis')
    parser.add_argument('--bridge', type=Path, default=analysis / 'fse2027-result-bridge.json')
    parser.add_argument('--lsgen-budget', type=Path, default=analysis / 'fse2027-lsgen-budget-controller.json')
    parser.add_argument('--current-ladder', type=Path, default=analysis / 'fse2027-current-only-deployment-ladder.json')
    parser.add_argument('--student-step', type=Path, default=analysis / 'icse-seet-student-step-size-20261023.json')
    parser.add_argument('--portfolios', type=Path, default=analysis / 'fse2027-selected-portfolios.json')
    parser.add_argument('--bridge-tex', type=Path, default=Path('paper/fse2027-result-bridge.tex'))
    parser.add_argument('--outdir', type=Path, default=Path('paper/Figures'))
    args = parser.parse_args()
    style()
    series = budget_series(args.lsgen_budget, args.current_ladder)
    data = breadth_series(args.bridge)
    reach = reach_series(args.student_step, args.lsgen_budget)
    ablation = ablation_series(args.bridge_tex)
    replication = replication_series(args.bridge_tex, args.portfolios)
    check(series, data, reach)
    check_effects(ablation, replication)
    args.outdir.mkdir(parents=True, exist_ok=True)
    budget_figure(series, args.outdir / 'fse2027-budget-frontier.pdf')
    breadth_figure(data, args.outdir / 'fse2027-breadth.pdf')
    breadth_compact_figure(data, args.outdir / 'icse-seet-breadth-cost.pdf')
    reach_figure(reach, args.outdir / 'icse-seet-student-reach.pdf')
    ablation_figure(ablation, args.outdir / 'icse-seet-ablation.pdf')
    replication_figure(replication, args.outdir / 'icse-seet-replication.pdf')
    print(json.dumps({'budget_frontier': series, 'breadth_k_union': data['k_union'], 'student_reach': reach}, indent=1))
