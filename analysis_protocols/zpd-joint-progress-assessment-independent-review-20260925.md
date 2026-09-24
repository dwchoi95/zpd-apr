# Joint progress assessment 독립 검토 — 2026-09-25

## 판정

**Pure supplied-input assessment 범위에서 PASS.**
기존13방법 repair/mechanism/CF gate를 그대로 유지하고, 사전 명시된 C_joint 비교를
추가 conjunction으로만 적용한다. 현재 검토한 source·합성 범위에서 고쳐야 할
구체적 blocker를 찾지 못했다. 이 PASS는 actual35 fits, 예측 봉인, 평가 label
출처 또는 empirical release를 인증하지 않는다.

본 검토자는 이 root 작성 assessment 모듈/저자 tests의 비작성자다. 관련 candidate
설계 문서와 두 파일 전문을 읽고, 새 독립 Fraction 회귀를 작성했다. 본 단계에서는
실제 cohort/label/model/feature 본문을 읽지 않았으며 fit, I/O 실험, SSH는 없었다.
저자 source·tests·gate를 바꾸지 않았다.

## 동결 검토 대상

| 파일 | SHA-256 |
|---|---|
| `scripts/zpd_joint_progress_assessment.py` | `ed0e0cd512c4b9b1562374e7e08fb4cc8b0266711aa0e6addc0e2bd48e60b19d` |
| `tests/test_zpd_joint_progress_assessment.py` | `e73306b9f2c1ca0a609b9cd7c39dd0180aea86f1c5b04c44c4b254160307f1ae` |
| candidate 설계 문서 | `0a98c47abc1da7b2323763c7616592c00ea7bc2b27426b00e5a99ec4bc611f32` |
| 독립 review tests | `29068c190f7acfa2305667cf5ba7dd84ea5f2be65259b35d783ce2a360dece8e` |

검토 시작·종료 사이 위 저자 파일은 변하지 않았다. 고정 fit/serialization order는
`H,Jm,HS,U,L,CF,C_joint`; 전체14방법은 여기에3 baseline,3 shared-H diagnostic,
no-op을 더한 정확한 roster다.

## 검토한 계약

- `project_progress`는 모든 recipient를 유지하는 exact13방법 투영이다. 새 C_joint
  항목만 제거하며, 기존 `progress.assess`에 cohort/labels를 그대로 전달한다.
- 기존 검증이 unique example/user/bank, problem-held5fold, exact label coverage,
  stable/unknown 의미, no-op, 예측 identity와 기존 choice 유효성을 검사한다.
  C_joint도 문자열이며 원래 해당 bank의 후보여야 한다. missing/extra method나
  recipient, boolean·외부후보 선택을 허용하지 않는다.
- 기존 gate 객체는 별도로 보존하고, 새 성공은
  `inherited_progress_gates_passed AND joint_current_contribution`이다.
  C_joint나 diagnostic의 우수한 결과가 기존 H 실패를 구제할 경로는 없다.
- C_joint 조건은 CF와 동일하다: full 및 known-current-nonAC에서 strict AC lower
  개선, regression lower/upper nonworse, pooled와 equal-problem 모두 요구한다.
  Known-current-AC는 세 지표 모두 nonworse이며, full held folds 중4/5 이상에서
  AC lower nonworse를 추가한다. 동률은 strict improvement가 아니다.
- Unknown을 분모에서 빼거나 확정 실패로 바꾸지 않는다. Equal-problem은 고정
  문제별 Fraction의 평균이며 pooled 값으로 대체하지 않는다. 빈 현재상태 그룹은
  not-evaluable/FAIL이지 통과가 아니다. Fold4/5는 full fold 비교다.
- 이전 전체·fold·현재상태 subgroup·subgroup-fold·문제별 셀과 paired switches는
  새 C_joint 선택에 따라 변하지 않는다. 평가 입력을 in-place 변경하지 않는다.

## 독립 합성 확인

```
.venv/bin/python -B -m unittest tests.test_zpd_joint_progress_assessment tests.test_zpd_joint_progress_assessment_review tests.test_zpd_repair_progress_assessment tests.test_zpd_repair_feedback_assessment -v
```

**29/29 PASS, 3.117초**, `git diff --check` PASS.
저자 신규9 + 기존18 + 독립2 tests다. 독립 첫 test는 고정 seed20260925의80개
합성 구성에서 모든14방법 선택을 바꾸고 문제 크기를 불균등하게 만든다. 새 C_joint
조건의 pooled/equal-problem/unknown/하위집단/4-of-5를 별도 `Fraction` 산식으로
재계산하여 모든 boolean과 비교한다. 둘째 test는 C_joint가 AC/nonAC/regression/
unknown/no-op을 고를 때도 모든 기존 full/fold/subgroup/subgroup-fold의 결과와
equal-problem·문제별 셀이 정확히 불변인지 검사한다.

## 적용 범위와 남은 의무

이 pure 함수는 작은 합성 인구도 평가하도록 설계되어 있어 스스로320/23/2544,
35개 fit 또는 all-predictions-before-label barrier를 강제하지 않는다. 이는 현재
docstring과 일치하며 누락된 empirical 인증을 PASS한 것으로 간주하면 안 된다.
별도 coordinator/worker/guard와 독립 결과 감사가 실제 고정 인구·source/runtime/
scaler·label 계약·예측 봉인을 인증해야 한다.

원래 progress32 H와의 architecture 진단은 candidate 문서의 별도 non-promotable
보고 의무다. 이 pure14방법 assessment에 old-H를 fifteenth method로 추가하지 않은
것은 명세와 일치한다. 향후 driver에서 그 의무를 누락해도 이 모듈 검토가 대신
충족시키지는 않는다. Nested C_joint/CF의 유효 용량 차이와 adaptive development
한계도 사라지지 않으며, 실제 우월성 또는 ZPD 학습효과는 아직 미측정이다.
