# CodeNet 원본 접근 및 provenance 점검

확인: 2026-09-15 19:12 KST. 읽기 조사만 수행했으며 tar 데이터 다운로드, 계정 사용, 실험, 기존 데이터 변경은 하지 않았다.

## 결론

기존 코드가 참조하는 로컬 `/Users/cdw/VSCode/aria/data/Project_CodeNet`의 metadata/data 존재를 main agent가 확인 중이다. 해당 원본을 읽기 전용으로 검증하는 것이 우선이며, 새 다운로드는 현재 불필요하다. 아래는 대체 접근 경로와 검증 계약이다.

## 공식 배포 및 실제 HEAD 응답

[IBM 공식 README](https://github.com/IBM/Project_CodeNet#relevant-links)는 전체 tar를 7.8GB로 안내하고, 별도 metadata tar는 더 이상 제공하지 않는다고 적고 있다. 그러나 동일 공식 bucket의 기존 metadata 객체 HEAD는 현재 200이었다. 문서와 endpoint 상태의 불일치를 기록하며, HEAD만으로 압축 내용/무결성까지 검증됐다고 간주하지 않는다.

| 객체 | HEAD 상태 | Content-Length | Last-Modified | ETag |
|---|---:|---:|---|---|
| [전체](https://codait-cos-dax.s3.us.cloud-object-storage.appdomain.cloud/dax-project-codenet/1.0.0/Project_CodeNet.tar.gz) | 200 | 8,343,137,473 bytes | 2021-05-05 21:13:40 GMT | `74257cf20935cb2827f01a9652eaa1b9-1592` |
| [metadata](https://codait-cos-dax.s3.us.cloud-object-storage.appdomain.cloud/dax-project-codenet/1.0.0/Project_CodeNet_metadata.tar.gz) | 200 | 294,521,596 bytes | 2021-06-01 16:51:59 GMT | `a66e3916e6ae01b0f316d652b731fe22-57` |

둘 다 `Accept-Ranges: bytes`, `Content-Type: application/gzip`. Multipart ETag를 SHA-256 또는 단일 파일 MD5로 취급하지 않는다. 문제별 파일의 독립 HTTP endpoint는 공식 문서에서 확인하지 못했다. gzip range 지원만으로 임의 tar member 선택 다운로드를 보장하지 않는다. 로컬 tar 또는 해제본이 없다면 metadata 전용 객체의 제한된 수신·무결성 검증을 다음 대안으로 검토할 수 있으나, 이 조사에서는 수행하지 않았다.

[IBM DAX 안내](https://developer.ibm.com/exchanges/data/)는 서비스 종료를 알린다. 예전 dataset 상세 URL이 일반 DAX 안내로 이동하므로 과거 다운로드 안내만으로 현재 가용성을 단정하지 않는다.

## 원본 schema 및 조인

공식 [metadata 설명](https://github.com/IBM/Project_CodeNet#metadata)과 [파일 관계](https://github.com/IBM/Project_CodeNet#relationships-among-the-metadata-and-data)에 따른 경로:

- `metadata/problem_list.csv`: 문제 ID, 원천, 시간/메모리 제한 등.
- `metadata/pNNNNN.csv`: submission_id, problem_id, user_id, date, language, original_language, filename_ext, status, cpu_time, memory, code_size, accuracy.
- `data/<problem_id>/<language>/<submission_id>.<filename_ext>`: 원시 코드. Python은 통상 `Python/sNNNNNNNNN.py`; 실제 row의 language/ext로 해석하고 고정 추정하지 않는다.
- date는 Unix seconds. ID는 익명화되어 있으므로 실제 사용자 재식별을 시도하지 않는다.
- accuracy는 AIZU 필드이며 testcase별 벡터가 아니다. 누락값과 잘못된 수치가 가능하다.

## importer 사전검증 권고 — 프로젝트 자체 판단

1. 기존 23문제 목록을 결과와 무관하게 고정한다. metadata의 모든 Python row를 읽고 AC 보유 여부로 user/problem을 사전 필터링하지 않는다.
2. raw CSV/code hash, byte size, 입력 경로, 접근 시각, 선언된 수집 범위를 manifest에 남긴다. 로컬 파일의 존재만으로 공식 배포본과 동일하거나 완전하다고 단정하지 않는다.
3. submission ID 중복·동일 ID 내용 충돌·파일 누락·문제 ID 불일치·비정상 date·timestamp tie를 별도 집계한다. tie의 임의 ID 정렬을 실제 시간 순서로 해석하지 않는다.
4. 동일 코드와 실패 반복을 보존한다. prefix 특징과 미래 label을 분리한다. 끝까지 AC가 관측되지 않은 sequence를 삭제하지 않고, 'never successful' 대신 '관측 기간 내 AC 없음'으로 기록한다.
5. 전체 metadata는 기존 eventual-AC archive의 선택 편향을 검사하는 데 충분할 수 있으나, 실제 코드 기반 상태 구성에는 대응 source files가 추가로 필요하다. CodeNet 수집 범위를 넘어선 평생 제출 완전성은 알 수 없다.
6. 출력은 zpd-apr 내부에만 작성하고 외부 원본은 읽기 전용으로 유지한다. 메타데이터 판정과 재실행 판정을 분리하며 로컬 testcase pass를 원래 judge의 전체 정답성과 동일시하지 않는다.

## 라이선스 구분

[CodeNet 저자 논문 부록 A.6, p.17](https://jiechenjiechen.github.io/pub/codenet.pdf)은 **dataset: CDLA Permissive v2.0**, **도구 repository: Apache 2.0**로 구분한다. [IBM repository LICENSE](https://github.com/IBM/Project_CodeNet/blob/main/LICENSE)만 보고 제출 데이터까지 Apache로 표시하지 않는다. 재배포를 실행하기 전에는 확보한 배포본의 license/notice도 함께 보존·확인해야 한다. 현재는 로컬 연구 입력 검증만 수행하는 단계다.
