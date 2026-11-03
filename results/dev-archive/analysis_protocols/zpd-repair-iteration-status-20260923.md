# 2026-09-23 자율 후속: 퇴행 원인 분해와 위험 필터

## 완료 결과와 원인

September22 고정 재검증은 2026-09-22 22:22:24 KST 완료되었다. 새 128개에서
이력 없는 C는 84 AC/24 퇴행/6 불확정, first는 78/20/6이었다. 원래 오답인
116개에서는 C79 vs first73 수리, 퇴행은23 vs19다. 결과를 로컬로 동기화하고
generation/prediction/evaluation/assessment/root COMPLETE의 SHA 및 원시 label
재집계를 확인했다. 원본 결과나 불확정 사례를 바꾸지 않았다.

별도 agent의 사례 진단은 `zpd-repair-regression-diagnosis-20260923.md`에 있다.
핵심은 C가 기준선의 실패24개를 고치는 동시에 기준선의 정답18개를 놓쳤고,
퇴행14개를 새로 만들면서10개를 회피했다는 것이다. AC가 은행에 있는데 놓친
29개 중22개는 선택 후보가 퇴행했다. 후보 생성 부재가 주된 병목은 아니다.

원본 유지 후보는 구현상 포함되어 있지만 학습된 no-op 지표 계수가 음수여서
전체128개에서 수정 후보를 골랐다. 이는 작은 학습자료의 수정 선호 빈도와
일치하며, 점수 여유를 안전성으로 해석할 수 없다. 같은 토큰 bag에서 연산·검사
순서만 다른 AC/nonAC 쌍도1개 확인했으나 이번 family에서는 표현까지 동시에
바꾸지 않는다. H/C는 규제가 달랐으므로 이력 자체의 효과로 단정하지 않는다.

불확정6개는 원본의 AC/TLE 실행 불일치2개 및 MemoryError 관련4개다. 기존
계약은 원본이 불확정이면 비교 전체를 불확정으로 둔다. 이들을 제거하거나
재분류해 성공률을 높이지 않는다.

## 실행할 고정 수정

`zpd-repair-risk-development-20260923.md`에 사전 고정했다.

- 신규 train256명·23문제·256 banks. 이전352명과 current→old 전체 source
  중복을 제외했다. 전체 이력 보존, strict-past matched donor 유지.
- 원래64명과 확장320명 학습을 비교한다. C/H/U 모두 lexical C=.1로 고정하고,
  독립 감사 지적에 따라 pair 총가중치1900, risk 총가중치467을 규모와 무관하게
  유지한다. 학습자료 증가와 정규화 약화를 혼동하지 않도록 한 수정이다.
- 정답 우선 순위 모델과 별도 퇴행 위험 모델을 각각6개씩 학습한다. 첫 후보보다
  예측 위험이 높지 않은 후보 안에서 순위를 적용하고, baseline/no-op을 보존한다.
  예측 위험의 제한은 실제 비퇴행 보장이 아니다.
- 모델을 봉인한 뒤 기존32+128+128 개발 자료를 모두 보고한다. 평가 자료는
  학습에 넣지 않으며, 이 자료를 새 확증 결과나 ZPD 효과라고 부르지 않는다.
- primary는 train320/C/filtered로 고정한다. 두128 각각에서 AC 증가와 관측·
  최악경우 퇴행 비악화를 모두 만족할 때만 별도 새 개발 재검증 준비에 진입한다.

준비 manifest SHA256:
`6a13658d5409d817ad4655efa7fe8a31fa84ec65a2efb24a03086920baaac793`.
생성은64 banks씩4묶음, 총2,048 attempts 상한. 동일4-block 평가가 완전히
끝나야 학습하고, 이후 집계까지 자동 연결한다. 미개봉 test와 paper는 그대로 둔다.

## 검증 및 실제 원격 시작

독립 실행 감사는 신규 준비16 + launcher8 + risk11 + fit runner9 =44개 합성
테스트를 통과했다. 첫 설계의 총 loss 가중치 confound와 sigmoid 포화 시 잘못된
위험 비교를 실행 전에 수정했다. 확률 표시와 별개로 logit의 순서를 비교한다.
이 테스트 통과는 코드 계약 검증이지 실측 성능·안전성 입증이 아니다.

로컬 전체 ZPD255 + prototype19 통과. 깨끗한 서버 사본에서는 기존 로컬 미커밋
fresh-holdout 테스트6개가 빠져 ZPD249 + prototype19, 총268개가 모두 통과했다.

- Upstream dev commit: `51b872bb`
- Clean snapshot: `f351d1c38dc5bcbb565d1ee22bdd6315f6c6e8f9`
- Bundle SHA256:
  `950c0f32db0f2e91ed2e7457f295c34da6090b05792a3dcc179fdb8f5e451496`
- Protocol SHA256:
  `896f92c96cc7ceb157a3d14582b539262b0b4b7a2e2be112b87b66c96cd339fc`
- Remote source: `/home/cdw/VSCode/zpd-apr/.runtime/repair-risk-20260923-v1`
- Remote output: `/home/cdw/VSCode/zpd-apr/outputs/zpd-repair-risk-development-20260923/run-v1`
- Remote log: 같은 출력 상위 폴더의 `run-v1.log`
- tmux: `zpd-repair-risk-20260923`
- Actual start: **2026-09-23 17:51:32 KST**

17:52:04 확인 시 데이터/계보/runtime 사전 검사를 통과한 launch.json이 존재하며,
GPU 28,305 MiB, 사용률49%로 CUDA graph 초기화를 수행했다. 새 vLLM 캐시와
설정 파일도 프로젝트의 `.cache`와 `.config` 아래에 기록하도록 경로를 지정했다.
원래 모델·생성 파라미터·테스트케이스·평가 규칙은 바꾸지 않았다.

신규 은행의 testcase 수 합계는5,141이며, bank당 원본+8개 후보를 모두 다르게
생성한 경우4-block 실행 상한은185,076 testcase다. 기존128 평가의 약85분과
규모를 기준으로 **20:30~21:30 KST** 집계를 예상하지만 타임아웃 분포에 따라
달라질 수 있다. 실제 학습과 성능 비교는 모든 새 실행 label이 완료된 다음이다.
아직 이 family의 성능 향상 결과가 나온 것으로 해석해서는 안 된다.
