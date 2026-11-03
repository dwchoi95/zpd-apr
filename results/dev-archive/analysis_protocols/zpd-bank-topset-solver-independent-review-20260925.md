# Bank top-set Newton 비작성자 독립 검토

2026-09-25. 판정: **pure solver 구현 범위 PASS**. 실제 학습·실험 release 승인은 아니다.
검토자는 새 bank-plan 모듈의 작성자이나, 여기서 검토한 solver/objective/저자
tests의 작성자는 아니다. 실제 corpus, own-label artifact, 결과, SSH에 접근하지
않았고 이전 35 fits를 재실행하지 않았다. 저장된 실제 모델도 읽지 않았다.

## 고정 대상과 수행 범위

- `scripts/zpd_bank_topset_newton.py` SHA256
  `64c74294bae77d7e7bf037a5e700dcc328aa566cd676d837815e3afebe78bb27`.
- `tests/test_zpd_bank_topset_newton.py` SHA256
  `24a3a8d36648e62cd2bd0d1ff79d3e75578d6affc5e13bb7badb61c1a2d39702`.
- 의존 objective SHA256
  `d4f777f0a346aff413179856af6bddebf348d9b06a320bf62a30c9daf20ef2eb`.
- objective 독립 검토, bank-objective design, bank-topset prospective 문서를
  전문 읽었다. 원래 common-offset 오류와 수정 이력은 선행 리뷰에 보존되어 있다.
- 동결된 저자 tests를 별도 재실행하여 **12/12 PASS, 5.841초** 확인했다.
  실제 native 4131 합성 fit 한 개는 9 updates/9 Cholesky, 5.562초였다.
  나머지에는 zero-design 종료 및 명시적 failure-injection 검사가 포함된다.
  이것은 로컬 synthetic 수치 검증이며 실제 Linux worker의 시간/32-GiB 경계
  인증이나 실제 repair 성능 측정이 아니다.

실행 명령은 여섯 BLAS/thread 환경 변수를 모두 `1`로 설정한 뒤
`.venv/bin/python -m unittest tests.test_zpd_bank_topset_newton -v`이다.
검사 종료 후 source/test SHA가 위 동결 값과 동일함을 다시 확인했다.

## 수식·구현 대조

각 top t의 독립 affine 표현은 `A={0,x_n-x_t}`, logits는
`{0,(x_n-x_t)·theta-log|N|}`이다. 이 softmax의 평균이 gradient,
중심 covariance가 Hessian이며, top 평균·`.1 W_b`·단위 ridge를 적용한다.
생산자의 rest 확률/active/curvature 분해와 작은 score-Hessian 조립은 이와
일치한다. 원 Bank bytes는 그대로 해시하고 모든 수치 곱에는 첫 행을 뺀
design을 사용한다. 추가 normalization, learned offset, intercept는 없다.

새 range는 양의 mass 및 nonempty rest인 모든 top 항에서
`range({0} ∪ {(x_n-x_t)·p})`의 최댓값이다. `max(abs(Xp))`로 대체하지 않았다.
각 LSE의 third central moment 절댓값은 해당 range×variance 이하이므로,
양의 가중합과 ridge에도 고정 방향의 1차원 상계가 성립한다. 따라서
`a=-g·p`, `q=p·Hp`에 대해 고정 alpha는
`min(1, log1p(r*a/q)/r)`이며 r=0에서는 `min(1,a/q)`이다.
이는 exact-real 감쇠 상계이지 floating-point 전체 실행의 interval proof는 아니다.

별도 scratch에서는 생산자의 score-Hessian/HVP/centering/gradient helpers를
재계산에 쓰지 않고 top별 직접 차분, `math.fsum` logits/확률 평균, affine
중심 covariance로 native **4131×4131 Hessian**과 gradient를 구성했다.
seed 20260925, 3개 합성 점: 모든 좌표가 있는 dense case, 공통 `2**10`
offset case, CF형 마지막 16열 zero case. 두 informative banks와 zero-mass
all-top bank를 함께 포함했다. 생산자 Cholesky helper로 구한 방향을 별도
H/g에 대입해 solve residual과 실제 목적함수 변화·analytic 상계를 검사했다.
이는 3개 점의 선형계산이며 optimizer fit은 아니다.

| 독립 대조 | 관측 최대 절댓값 오차 |
|---|---:|
| objective | 0 |
| full gradient | 1.3322676295501878e-15 |
| full Hessian | 4.440892098500626e-16 |
| directional range | 2.6645352591003757e-15 |

독립 H/g 기준 normalized solve residual 최대는 `2.871164388232589e-16`였다.
세 경우 모두 alpha 일치, 음의 analytic 상계, 실제 감소≤상계(+비교용 1e-10)
관계가 성립했다. CF16 zero block은 정확한 identity Hessian 및 zero cross
block으로 남았다. 여기의 비교 allowance는 실제 종료 기준을 완화하지 않는다.

scratch: `/private/tmp/zpd-bank-topset-solver-review.HSYwmw/audit.py`, SHA256
`774b64236dd993685ef81b9bc4b0cf571d1edaf6cf033cb8046f124e1cdf5796`.
NumPy/SciPy와 Cholesky primitive는 공유한다. 독립성은 목적함수/derivative/range
재구성 경로에 있으며 다른 수치 라이브러리·interval arithmetic 인증은 아니다.

## 종료·실패·모델 경계

소스와 합성 tests에서 한 zero start, 최대 2000 updates/Hessian/solve,
2001 loop evaluations+1 fresh final check=최대 2002를 확인했다. loop와 fresh
final gradient 모두 **infinity norm≤1e-8**가 필요하다. final 호출만 nextafter로
기준을 넘기면 FAILED이며 cached gradient로 승격하지 않는다. Cholesky 또는
finite/centered subtraction/descent/solve-residual/unchanged-iterate 실패는
retry, jitter, 다른 optimizer, threshold 확대 없이 종료한다.

저자 unmocked 합성 fit의 독립 scalar optima/최종 gradient와 nested unused
coefficients zero 검사가 통과했다. 모델은 raw rows/top order/weights 해시,
4131 및 objective 고정 configuration, count/trace/runtime/self-hash를 묶는다.
`validate_model(expected_banks=..., expected_weights=...)`는 입력 대조를 추가한다.
이 인수가 없으면 self-consistent certificate 검사일 뿐 실제 입력 ancestry
인증이 아니다. 어느 모드도 저장 gradient 자체의 정직성을 독립 재계산하지는
않는다. 이는 문서화된 pure API 경계이며 아래 별도 감사가 필요하다.

unknown mask, maximal T, 원 pair bank mass, own-fold labels, accepted32/scaler
ancestry 및 전체 coverage는 외부 plan/worker 책임이다. sum(W)=1900만으로
그 사실을 보증하지 않는다. 실제 resource limits와 runtime/source sealing,
35 predictions-before-assessment barrier도 이 solver의 검증 범위 밖이다.
현재 발견한 수정 요구/blocker는 없다. 실제 fitted model의 수치 승인과
repair/history gate 통과를 이 PASS에서 추론하면 안 된다.

## 제안: 저장 모델 final-point 독립 감사 — 아직 구현/실행 아님

`audit_model(banks, weights, model, *, expected_configuration, expected_runtime,
expected_plan_sha256)` 형태의 pure 감사가 적절하다. 은행 배열·mask/mass와 plan
외부 pin은 caller가 인증하되, 감사 내부에서는 producer fit/validate/gradient/
score-Hessian helpers를 호출하지 않고 다음을 수행한다.

1. strict schema/config/runtime, raw array SHA, top-index order, weights, counts,
   iteration bounds, damping scalar 식·trace 자기 일관성을 별도 검사한다.
2. 저장 theta에 대해 위 direct-affine 식으로 각 top loss와 full 4131 gradient를
   `math.fsum` 중심으로 재구성하고 data/ridge/total decomposition을 대조한다.
   float 비교 정책을 사전 고정하되, 독립 gradient 자체는 **≤1e-8 그대로**
   요구한다. 저장 gradient와의 근접성만으로 승인하지 않는다.
3. 실제 zero/constant design columns와 CF/C_joint nested columns의 coefficients
   zero를 검사하고, row-order/raw-feature hash drift를 거부한다.
4. 모든 모델/arm에 동일하게 적용하고 실패는 그대로 기록한다. 새 fit, Hessian
   optimizer replay, 과거 35 fits 재실행은 필요하지 않다.

중간 theta/direction이 저장되지 않으므로 이 final-point 감사로 모든 trace
Hessian/linear solve를 재현했다고 주장할 수 없다. 모델 최종점의 float64
stationarity와 자체 기록의 정합성, 외부 실행 provenance를 구분해 보고해야 한다.
오차 enclosure 없는 float64 agreement를 exact optimum 증명·성능 증명으로
표현하지 않는다. 이 제안은 root의 별도 검토/구현 범위 확정 전 release가 아니다.
