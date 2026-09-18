# 의존성 복구 및 실제 수리 실험 준비 상태

## 요청 및 수행

사용자는 누락 의존성 해결과 개선 알고리즘의 실제 성능 비교를 요청했다.
프로젝트 `.venv`에 기존 requirements.txt의 범위에 맞는 scikit-learn 1.9.1,
scipy 1.18.1을 설치했다. 함께 설치된 의존성은 cloudpickle 3.1.2,
joblib 1.6.0, narwhals 2.26.0, threadpoolctl 3.7.0이다.
시스템 Python이나 원격 환경은 변경하지 않았다.

실행:

```
uv --no-cache pip install --python .venv/bin/python 'scikit-learn>=1.5' 'scipy>=1.13'
.venv/bin/python -m unittest discover -s tests -p 'test_zpd*.py'
.venv/bin/python -m unittest discover -s tests -p 'test_repair_pilot*.py'
```

결과: ZPD 134/134 통과(이전 15개 skip도 실제 실행), repair pilot 19/19 통과.
fresh-holdout audit의 기존 CSV file-handle ResourceWarning은 남지만 테스트
실패는 없다. 이는 해당 두 suite 결과이며 전체 repository 테스트 완료가 아니다.

## 실제 실험은 미실행

소스 검색상 새 CandidateBank/TwoChannelCoefficients를 연결하는 실행 코드는
합성 `scripts/check_repair_pilot.py`뿐이다. 학습된 계수, 실제 후보 bank 생성 및
원자적 attempt 저장, 실제 evaluator 연결과 모델 선택 lifecycle은 아직 없다.
이전 단계의 '개선'은 알고리즘 후보 구조의 구현이지 측정된 성능 향상이 아니다.

UbuntuServer의 지정 프로젝트를 읽기 전용 확인했다. root checkout은 df650c9,
fse-env/fse-vllm 환경은 존재하며 RTX 5090은 당시 사용률 0%, 187 MiB였다.
outputs 하위 depth 3의 이름에 repair가 포함된 디렉터리는 없었다.
이 제한된 탐색만으로 서버 전체에 모든 관련 산출물이 없다고 단정하지 않는다.
GPU 가용성과 별개로 새 실험 source bundle/provenance 준비가 필요하다.

기존 pilot skeleton 및 v2 plan은 history gate 미통과 시 schema/fixture만
허용한다. fresh holdout도 검정력 기준 미충족으로 중단됐다. 의존성을 설치한
것은 이 과학적 실행 조건을 바꾸지 않는다. eval 정답을 열거나 기존 family를
재개하지 않았다.

## 필요한 결정

기존 predictive gate 실패는 그대로 남기되, '다음 제출 판정 예측'과 '고정 후보의
수리 선택'은 다른 목표라는 가설로 **독립된 개발용 repair pilot**을 새로 허용할지
명시적으로 결정해야 한다. 이는 기존 gate 통과로 간주하는 변경이 아니다.
허용 시 이미 노출된 개발 데이터만 사용하는 별도 실험으로 기록하고, 미개봉
holdout은 사용하지 않으며, 확증적 일반화/교육 효과를 주장하지 않는다.

실행 전 candidate generator/checkpoint, cohort/exposure, 고정 8 attempts,
4-block stability, train/valid 분리, C/H/U 동일 bank와 예산, gain/risk 학습 및
threshold, primary endpoint, unknown 처리, 최대 비용과 중지 규칙을 동결하고
독립 점검해야 한다. 이 결정 전에는 수동 계수를 실제 모델처럼 평가하지 않는다.
