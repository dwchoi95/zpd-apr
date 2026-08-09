# ZPDPatch

ZPDPatch는 실제 학생 submission trajectory에서 실행으로 관측된 개선 관계를
자동 채굴하고, Progress--Strict--Answer adapter portfolio로 다음 repair를 생성하는
trajectory-derived program repair 프로젝트이다.

## Latest Canonical Version

최신 방법론은 **canonical-v5**이다.

- 모든 policy는 동일한 authentic trajectory에 조건부 독립으로 후보를 생성한다.
- Progress는 동일 verdict 안의 testcase-wise Pareto 개선을 학습한다.
- Strict는 coarse verdict가 엄격히 개선되는 전이만 학습한다.
- Answer는 각 non-AC submission을 마지막 Accepted submission에 1:1로 대응한다.
- inference는 Progress--Strict--Answer 순서로 실행하며 AC에서 조기 종료한다.
- 모두 실패하면 current program을 포함해 pass rate 최대, AST edit distance 최소 후보를
  선택하므로 관측 testcase에서 regression을 강제하지 않는다.
- 각 relation의 세 독립 seed checkpoint를 문제 균형 validation에서 실행하고, test를
  보지 않은 채 one-per-relation 포트폴리오를 정확히 선택한다. Unrestricted coverage와
  사전 선언 TED 예산 `{5,10,20,40,80,160}`의 평균 coverage를 각각 선택한다.
- TED 예산 모드에서는 초과 후보를 반환 후 폐기하지 않고 다음 policy까지 계속 실행해,
  예산 이내 AC가 있으면 첫 후보를 반환한다. 없으면 예산 이내 후보와 current program
  사이에서 non-regressive selection을 수행한다.
- 모든 새 후보 생성은 최대 4,096 new tokens에서 종료해, EOS를 내지 않는 실패 출력이
  32K context 전체를 소비하지 않도록 한다.

아래 표는 validation 선택 이전의 고정 seed 포트폴리오 민감도이다. 최종 시스템 수치는
`fse2027-portfolio-validation-selection.json`과
`fse2027-selected-portfolios.json`에서 읽는다.

| Split | Seed 2027 RR | Seed 2028 RR | Seed 2029 RR | Mean +/- SD |
|---|---:|---:|---:|---:|
| Seen | 59.5% | 57.6% | 59.0% | 58.7 +/- 1.0%p |
| Unseen | 73.2% | 74.0% | 70.4% | 72.5 +/- 1.9%p |

논문용 canonical artifact는 다음 위치에 생성한다.

```text
outputs/split-90-10/canonical-v5/
checkpoints/split-90-10/canonical-v5/
checkpoints/split-90-10/canonical-v5-rq2/
checkpoints/split-90-10/canonical-v5-seeds/
checkpoints/split-90-10/codeworkout/
data-canonical-v5/
archive/external/tiktoc/
```

UbuntuServer에서도 작업공간은 `/home/cdw/VSCode/zpd-apr/` 하나만 사용한다.
별도의 sibling checkout이나 `/home/cdw/zpd-apr` 경로를 만들지 않는다.

## Repository Structure

```text
run.py          단일 CLI entrypoint
src/            데이터, 학습, 생성, 실행, 분석 구현
scripts/        canonical-v5 및 FSE 2027 재현 스크립트
tests/          unit/property/artifact tests
paper/          FSE 2027 원고, 그림, 모의 리뷰(dev branch only)
```

`data/`, `outputs/`, `checkpoints/`, model cache는 Git에 포함하지 않는다.

## Environment

```bash
python3 -m venv env
source env/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Dataset Rules

최종 split 전에 Answer, Strict, Progress, evaluation 중 하나라도 Prompt D 기준
4,096 tokens를 넘는 trajectory 전체를 제외한다. 포함된 trajectory의 history, target,
testcase를 부분적으로 자르지 않는다.

Seen problem은 trajectory 수준으로 train/valid/test에 나누며 모든 Seen problem이 세
split에 최소 한 trajectory를 갖는다. Unseen problem은 학습과 retrieval에서 완전히
제외하고 test에만 사용한다.

Adapter별 supervision은 다음과 같다.

- **Answer:** `{S1, Sn}, ..., {S(n-1), Sn}`. 각 입력은 non-AC submission 하나이고
  target은 마지막 Accepted submission이다.
- **Strict:** 마지막 보존 submission보다 verdict가 엄격히 개선된 submission만 남긴
  단조 trajectory의 prefix-target pair이다.
- **Progress:** Strict 전이에 더해, verdict가 같을 때 모든 testcase가 비악화되고
  하나 이상 엄격히 개선되는 submission을 남긴다.

Strict와 Progress의 비교 기준은 직전 원본 submission이 아니라 마지막으로 보존된
submission이다.

## Canonical-v5 Reproduction

전체 canonical-v5 데이터와 testcase cache를 준비한다. 이 단계는 이전 canonical
버전의 산출물에 의존하지 않는다.

```bash
bash scripts/run_canonical_v5_prepare_remote.sh
```

Primary seed의 세 adapter와 RQ1--RQ5 평가를 실행한다.

```bash
bash scripts/run_canonical_v5_gpu_remote.sh
```

최종 independent-policy system과 repeated Answer/generated-feedback 대조군을 실행한다.

```bash
bash scripts/run_fse2027_acceptance_ablations_remote.sh
```

추가 seed 2028/2029의 세 adapter를 모두 다시 학습하고 Seen/Unseen을 평가한다.

```bash
bash scripts/run_fse2027_multiseed_remote.sh
```

동일 타깃 Answer-3Seed 통제를 실행하고, 문제당 한 validation trajectory에서 9개
checkpoint와 27개 relation-constrained 및 84개 size-three 포트폴리오를
평가·선택한 뒤 독립 Seen/Unseen test로 넘긴다. v5 primary는 84개 전체에서
고른 포트폴리오이며, one-per-relation 선택과 Answer-3Seed는 필수 통제다.

```bash
bash scripts/run_fse2027_answer_seed_control_remote.sh
bash scripts/run_fse2027_portfolio_validation_remote.sh
bash scripts/run_fse2027_selected_portfolios_remote.sh
```

선택 평가를 재개할 때는 코드가 동일한 기존 개별·순차 후보의 testcase outcome을
재사용하고, 새 후보만 실행한다. TED는 동일한 ordered unit-cost 정의의 APTED로
다시 계산하며 소규모 AST 쌍에서 기존 ZSS 결과와 교차 검증한다. 동일 split의
모든 후보는 한 canonical current-program outcome을 공유해 timeout 경계의 baseline
변동이 portfolio 비교에 들어오지 않게 한다.

TIKTOC CodeWorkout에서는 동일한 전체-trajectory 4K 규칙과 학생-disjoint split을
적용한다. 각 relation의 세 seed를 새로 학습하고 student-disjoint validation으로
포트폴리오를 선택한 후 student-held-out Java test를 실행한다.

```bash
bash scripts/run_fse2027_codeworkout_remote.sh
bash scripts/run_fse2027_lsgen_budget_remote.sh
```

마지막 스크립트는 LSGen도 성공 후 즉시 중단하지 않고 최대 3후보를 저장한 뒤,
ZPDPatch와 동일한 TED 예산별 계속 탐색 규칙을 replay한다. 동일한 retrieval-pair
설명 cache와 이미 세 후보가 모두 저장된 legacy 행은 token-cap 감사 후 재사용한다.
후보 TED는 unit-cost APTED로 정확 계산하되 AST node-count 차이가 최대 사전 선언
예산 160을 이미 넘으면 sound lower bound로 `>160`만 저장한다.

논문 분석을 재생성한다.

```bash
python scripts/analyze_fse2027_robustness.py \
  --eval-root outputs/split-90-10/canonical-v5/eval \
  --output outputs/split-90-10/canonical-v5/analysis/fse2027-robustness.json

python scripts/analyze_fse2027_multiseed.py \
  --eval-root outputs/split-90-10/canonical-v5/eval \
  --robustness outputs/split-90-10/canonical-v5/analysis/fse2027-robustness.json \
  --output outputs/split-90-10/canonical-v5/analysis/fse2027-multiseed.json
```

## Evidence Manifest

논문 수치는 dataset, evaluation, analysis, checkpoint metadata의 SHA-256 manifest로
source revision에 결합한다.

```bash
REVISION=$(git rev-parse HEAD)
python scripts/build_fse2027_evidence_manifest.py \
  --run-root outputs/split-90-10/canonical-v5 \
  --checkpoint-root checkpoints/split-90-10/canonical-v5 \
  --checkpoint-root checkpoints/split-90-10/canonical-v5-rq2 \
  --checkpoint-root checkpoints/split-90-10/canonical-v5-seeds \
  --checkpoint-root checkpoints/split-90-10/codeworkout \
  --external-root archive/external/tiktoc \
  --source-revision "$REVISION" \
  --output outputs/split-90-10/canonical-v5/analysis/evidence-manifest.json

python scripts/verify_fse2027_evidence_manifest.py \
  --manifest outputs/split-90-10/canonical-v5/analysis/evidence-manifest.json \
  --run-root outputs/split-90-10/canonical-v5 \
  --checkpoint-root checkpoints/split-90-10/canonical-v5 \
  --checkpoint-root checkpoints/split-90-10/canonical-v5-rq2 \
  --checkpoint-root checkpoints/split-90-10/canonical-v5-seeds \
  --checkpoint-root checkpoints/split-90-10/codeworkout \
  --external-root archive/external/tiktoc
```

UbuntuServer에서는 최종 dev commit 이후 같은 절차와 전체 테스트를 한 번에 실행한다.

```bash
bash scripts/finalize_fse2027_evidence_remote.sh "$(git rev-parse HEAD)"
```

성공 시 manifest 검증과 전체 테스트를 통과한 source revision이
`analysis/FSE2027_COMPLETE`에 기록된다. 최종화는 실험에서 생성한 TeX
result bridge와 `paper/fse2027-result-bridge.tex`의 바이트 동일성 및 논문의
신규 결과군 참조도 함께 검사한다.

## Verification

```bash
python -m unittest discover -s tests -v
bash -n scripts/run_canonical_v5_prepare_remote.sh
bash -n scripts/run_canonical_v5_gpu_remote.sh
bash -n scripts/run_fse2027_acceptance_ablations_remote.sh
bash -n scripts/run_fse2027_multiseed_remote.sh
bash -n scripts/run_fse2027_portfolio_validation_remote.sh
bash -n scripts/run_fse2027_selected_portfolios_remote.sh
bash -n scripts/run_fse2027_codeworkout_remote.sh
bash -n scripts/run_fse2027_lsgen_budget_remote.sh
```

FSE 2027 원고는 `paper/main.tex`이며 현재 PDF는 본문 18쪽 이내와 참고문헌 3쪽으로
빌드된다. 최종 결과 반영 후에도 18+4 제한과 시각 레이아웃을 다시 검사한다.
독립 심사는 `paper/reviews/PROTOCOL.ko.md`의 무이력·새 리뷰어 절차를 따른다.
