"""Path/roster-only inventory. Candidates are NOT certified fresh holdouts."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from scripts.audit_zpd_history_support import digest_file, rows


def inventory(repo, original, output):
    if output.exists() or output.resolve().is_relative_to(original.resolve()):
        raise ValueError('new project-local output outside original source required')
    if not output.resolve().is_relative_to(repo.resolve()):
        raise ValueError('output must remain in project')
    existing = {p.name for p in (repo / 'data').iterdir() if p.is_dir() and re.fullmatch(r'p\d{5}', p.name)}
    rosters = list((repo / 'data').glob('splits*/problem_split.jsonl'))
    roster_hashes = {str(p.relative_to(repo)): digest_file(p) for p in rosters}
    for p in rosters:
        existing.update(r['problem_id'] for r in rows(p))
    metadata_ids = {p.stem for p in (original / 'metadata').glob('p?????.csv') if re.fullmatch(r'p\d{5}', p.stem)}
    python_available = {key for key in metadata_ids if (original / 'data' / key).is_dir()
                        and any(p.is_dir() and p.name.startswith('Python') for p in (original / 'data' / key).iterdir())}
    candidates = sorted(python_available - existing)
    population = {'original_metadata_problem_ids': sorted(metadata_ids),
                  'original_python_directory_problem_ids': sorted(python_available),
                  'conservatively_excluded_local_problem_ids': sorted(existing),
                  'candidate_problem_ids': candidates}
    canonical = json.dumps(population, sort_keys=True).encode()
    report = {'scope': 'path and split-roster inventory only; not fresh-holdout certification',
              'counts': {k: len(v) for k, v in population.items()},
              'population': population, 'population_sha256': hashlib.sha256(canonical).hexdigest(),
              'roster_sha256': roster_hashes, 'script_sha256': digest_file(Path(__file__)),
              'original_root': str(original), 'metadata_contents_opened': False,
              'program_contents_opened': False, 'label_files_opened': [],
              'fresh_holdout_certified': False,
              'unresolved': ['Deleted/remote/other-project historical exposure is not comprehensively indexed.',
                             'User overlap and exact-code overlap have not been checked.',
                             'Prefix ordering/source completeness/censoring/donor eligibility and future partition are not checked.',
                             'No candidate is selected for fitting or final evaluation by this inventory.']}
    output.mkdir(parents=True)
    (output / 'inventory.json').write_text(json.dumps(report, indent=2) + '\n')
    (output / 'COMPLETE').write_text(digest_file(output / 'inventory.json') + '\n')
    print(json.dumps({'counts': report['counts'], 'fresh_holdout_certified': False}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    for name in ('repo', 'original', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    inventory(args.repo, args.original, args.output)
