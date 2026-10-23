# FSE 2027 Research Track 모의 리뷰: Round 3

## 판정

- Overall Merit: **4. Accept**
- Reviewer confidence: **4/5**
- Originality: **4/5**
- Importance: **4/5**
- Soundness: **4/5**
- Evaluation: **4/5**
- Presentation: **4/5**
- Related-work comparison: **4/5**

평가는 FSE 2027 Research Track CFP가 명시한 originality, importance of
contribution, soundness, evaluation, quality of presentation, related-work
comparison을 따른다. 공식 CFP는 본문과 그림 18쪽 및 참고문헌 4쪽, 익명화,
Conclusion 뒤 Data Availability, 재현 패키지를 요구한다:
<https://conf.researchr.org/track/fse-2027/fse-2027-papers>.

## 요약

이 논문은 실제 학생 submission trajectory에서 실행으로 관측된 전이만 채굴해
Progress, Strict, Answer 정책을 학습하고, 독립적으로 생성한 후보를 실행 기반으로
순차 선택하는 ZPDPatch를 제안한다. 기여는 단순한 세 LoRA adapter 조합이 아니다.
verdict/testcase product order, assistance horizon, terminal closure를 하나의
execution-evidence 구조로 정식화하고, supervision의 유한 단조성, Strict event의
Progress 포함, observed-test non-regression, minimum-breadth escalation을 명제와
실행 가능한 certificate로 연결한다.

주 실험에서 Seen RR은 Zero-shot 30.7%와 가장 강한 단일 Answer 50.1%보다 높은
59.5%이다. same-problem retrieval인 LSGen의 80.2%보다는 낮지만 성공 patch의 평균
TED가 훨씬 작고 Unseen 문제에도 적용된다. heterogeneous independent portfolio는
동일한 최대 세 번 생성 예산의 Answer×3보다 Seen에서 4.31%p 높고, generated
feedback 방식보다 2.91%p 높다. 후자의 problem-cluster 95% CI [0.81, 5.01]은
0을 제외한다.

추가 QLoRA seed 2028/2029는 Round 2의 마지막 핵심 불확실성을 해소한다. 세 seed의
Seen RR은 59.5/57.6/59.0%(평균 58.7%, 표준편차 1.0%p), Unseen RR은
73.2/74.0/70.4%(평균 72.5%, 표준편차 1.9%p)이다. 모든 Seen seed가 이전
Generated Feedback 결과 56.6%보다 높다. 이 비교는 paired causal contrast로
과장하지 않고, 학습 변동의 경험적 범위로 정확히 서술되어 있다.

## 이전 리뷰 대비 개선

| 기준 | Round 1 | Round 2 | Round 3 |
|---|---:|---:|---:|
| Overall Merit | 3 | 3 | **4** |
| Originality | 3 | 4 | **4** |
| Soundness | 2 | 4 | **4** |
| Evaluation | 3 | 3 | **4** |
| Presentation | 4 | 4 | **4** |
| Related work | 3 | 4 | **4** |

Round 1의 이론 부재, problem-cluster dependence, repeated-policy control, 순서
정당화, artifact 계보, 단일 seed 문제가 모두 직접적인 방법론 개선 또는 추가
실험으로 해결되었다. Round 2 이후에는 두 추가 seed의 전체 재학습·평가와 evidence
manifest가 추가되었다. manifest는 실험 revision `aa908288a397`에 연결된 143개
dataset/evaluation/analysis/checkpoint record, 총 2,290,121,794 byte를 SHA-256과
JSONL 행 수로 봉인하며, 독립 검증기가 143개 모두의 일치를 확인했다.

## 강점

1. **Originality.** authentic trajectory를 단순 prompt history가 아니라 실행으로
   관측된 reachability relation의 원천으로 사용한다. RQ2의 history-serialization
   null result까지 이용해 기여를 더 정밀하게 분리했다.
2. **Technical soundness.** nested evidence order와 online selector의 증명 경계를
   분리하고, 명제·reference semantics·전수 audit를 동일 artifact에 연결한다.
3. **Evaluation.** Seen/Unseen problem holdout, paired testing, problem-cluster bootstrap,
   problem-balanced estimand, six-order replay, Answer×3, generated-feedback ablation,
   세 training seed가 서로 다른 대안 설명을 통제한다.
4. **Claim discipline.** LSGen의 높은 coverage, RQ2 null result, learner study 부재를
   숨기지 않으며 교육 효과 대신 repair/feedback-authoring substrate로 범위를 잡는다.
5. **Reproducibility.** 원고 수치가 source revision과 2.29 GB evidence graph로
   봉인되고, Data Availability가 공식 형식에 맞게 Conclusion 뒤에 있다.

## 남은 한계와 비치명적 요청

- 단일 7B 모델, Python, Project CodeNet에 한정되므로 architecture/language transfer는
  후속 연구가 필요하다.
- user-held-out split과 실제 학습 효과를 측정하는 learner study는 없다. 현재 논문은
  이를 명시하고 교육적 우월성을 주장하지 않으므로 Reject 사유는 아니다.
- 제출 패키지에는 manifest뿐 아니라 검증 명령과 aggregate table 재생성 명령을
  눈에 띄게 제공해야 한다.
- FSE 2027 생성형 AI 정책에 맞춰 연구 스크립트와 분석 코드 개발에서의 Codex 보조,
  실제 실행 및 독립 검증 책임을 Methods에 공개한 현재 문구를 유지해야 한다.

## 형식 및 artifact 확인

- 본문: 18쪽
- 참고문헌: 2쪽
- 미정의 참조: 0
- overfull box: 0
- Data Availability: Conclusion 직후 배치
- evidence manifest: 143/143 record 검증 성공
- training seeds: 2027, 2028, 2029 전체 평가 완료

## 최종 의견

Round 2에서 Accept를 보류시킨 training variance와 artifact lineage가 모두 실제
산출물로 채워졌다. 핵심 기여는 trajectory-aware prompting이라는 약한 주장보다,
authentic execution trajectory에서 자동 채굴한 nested repair relations와 이를
minimum-breadth candidate portfolio로 변환하는 증명 가능한 설계에 있다. 평가도
주요 대안 설명을 충분히 통제하며 결과 변동 범위를 보고한다. 남은 한계는 논문이
명시한 외적 타당성 범위에 해당하고 핵심 결론을 무너뜨리지 않는다.

**Recommendation: 4. Accept.**
