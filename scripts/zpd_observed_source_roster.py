"""Pure exact-source roster from the certified observed-only repair join.

No file I/O, execution, CLI or outcome access. Callers must first authenticate
the output of audit_zpd_repair_feedback_support.join_observations. In particular,
that join verifies each donor history against its donor's current timestamp,
which is NOT present in its returned rows; this module does not invent it.
Current language is Python by that same join's explicit checked contract.
This roster is a request inventory, never authorization to execute its sources.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import re


VERSION = 'certified_observed_source_roster_v1'
OBSERVATION_FIELDS = frozenset({'example_id', 'user_id', 'problem_id', 'bank_id',
    'fold', 'current_code', 'current_verdict', 'current_timestamp',
    'current_source_sha256', 'history', 'donor_history', 'donor_example_id',
    'donor_user_id', 'observed_source_ids', 'donor_source_ids'})
HISTORY_FIELDS = frozenset({'code', 'verdict', 'timestamp', 'language'})
NOMINAL_VERDICTS = frozenset({'AC', 'CE', 'OTHER', 'RE', 'RESOURCE', 'WA'})
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]*\Z')
_SHA = re.compile(r'[0-9a-f]{64}\Z')


def configuration():
    return dict(version=VERSION, source_identity='problem_id:raw_submission_id',
        execution_identity=['problem_id', 'source_sha256', 'language'],
        position='zero_based_chronological; current_position_is_prior_count',
        current_language='Python_verified_by_upstream_join',
        donor_cutoff='not_supplied; strictly_prior_certified_by_upstream_join',
        recipient_cutoff_revalidated=True, execution_authorized=False,
        non_python='retained_unavailable_for_Python_replay',
        fitting_performed=False, testcase_access=False)


def _digest(source):
    return hashlib.sha256(source).hexdigest()


def _canonical(value):
    return _digest(json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=True, allow_nan=False).encode('utf-8'))


def _identifier(value, name):
    if type(value) is not str or not _ID.fullmatch(value):
        raise ValueError('invalid ' + name)
    return value


def _source_id(value, problem):
    if type(value) is not str or value.count(':') != 1:
        raise ValueError('source identity must be exactly problem:submission')
    pid, raw = value.split(':')
    _identifier(pid, 'source problem ID'); _identifier(raw, 'raw submission ID')
    if pid != problem:
        raise ValueError('source/problem identity mismatch')
    return raw


def _time(value):
    if type(value) not in (int, float):
        raise ValueError('finite real timestamp required')
    try:
        valid = math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError('finite real timestamp required')
    return value


def _text(value):
    if type(value) is not str:
        raise ValueError('exact UTF-8 source string required')
    try:
        return value.encode('utf-8', errors='strict')
    except UnicodeError as exc:
        raise ValueError('exact UTF-8 source string required') from exc


def _language(value):
    if (type(value) is not str or not value or value.strip() != value
            or any(ord(c) < 32 or ord(c) == 127 for c in value)
            or '/' in value or '\\' in value):
        raise ValueError('nonempty declared language required')
    try:
        value.encode('utf-8', errors='strict')
    except UnicodeError as exc:
        raise ValueError('invalid declared language') from exc
    return value


@dataclass(frozen=True)
class SourceRecord:
    problem_id: str
    submission_id: str
    raw_submission_id: str
    user_id: str
    source: bytes
    source_sha256: str
    language: str
    timestamp: int | float
    verdict: str

    @property
    def python_eligible(self):
        return self.language == 'Python'

    def to_json(self):
        value = asdict(self)
        value['source_hex'] = value.pop('source').hex()
        value['python_eligible'] = self.python_eligible
        return value


@dataclass(frozen=True)
class Membership:
    recipient_id: str
    bank_id: str
    user_id: str
    problem_id: str
    fold: int
    current_cutoff: int | float
    role: str
    position: int
    submission_id: str
    source_sha256: str
    donor_example_id: str
    donor_user_id: str


@dataclass(frozen=True)
class Recipient:
    example_id: str
    user_id: str
    problem_id: str
    bank_id: str
    fold: int
    current_cutoff: int | float
    current_source_id: str
    prior_source_ids: tuple[str, ...]
    donor_source_ids: tuple[str, ...]
    donor_example_id: str
    donor_user_id: str


@dataclass(frozen=True)
class ExecutionRequest:
    problem_id: str
    source_sha256: str
    language: str
    submission_ids: tuple[str, ...]


@dataclass(frozen=True)
class SourceRoster:
    sources: tuple[SourceRecord, ...]
    memberships: tuple[Membership, ...]
    recipients: tuple[Recipient, ...]
    execution_requests: tuple[ExecutionRequest, ...]

    def to_json(self):
        # JSON round-trip makes all tuple fields JSON arrays without sharing
        # mutable state with the frozen roster or with another serialization.
        value = dict(configuration=configuration(), execution_authorized=False,
            sources=[v.to_json() for v in self.sources],
            memberships=[asdict(v) for v in self.memberships],
            recipients=[asdict(v) for v in self.recipients],
            execution_requests=[asdict(v) for v in self.execution_requests],
            counts=dict(recipients=len(self.recipients), sources=len(self.sources),
                memberships=len(self.memberships), execution_requests=len(self.execution_requests),
                roles=dict(sorted(Counter(v.role for v in self.memberships).items())),
                languages=dict(sorted(Counter(v.language for v in self.sources).items())),
                folds={str(k): n for k, n in sorted(Counter(v.fold for v in self.recipients).items())},
                problems=len({v.problem_id for v in self.recipients})))
        return json.loads(json.dumps(value, ensure_ascii=True, allow_nan=False))

    @property
    def roster_sha256(self):
        return _canonical(self.to_json())


def build_roster(observations):
    """Validate and freeze certified join rows; never read a path or infer data.

    The production caller separately verifies the frozen320 cohort and all five
    folds. This pure function supports smaller synthetic cohorts but rejects
    invalid fold values and any problem assigned to conflicting folds.
    Prior SHA/language and donor-cutoff authenticity rely on the certified
    upstream join. Byte identity and recipient cutoff are rechecked here.
    """
    if type(observations) not in (list, tuple) or not observations:
        raise ValueError('nonempty certified observation list/tuple required')
    sources = {}; members = []; recipients = []
    examples = set(); users = set(); banks = set(); problem_folds = {}
    donor_owners = {}

    def add_source(problem, ident, user, code, timestamp, verdict, language):
        raw = _source_id(ident, problem)
        data = _text(code); stamp = _time(timestamp); language = _language(language)
        if type(verdict) is not str or verdict not in NOMINAL_VERDICTS:
            raise ValueError('certified nominal verdict required')
        record = SourceRecord(problem, ident, raw, user, data, _digest(data), language, stamp, verdict)
        if ident in sources and (sources[ident] != record
                or type(sources[ident].timestamp) is not type(stamp)):
            raise ValueError('conflicting source identity bytes/time/language/verdict/owner')
        sources[ident] = record
        return record

    for row in observations:
        if type(row) is not dict or set(row) != OBSERVATION_FIELDS:
            raise ValueError('exact certified observation fields required')
        pid = _identifier(row['problem_id'], 'problem ID')
        eid = row['example_id']; _source_id(eid, pid)
        uid = _identifier(row['user_id'], 'user ID')
        did = row['donor_example_id']; _source_id(did, pid)
        duid = _identifier(row['donor_user_id'], 'donor user ID')
        fold = row['fold']
        if type(fold) is not int or fold not in range(5):
            raise ValueError('integer fold in 0..4 required')
        if pid in problem_folds and problem_folds[pid] != fold:
            raise ValueError('conflicting problem fold')
        problem_folds[pid] = fold
        if eid in examples or uid in users:
            raise ValueError('duplicate recipient example or user')
        if uid == duid or eid == did:
            raise ValueError('donor must be a different user and example')
        if did in donor_owners and donor_owners[did] != duid:
            raise ValueError('conflicting donor current owner')
        donor_owners[did] = duid
        current = add_source(pid, eid, uid, row['current_code'], row['current_timestamp'],
                             row['current_verdict'], 'Python')
        if (type(row['current_source_sha256']) is not str
                or not _SHA.fullmatch(row['current_source_sha256'])
                or current.source_sha256 != row['current_source_sha256']):
            raise ValueError('current exact-source SHA mismatch')
        bid = row['bank_id']
        if (type(bid) is not str or not _SHA.fullmatch(bid)
                or bid != _digest((pid + '|' + current.source_sha256).encode('utf-8'))
                or bid in banks):
            raise ValueError('invalid or duplicate bank identity')
        examples.add(eid); users.add(uid); banks.add(bid)
        history = row['history']; donor = row['donor_history']
        ids = row['observed_source_ids']; donor_ids = row['donor_source_ids']
        if (type(history) is not list or type(donor) is not list or not history
                or len(history) != len(donor) or type(ids) is not list
                or type(donor_ids) is not list or len(ids) != len(history) + 1
                or len(donor_ids) != len(donor) or ids[0] != eid):
            raise ValueError('exact nonempty aligned current/prior/donor identities required')
        for ident in (*ids, *donor_ids):
            _source_id(ident, pid)
        if (len(set(ids)) != len(ids) or len(set(donor_ids)) != len(donor_ids)
                or set(ids) & set(donor_ids) or did in donor_ids or did in ids):
            raise ValueError('duplicate, cross-user or donor-current source identity')

        def membership(source, role, position):
            members.append(Membership(eid, bid, uid, pid, fold, current.timestamp,
                role, position, source.submission_id, source.source_sha256, did, duid))

        for role, chain, chain_ids, owner in (('prior', history, ids[1:], uid),
                                             ('donor', donor, donor_ids, duid)):
            previous = None
            for position, (value, ident) in enumerate(zip(chain, chain_ids, strict=True)):
                if type(value) is not dict or set(value) != HISTORY_FIELDS:
                    raise ValueError('exact history source fields required')
                item = add_source(pid, ident, owner, value['code'], value['timestamp'],
                                  value['verdict'], value['language'])
                if (item.timestamp >= current.timestamp
                        or previous is not None and item.timestamp <= previous):
                    raise ValueError('strictly increasing history before recipient cutoff required')
                previous = item.timestamp
                membership(item, role, position)
        membership(current, 'current', len(history))
        recipients.append(Recipient(eid, uid, pid, bid, fold, current.timestamp,
            eid, tuple(ids[1:]), tuple(donor_ids), did, duid))

    for did, owner in donor_owners.items():
        if did in sources and sources[did].user_id != owner:
            raise ValueError('donor current identity conflicts with source owner')
    executions = {}
    for source in sources.values():
        key = source.problem_id, source.source_sha256, source.language
        executions.setdefault(key, []).append(source.submission_id)
    return SourceRoster(tuple(sources[k] for k in sorted(sources)),
        tuple(sorted(members, key=lambda m: (m.recipient_id, m.role, m.position))),
        tuple(sorted(recipients, key=lambda r: r.example_id)),
        tuple(ExecutionRequest(*key, tuple(sorted(ids))) for key, ids in sorted(executions.items())))
