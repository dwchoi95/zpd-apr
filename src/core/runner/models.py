from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Verdict(StrEnum):
    AC = "AC"
    WA = "WA"
    TLE = "TLE"
    RE = "RE"
    CE = "CE"


@dataclass(frozen=True)
class TestCase:
    __test__ = False

    case_id: str
    input_text: str
    expected_text: str


@dataclass
class CaseOutcome:
    case_id: str
    verdict: Verdict
    runtime_sec: float = 0.0
    stdout: str = ""
    stderr: str = ""

    def to_json(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["verdict"] = self.verdict.value
        return payload


@dataclass
class SubmissionOutcome:
    submission_id: str
    problem_id: str
    language: str
    source_verdict: str | None
    verdict: Verdict
    cases: list[CaseOutcome] = field(default_factory=list)
    compile_error: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "submission_id": self.submission_id,
            "problem_id": self.problem_id,
            "language": self.language,
            "source_verdict": self.source_verdict,
            "verdict": self.verdict.value,
            "compile_error": self.compile_error,
            "tc_outcomes": {case.case_id: case.verdict.value for case in self.cases},
            "cases": [case.to_json() for case in self.cases],
        }
