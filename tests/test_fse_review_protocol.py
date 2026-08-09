import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "paper" / "reviews" / "PROTOCOL.ko.md"


class FSEReviewProtocolTest(unittest.TestCase):
    def test_protocol_preserves_independent_blind_review(self) -> None:
        text = PROTOCOL.read_text(encoding="utf-8")
        normalized = " ".join(text.split())
        self.assertIn(
            "FSE 2027(https://conf.researchr.org/track/fse-2027/fse-2027-papers)에 "
            "제출할 논문인데 평가해줘.",
            text,
        )
        self.assertIn("fork_turns: none", text)
        self.assertIn("`paper/main.pdf` 하나만", text)
        self.assertIn("이전 리뷰에 참여하지 않은 새 서브에이전트", text)
        self.assertIn("응답은 요약하거나 고쳐 쓰지 않고", text)
        self.assertIn("특정 점수나 채택 판정을 유도하지 않는다", normalized)


if __name__ == "__main__":
    unittest.main()
