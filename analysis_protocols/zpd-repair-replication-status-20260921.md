# Frozen development replication 실행 상태

2026-09-21 16:37 KST 실행 시작. 원래모델 재학습/threshold선택 없이 새128개
개발valid 사례를 평가한다.22문제128bank,최대1024attempt,중복제거 전
testcase실행상한97,560(각bank9sources×4blocks)이다. 원래96사용자와의중복,
new current와old current/prior/donor codeSHA중복을 제거했다. 새 history/donor까지
완전독립이라는 주장은 하지 않는다.

- upstream source: `1989dbd460b08b40bb975dcdc3e6dd3876d02beb`
- clean snapshot: `4a9cd50f74c7badc6db839ba5dcbcf30c2e3e7be`
- bundle SHA: `76787675d16b765ab8cffb09ff8fa7174983baac8f7d50c9a16121b12a9019ff`
- 원격 root: `/home/cdw/VSCode/zpd-apr`
- source: `.runtime/repair-replication-20260921-v1`
- inputs: `outputs/zpd-repair-replication-20260921/prepared-v1`
- output: `outputs/zpd-repair-replication-20260921/run-v1`
- log: `outputs/zpd-repair-replication-20260921/run-v1.log`
- tmux: `zpd-repair-replication-20260921`

독립감사 prep+prediction+assessment19tests 통과,root launcher1test도 통과.
기존32valid에 대한C/H/U 선택96개를 고정계수로 재계산해96/96일치를 확인했다.
clean remote snapshot ZPD169 +prototype19 tests 모두통과. 원격에서bundleSHA대조,
미변경generator/parser/prompts/runtime 및 parentfit관측입력연결을 launcher가 검증한다.

실행순서:64bank생성 두묶음→같은config로병합→prediction봉인→4block실행→assessment.
어떤새label도 prediction봉인 전에 생성하지 않는다. 학습함수를 호출하지 않는다.
partial/unstable은unknown이고6h evaluator예산초과시중지하며 완료표시하지 않는다.
시작시점에는 결과가 없다. 이전실행시간으로 전체약1.5~3h를 예상하되TLE/긴출력과
실행안정성에 따라 달라질 수 있다.

## 재개 확인

generation-0/attempts +generation-1/attempts 합 /1024 → predictions/COMPLETE.json
→ evaluation/completions.jsonl → assessment/report.json → 최상위COMPLETE.json.
모든SHA와unknown분모를검증해H-C netgain interval,RR/퇴행과H-U/H-first를보고한다.
구간이0을포함하면확정개선이라고부르지않는다. 불리한결과도그대로보존한다.
