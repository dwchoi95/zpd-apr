# FSE 2027 Research Track 모의 리뷰: Round 2

## 현재 판정

- Overall Merit: **3. Borderline / Major Revision**
- Reviewer confidence: **4/5**
- Originality: **4/5**
- Importance: **4/5**
- Soundness: **4/5**
- Evaluation: **3/5**
- Presentation: **4/5**
- Related-work comparison: **4/5**

## Round 1 이후 달라진 핵심

원고는 세 데이터 필터를 병렬적인 heuristic으로 제시하던 상태에서, verdict
severity와 testcase product order로 정의된 nested execution-evidence order로
전환되었다. 유한 단조 supervision, Strict event 포함, assistance-horizon nesting,
observed-test non-regression, minimum-breadth escalation을 명제와 증명으로
제시하고, 실행 가능한 reference semantics와 여섯 property test를 추가했다.

방법론도 개선되었다. 생성된 후보와 outcome을 다음 adapter prompt에 넣던
Generated Feedback 방식을 최종 방법에서 제거하고, 모든 policy가 authentic
trajectory에 조건부 독립인 candidate portfolio를 구성하게 했다. 이 변경은
Seen RR을 56.6%에서 59.5%로 +2.91%p 높였으며, problem-cluster 95% CI
[0.81, 5.01]로 0을 제외한다. 최종 portfolio는 Answer 단독보다 +9.43%p
[7.59, 11.33], Zero-shot보다 +28.79%p [24.45, 33.11] 높다.

## 해결된 주요 지적

- **M1 이론 부재:** 다섯 명제, 증명, executable reference semantics 및
  canonical dataset 전수 audit로 해결되었다.
- **M2 problem dependence:** 모든 핵심 효과에 problem-cluster bootstrap과
  problem-balanced estimand가 추가되었다.
- **M4 순서 근거:** assistance horizon으로 breadth order를 유도하고, 여섯
  permutation 전수 replay로 P--S--A가 minimum breadth와 minimum TED를
  선택함을 보였다.
- **M3 generated feedback:** 독립-policy 방식이 generated-feedback 방식보다
  유의하게 우수하므로 최종 알고리즘 자체가 개선되었다.

## Accept 이전에 남은 사항

1. ~~Answer×3 Seen/Unseen 및 독립-policy Unseen 결과를 RQ4--RQ5에 반영한다.~~ 완료.
2. seed 2028/2029 재학습 결과로 training variance를 보고해야 한다.
3. canonical evidence manifest에 dataset, evaluation, checkpoint metadata의
   SHA-256과 source revision을 봉인해야 한다.
4. 위 결과를 반영한 PDF가 본문 18쪽과 참고문헌 4쪽 한도를 지키는지
   렌더링 검증해야 한다.

현재 novelty와 technical originality는 Accept 수준으로 올라왔고 사전 선언한
핵심 대조군도 완료되었다. 다중 seed와 artifact 봉인이 아직 완료되지 않아 Overall
Merit 4 확정은 보류한다. 남은 항목이 수치와 artifact로 채워진다면 예상 판정은
4. Accept이다.
