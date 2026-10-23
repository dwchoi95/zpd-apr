# 참고 논문 분석 — Histra (APR for programming assignments)

[skeleton.md](skeleton.md)의 하위 문서. 사용자가 제공한 참고 논문을 **섹션 → 문단 → 문장** 단위로
뜯어 관례를 뽑았다. 기존 네 편(ICSE25·ICSE26·ASE26·FSE26)은 symbolic execution 논문이고, 이
논문은 **ZPDPatch와 같은 도메인·같은 문제 설정**이므로 서사 관례는 이 문서를 우선 따른다.
표기·플로트·분량 규격은 기존 문서를 따른다.

**분석 범위.** 원고 전문(645줄)을 받아 Title, Abstract, §1 Introduction, §2 Preliminaries,
§3 Our Approach, §4 Experiments, §5 Related Work, §6 Conclusion, Data Availability를 모두 분석했다.

---

## 0. 한 줄 요약 규칙

1. **결과는 baseline 대비 상대 범위로 쓴다.** "4.7--76.7\% more submissions", "11.7--35.2\% less
   of the skeleton", "9.4--16.6\% more of the code". 절대값만 쓰지 않고, 여러 baseline에 대한
   최소--최대를 한 범위로 묶는다.
2. **신조어는 정의하는 문장 안에서 쓰임을 함께 보인다.** 인용부호로 도입하고(``intent skeleton,''),
   바로 뒤에 동격절로 풀어 쓴다.
3. **모든 형식 정의 뒤에 `Intuitively, ...` 한 문장을 둔다.** display 수식 앞에는 `Formally, ...`.
4. **단계는 고유명사로 쓴다.** "the Sketch stage", "In the Repair stage". 소문자로 풀지 않는다.
5. **하이퍼파라미터는 `\eta` + 아래첨자**이고, 값은 알고리즘 주석(`\Comment{$\eta_k = 20$}`)과
   산문("where $\eta_k = 20$ in our experiments") 양쪽에 쓴다.
6. **알고리즘은 `\Procedure{Name}{args}`로 감싸고**, `\Require`/`\Ensure`는 **"명사 ($기호$)"**를
   쉼표로 나열하고 마침표로 닫는다. 실패 반환이 있으면 `\Ensure ..., or $\bot$ if none is found`.
7. **단계 블록 주석**은 `\Statex\hspace{\algorithmicindent}\textit{/* Stage k. Name */}`.
8. 선행 기법 대조는 **문단이 아니라 문장 안에서** 한다. `Unlike existing techniques, which ...,`
9. **지표별 결과 문장은 한 틀로 쓴다.** `In terms of <지표>, X <값(절대)>, that is, a\%, b\%, and c\%
   more than A (x\%), B (y\%), and C (z\%), respectively.` 감소면 `a relative reduction of ... from`,
   증가면 `a relative increase of ... over`. baseline 절대값을 **괄호에 함께** 적는다.
10. **문단은 `Overall, ...` 또는 `These results show that ...` 한 문장으로 닫는다.** 그 문장에는
   수치를 넣지 않고, 그 문단이 보인 것만 말한다.
11. **설계 선택의 정당화에 실험 수치를 앞당겨 인용한다.** `In fact, 63.0\% of the passing patches came
   from the hole-only phase (Section~\ref{sec:rq1}).`

---

## 1. 제목

`\tool{}: Guiding Program Repair for Programming Assignments with Students' Own Submission Histories`

- 틀: `<Tool>: <동명사구 = 기법이 하는 일> for <도메인> with <구별되는 입력>`
- 트레이드오프나 희생을 제목에 쓰지 않는다. **무엇으로 무엇을 하는가**만 쓴다.

## 2. Abstract — 8문장

| # | 역할 | 문형 |
|---|---|---|
| 1 | 제안 | `We present X, a <유형> technique that <한다> while <보존한다>.` 한 문장 |
| 2 | 도메인 성취 | `<분야> has substantially improved <지표> for <대상>.` |
| 3 | However + 기제 | `However, existing techniques frequently <문제>, the <신조어 풀이>, because <무엇이 결정하기 때문>.` |
| 4 | 측정된 격차 | `The passing patches of two state-of-the-art techniques change 2.7--3.2 times as much ... as students do.` |
| 5 | 난제 | `<X>ing is challenging because <이유 A> and <이유 B>.` |
| 6 | 작동 | 한 문장에 세 단계를 동사로 나열하고, 마지막에 물러섬과 되돌림을 붙인다 |
| 7 | 결과 | `Experimental results on <규모> show that X <상대 범위> while <상대 범위> and <상대 범위>.` |
| 8 | 사람 평가 | `In a blinded study, two instructors chose ... in 77.6\% of the pairs.` |

- 인용 없음, 한계 서술 없음, 마지막 문장이 결과다.
- `IEEEkeywords` 블록을 둔다.

## 3. Introduction — 5문단 + 3 bullets

### I1 Domain (3문장)

1. `<분야>~\cite{}은 <가치>로 널리 연구되어 왔다.`
2. **입출력 계약 + `i.e.,` 풀이 + 혜택**: `Given a buggy submission and the test suite, a technique
   automatically produces a patch, i.e., a modified program that passes every test, so that students
   can receive feedback on every failed attempt~\cite{}.`
3. **일반 파이프라인**: `To this end, the technique determines <어디>, synthesizes <무엇으로부터>,
   and returns to the student only a candidate that passes every test.`

비판 0개.

### I2 SOTA (5문장)

1. **열린 문제 2개**: `Repairing student programs poses two open problems: <A>, and <B>.`
2. **분류 축을 명시**: `Existing techniques fall into three groups by how they <축>.`
3--4. 범주명을 주어로 세우고 인용 묶음을 붙인다. 각 범주가 그 축에서 무엇을 하는지 한 절로.
5. **정성적 칭찬**: `These techniques have substantially raised the repair rate for student submissions.`

비판 0개. 범주는 **세 개**이고, 축이 I3의 공백과 같은 축이다.

### I3 Gap (8문장)

1. `However, existing techniques do not <무엇을 모른다>.`
2. 그 대신 무엇이 결정하는가 + "가까움을 선호하는 기법조차 모든 부분을 똑같이 다룬다"
3. **왜 중요한가 + 인용 2쌍**: 피드백 이론 + 학계가 이미 쓰는 품질 기준
4. 학습자에 대한 귀결 + 인용
5. **신조어 정의 2개**: `In this work, we define the \emph{A} of ... as ..., and the \emph{B} of ...
   as the fraction of ... that ...`
6. **측정된 대조 + 배수 + 절 참조**: `More than half (61.3\%) ... whereas 70.0\% and 73.7\% ...,
   and they change 2.7 to 3.2 times as much of it as the students do (Section~\ref{}).`
7. (6에 포함)
8. **근본 원인 + 귀결**: `Without the history of the student being helped, these techniques may give
   the student a program shaped by someone else's solution rather than feedback on their own attempt.`

### I4+I6 Proposal (8문장)

1. `In this paper, we present X, a <유형> technique that <한다> while <보존한다>.` **짧게(24 words)**
2. `Our key idea is that <데이터에 대한 주장>: <살아남은 것은 A일 가능성이 높고, 바뀌는 것은 B일
   가능성이 높다>.` 콜론으로 풀이를 붙인다
3. **난제 + Preliminaries 참조 + 설계 응답**: `Because this signal is coarse (Section~\ref{}),
   X focuses ... but treats it as a preference rather than a constraint.`
4--6. **단계별 한 문장씩**: `In the <Stage> stage, X <한다>.` 각 단계 안에 필요하면
   `Unlike the holes of existing techniques, which come from ..., these holes mark ...`로 대조
7. (단계 설명에 포함)
8. `As a result, the patches tend to <성질>.`

- **단계 수를 따로 선언하지 않는다.** 단계 이름을 가진 문장을 차례로 쓰는 것으로 대신한다.
  (Preliminaries형 "operates in three stages"는 §3.1 Overview에서 쓴다.)

### I7 Results (7문장)

1. **헤드라인 최상급**: `Experimental results demonstrate that X <가장 많이> while <가장 적게>.`
2. **설정 + baseline을 계열명과 실명으로**: `We evaluated X on <규모> against state-of-the-art
   techniques of the three groups: A~\cite{}, B~\cite{}, and C~\cite{}.`
3. **주 지표**: `X fixed 96.5\% ..., 4.7--76.7\% more than the baselines.`
4. **부 지표 2개**: `Its passing patches changed only 18.7\% ..., 11.7--35.2\% less than those of the
   baselines, and left ... 42.0--149.7\% more often.`
5. **ablation**: `Without the history and with holes from FL instead of the history, the skeleton loss
   increased by 32.1\% and 11.6\%, respectively.`
6. **공정 조건 명시**: `On the trajectories that all techniques fixed, ...`
7. **사람 평가 + 절 참조**

- 강조 부사 없음. 크기는 전부 **상대 범위**가 말한다.

### I8 Contributions — 3 bullets

| bullet | 라벨 | 내용 |
|---|---|---|
| 1 | `Observation:` | `We show that <관찰>, motivating the need for <논문이 하는 일>.` 한 문장 |
| 2 | `New technique:` | `We present X, a <유형> technique for <도메인>. Our core technical contribution is <알고리즘 한 문장>.` |
| 3 | `Evaluation:` | `We demonstrate the effectiveness of X by comparing it with <baseline>과 <통제군> on <규모>: <결과 두 절>.` |

- 도입: `\textbf{Contributions.} We summarize our contributions below:`
- 라벨 뒤는 **콜론**, 라벨은 굵게.

## 4. Preliminaries — 2 하위절

### §2.1 `Automated Program Repair for Programming Assignments` (3문단)

- **D**: 선행 목표 + 흔한 수단(`often by using \emph{reference programs}, i.e., ...`) →
  `We define the \emph{submission trajectory} ... as a sequence ...` → 누출 선언을 정의의 관계절로
  (`which serves only as ground truth for evaluation and is never given to a technique`) →
  버기 프로그램·이력 프로그램 명명.
- **Algorithm 1** (일반 알고리즘) → **W**: `It takes <명사 ($기호$)> as input, and returns <...>.`
  뒤에 `At line~2, ... At line~3, the function $\mathsf{Sketch}$ returns a \emph{sketch}~\cite{} ...
  As soon as ... (lines~5--6); if no ..., it returns $\bot$ (line~7).`
  **함수를 이름으로 부르고**, 외부 개념에는 인용을 붙인다.
- **M**: `Existing techniques fall into three groups by how they decide, at line~3, which parts of $b$
  to repair.` → 범주마다 **어느 줄을 무엇으로 대체하는지** + 도구 실명 + 인용 →
  `In all cases, which parts of $b$ to repair is decided by ...; the student's history is not used.`

### §2.2 `Limitation of History-Agnostic Repair` (5문단)

- **O**: `Our key observation is that <관찰>.` → `To quantify this, we formalize <신조어> introduced
  in Section~\ref{sec:intro}.` → 정규화·정렬·stable 정의 → `Formally, ...` + display 수식 →
  `where ... denotes ...` → 지표 정의(`We measure ... by its \emph{skeleton loss}, our main metric:
  the fraction of ...`) → `We call a patch with no skeleton loss an \emph{intact patch}.`
- **T**: 그림/표 + `Figure~\ref{} shows how much ... by difficulty ...` → 학생 기준선과 도구 비교를
  **배수로** → 난이도별 추세 → **타당성 점검**(`Moreover, in their own fixes the students changed only
  9.8\% of the skeleton nodes but 18.8\% of the other nodes, which shows that ...`)
- **N**: `Minimizing the repair alone does not solve this problem.` → **선행 기법이 이미 그것을
  시도한다는 근거를 인용으로** → `Nevertheless, their passing patches changed ...` → 왜 안 되는가
- **G**: `These limitations motivate our approach.` → `Our goal is to repair $b$ ... by deriving ...`
  → `However, the history marks where to repair only coarsely:` + 수치 → `Moreover, ...` →
  `Our work thus tackles two key challenges: (1) ..., and (2) ...`

## 5. Our Approach — Overview + 도구명 하위절 + 단계별 하위절

- **Figure(overview)가 §3 맨 앞**, 그 다음 §3.1 Overview.
- §3.1 1문단: `Figure~\ref{} illustrates how X <한다>.` → `X takes the inputs of Algorithm~\ref{},
  namely ..., together with <추가 입력>.` → `X processes these inputs in three stages: A, B, and C.`
  → 단계마다 한 문장 + `(Section~\ref{})` → 실패 반환.
- §3.1 2문단: `X differs from existing techniques in <두 축>. First, ... Second, ...` 각 축에서
  선행 기법이 무엇을 하는지 인용과 함께 대조.
- §3.2는 **하위절 제목이 도구명**이고 Algorithm 2를 싣는다. 첫 문단: `Algorithm~\ref{alg:tool}
  details how X instantiates Algorithm~\ref{alg:generic}.` → 입력 차이 → 줄 번호 해설.
- **불변 성질 문단**을 둔다: `This validation order affects only which passing patch X returns, not
  whether it finds one, because ... Hence, given deterministic test outcomes, the history does not
  lower the repair rate.`
- 단계 하위절은 `The goal of the <Stage> stage is to ... (lines~a--b).`로 열고, 설계 선택마다
  `We require ... because ...`로 이유를 붙여 닫는다.


### §3.4--§3.5 단계 하위절 (Search, Repair)

- 하위절은 **한 문장으로 열고 담당 줄 번호를 괄호에** 넣는다. `The goal of the Search stage is to
  retrieve, from the reference programs, those that are likely to merge well into $b$ (line~5).`
  여러 줄이면 `(lines~6--13).`
- 여러 부분으로 쪼개지는 단계는 **열기 문장 바로 뒤에 부분 목록**을 둔다. `It has three parts:
  merging ..., validating ..., and minimizing ....` 그리고 각 부분을 **bold run-in 라벨**로 쓴다.
  `\textbf{Merge.}`, `\textbf{Hole-only merge.}`, `\textbf{Skeleton-aware ordering.}`,
  `\textbf{Minimization.}`
- 보조 함수는 산문에서도 **기호로 호출 형태까지** 쓴다. `$\mathsf{Merge}(b^{\square}, r, m, o)$
  first matches the nodes of the two programs ...`
- 외부 알고리즘을 쓰면 **그 자리에서 인용**하고 자기 변형임을 밝힌다. `in a manner inspired by
  GumTree~\cite{falleri2014fine}`, `with the Needleman--Wunsch algorithm~\cite{needleman1970general}`.
- display 수식은 `where <기호> is <명사>`로 해설하고, 바로 뒤에 직관 문장을 붙인다. `Thus, features
  that most reference programs share, such as reading the input, contribute little, whereas rare
  features that $b$ shares with $r$ contribute much.`
- **설계 선택마다 `because` 절로 이유**를 붙인다. `The features describe what a program does rather
  than how its variables are named, because students name their variables differently and the merge
  renames them to the student's anyway.`
- 단계 안에서 **실패·대안 경로를 미리 처리**한다. `However, no hole-only patch exists when ... \tool{}
  therefore also merges each retrieved program without frozen nodes ... and validates these free
  candidates only after every hole-only candidate has failed.`
- 하이퍼파라미터는 문장 끝에 설정 근거를 붙여 닫는다. `, which we set to 20 by trial and error.`

---

## 6. Experiments — 도입 + Settings + RQ 하위절 + Discussion + Threats

### §4 도입 (3요소, 문단 없음)

1. `In this section, we evaluate \tool{} to answer the following research questions:`
2. `itemize`로 **RQ 네 개**, 각각 한 문장 의문문. 축은 **효과성 → 학생 자신의 수정과의 근접성 →
   기여 분해(ablation) → 사람 평가**.
   - `RQ1: How effectively does \tool{} repair buggy submissions?`
   - `RQ2: To what extent do the patches of \tool{} resemble the fixes that students make ...?`
   - `RQ3: How do the student's history and each design choice of \tool{} contribute to ...?`
   - `RQ4: Which feedback do instructors prefer?`
3. **하드웨어 한 문장.** `All experiments were conducted on a server running Ubuntu 22.04, equipped
   with two Intel Xeon Silver 4510 processors (24 cores), 439 GB of RAM, and an NVIDIA H100 NVL GPU.`

구현 문단·도구 버전 문단을 따로 두지 않는다.

### §4.1 Experimental Settings — bold run-in 3개

**`\textbf{Baselines.}`**

1. `We selected one state-of-the-art technique from each group of Section~\ref{sec:prelim-repair} as a
   baseline: A~\cite{}, B~\cite{}, and C~\cite{}.` — **§2.1의 범주 축을 그대로 재사용**한다.
2. baseline마다 **한 문장**으로 무엇을 어떻게 하는지. 범주 설명을 반복하지 않고 그 도구의 동작만.
3. LLM이 끼면 **모델 선택 근거**까지 한 문장. `As the LLM, we used GPT-4o~\cite{}, which performed
   best in the evaluation of LSGen among the models still available.`

**`\textbf{Benchmarks.}`**

1. **규모가 첫 문장**: `We used the 1,764 submission trajectories (8,696 submissions) of the 14
   AtCoder problems in Table~\ref{tab:bench}.`
2. 출처와 테스트 수트 출처를 인용으로. `We built the benchmark from the Python submissions of Project
   CodeNet~\cite{}, whose AtCoder problems come with the test suites of FixEval~\cite{}.`
3. **포함 기준을 번호로 셋**: `we collected the trajectories that satisfy three criteria: (1) ...;
   (2) the test suite reproduces every verdict in the trajectory; and (3) each problem has at least
   100 such trajectories.`
4. 표 열을 **괄호 약어로 선언**: `lists, for each problem, the concept it mainly exercises, its number
   of trajectories (\#Traj), ... and the average number of non-blank lines (Avg LOC).`
5. 도메인 적합성 한 문장: `The problems exercise concepts of introductory programming, such as edge
   cases, floating-point precision, and prefix sums.`
6. **누출 통제를 마지막 문장**: `For each trajectory, the reference programs ($R$) are the final
   accepted submissions of the other trajectories of the same problem (100--173 programs); the
   student's own accepted submission is used only for evaluation.`

**`\textbf{Evaluation Metrics.}`**

- `We measured effectiveness with three metrics.`로 개수를 먼저 선언한다.
- 지표마다 `The <지표> is the fraction of ...` 한 절, **집계 방식**을 같은 문장에 붙인다
  (`is measured for each passing patch and averaged over the passing patches`).
- **사람 기준선을 지표로 함께 선언**한다. `As a reference point, we also measured both skeleton
  metrics for the students' own accepted submissions (Student).`

표(`tab:bench`)는 난이도 그룹별로 행을 묶고, 헤더 아래 `\midrule\midrule`을 쓴다.

### RQ 하위절의 문단 배열

| 문단 | 역할 | 문형 |
|---|---|---|
| 1 | 목적 + 방법 (2문장) | `RQ1 examines whether \tool{}, which <우리 설계>, <주장>. To this end, we compared <지표들> of \tool{} and the baselines on <범위>.` |
| 2 | 표 읽기 + 지표별 결과 + `Overall,` | 표/그림 → `Table~\ref{} shows, for each ..., the A (Fixed), B (Loss), and C (Intact) of each technique, together with ...; ``--'' denotes no passing patch, and bold marks the best value among the techniques.` → `In terms of <지표>, ...` 한 문장씩 → `Overall, ...` |
| 3 | 하위군 분해 | 유리한 구간 → 중간 → `In contrast,` 불리한 구간. 끝에 `we examine the cause below`로 다음 문단에 넘긴다 |
| 4 | 왜 baseline이 그렇게 행동하는가 | baseline을 하나씩 주어로 → `Thus, although the baselines changed the skeleton in different ways, the cause is the same: <한 문장>.` |
| 5 | **자기비판 + 해소** | `Nevertheless, \tool{} still <우리가 못한 점>, and this gap was concentrated in <어디>.` → 하위군 수치로 분해 → 왜 불가피한가 → `These results show that ...` |

- 표 안의 기호를 **본문에서 선언**한다(``--'' = 통과 패치 없음, 굵게 = 기법 중 최고값).
- 불리한 결과를 **숨기지 않고 같은 문단에서 수치로** 말한다. `but changed 45.4\% of the skeleton,
  7.7\% more than LSGen, and only 3.8\% of its passing patches were intact patches`.

### RQ2형 — 주 지표가 자기 정의일 때

- 첫 문단에 **왜 다른 지표를 쓰는지** 밝힌다. `Because the skeleton loss is measured with the skeleton
  that \tool{} itself uses, here we measured three metrics based on the student's own accepted
  submission $P_{\mathit{ac}}$, independently of the skeleton.`
- 지표 세 개를 **세미콜론으로 한 문장에** 정의한다. `Kept is the share of ...; Ident is the share of
  ...; and Dist is the value-aware tree edit distance between the patch and $P_{\mathit{ac}}$.`
- 공정 조건을 그림 설명과 캡션 양쪽에 쓴다. `on the trajectories that all techniques fixed`.
- 두 번째 문단은 **원인 두 개**: `Two reasons explain why ...: First, ... Second, ...` 두 번째 원인은
  하위군을 나눠(`On the 391 trajectories in which ...`, `On the 267 trajectories in which ...`)
  **유리한 하위군과 불리한 하위군을 같이** 보고한다.

### RQ3형 — Ablation

- 변형군과 통제군을 **이름으로 구분**한다. 설계 선택 제거는 `\tool{}$-$Name`(Norm, Hole, Kept, Min),
  대체·통제는 `\tool{}$_{\mathit{name}}$`($\emptyset$, rand, frac, FL, size).
- 변형 정의마다 **알고리즘 줄 번호**를 괄호로 붙인다. `\tool{}$-$Min returns the first passing
  candidate without minimization (line~12)`.
- 통제군은 **신호의 출처만 바꾼** 것들로 설계한다. 없음($\emptyset$) / 같은 분량만 맞춘 무작위(frac) /
  개수·종류·크기를 유지하고 위치만 무작위(rand) / 다른 기법의 신호(FL). 무작위는 **세 번 뽑아 평균**.
- 표는 `\multicolumn{4}{l}{\textit{Design choice removed or replaced}}` /
  `\multicolumn{4}{l}{\textit{Source of holes}}` 소제목 행으로 두 묶음을 나누고, 값에 상대 변화를
  괄호로 병기한다(`21.8 ($+$16.6\%)`), 캡션에 `with the relative change from \tool{} in parentheses`.
- **먼저 변하지 않은 지표를 치운다.** `Since all configurations repaired 96.1 to 96.5\% of the
  submissions, the differences appeared in how much of the skeleton the patches kept.`
- 효과가 **없는** 변형도 보고하고 **왜 없는지** 설명한다. `within the validation budget, both orders
  mostly reach the same patch, and because students rarely switch between equivalent forms across
  consecutive submissions, normalization changed the skeleton of only 14.8\% of the trajectories.`
- 통제군 문단은 **신호가 무엇으로 기여하는지**로 해석을 닫는다. `The history thus contributes mainly by
  deciding how many holes of which sizes each program needs: ... and placing them where the history
  indicates adds a small but consistent gain on top.`

### RQ4형 — 사람 평가 (쓸 수 있으면)

- 평가자 자격: 저자가 아님, 교육 경력 연수, 현재 담당 과목.
- 비교 대상을 **같은 파이프라인의 통제군**으로 골라 blinding 성립 근거를 쓴다. `since both come from
  the same pipeline and all programs were shown in the same normalized format, the instructors could
  not tell the source of a patch.`
- 표본: 포함 조건 → **문제별 n개, 고정 시드** → `so that no problem dominates the sample`.
- 질문은 **정보를 나누어 두 단계**로. 먼저 이력 없이 P-Feedback, 이력을 보인 뒤 P-Intent.
- 결과 문단: 종합 비율 → **평가자별 비율 괄호** → 유의성(`exact sign test, $p < 0.001$`) →
  일치도(`a linear weighted $\kappa$ of 0.70 ... (90\% raw agreement)`) → `Overall, ...`
- 마지막 문단에서 **사람 선호와 우리 지표의 상관**을 그림으로 보인다(막대=쌍 수, 선=선택 비율).

### §4.6 Discussion — bold run-in 2개

- `\textbf{Implications for instructors.}` `Our results suggest three ways to use ... .` →
  `First, ... (Section~\ref{})`, `Second, ...`, `Third, ...` — **모든 권고에 절 참조**를 붙인다.
- `\textbf{Delivering patches.}` 전달 형태 나열 → 인용으로 뒷받침 → 미해결을 `Which form of delivery
  helps learning most remains to be studied with students.`로 닫는다. **교육 효과를 주장하지 않는다.**

### §4.7 Threats to Validity — 한 문단

- 위협 → `However,` 반박 → 반박을 **수치나 설계 사실로** 뒷받침, 두 위협을 한 문단에 잇는다.
- 외부 타당성: `Our benchmark consists of ... and may not represent course assignments or other
  languages. However, the problems exercise concepts of introductory programming (Table~\ref{}), and
  we chose Python because the released implementations of all baselines target Python.` → 포팅 비용을
  한 문장으로(`porting \tool{} to another language requires only a parser and normalization rules`).
- 적용 범위: 포함 기준이 배제한 모집단을 밝히고, **그 모집단에서 기법이 어떻게 되는지**를 이미 돌린
  통제군으로 답한다. `For such a student, \tool{} runs without the history, which is the setting of
  \tool{}$_{\emptyset}$ in RQ3; even in this setting, \tool{} fixed more buggy submissions than every
  baseline (Section~\ref{}).` → 가장 불리한 하위군 수치(`34.3\% of the trajectories`)로 닫는다.

---

## 7. Related Work — bold run-in 2개

- **첫 번째는 §2.1의 범주를 이어받는다.** `\textbf{APR for Programming Assignments.} Beyond the
  techniques described in Section~\ref{sec:prelim-repair}, many techniques automatically repair
  student submissions.` → `Among alignment-based techniques, ...`, `As a localization-based
  technique, ...`, `Among knowledge-based techniques, ...` — §2.1과 **같은 범주명**을 쓴다.
- **baseline 선정과 제외를 한 문장에 세미콜론으로 나열**한다. `We excluded CLARA, which repaired fewer
  submissions than Refactory~\cite{}; Sarfgen and Qlose, whose implementations are not publicly
  available; Verifix and CEGIS, which handle only C programs; AutoGrader, which requires an
  instructor-written error model; and Refazer, whose parser does not support our benchmark.`
  — 제외 사유를 도구마다 하나씩 붙이고, 빠진 비교는 RQ로 대체했음을 밝힌다.
- **두 번째는 논문의 구별되는 입력**을 축으로 잡는다. `\textbf{Feedback on the Student's Own Work.}`
  이력을 쓰는 계열 → 그중 **남의 이력을 쓰는 것과 자기 이력을 쓰는 것을 구분** → 교육 효과 연구
  (긍정과 우려를 함께) → 최근의 유사 기준 연구와 그 한계(`but its distance-based objectives charge
  every part of the program alike`) → `In contrast, \tool{} ...` → `To our knowledge, \tool{} is the
  first repair technique that infers the intent to preserve from the student's own submission history.`

---

## 8. Conclusion (6문장) + Data Availability

1. 도메인 성취: `Automated Program Repair has substantially improved the repair rate for buggy student
   submissions.`
2. `However, existing techniques <한계>, <신조어 풀이>.`
3. `This paper aims to <목표>.`
4. `To this end, \tool{} <동사1>, <동사2>, and <동사3>.` — 단계 이름이 아니라 **동작**으로 쓴다.
5. `Experimental results demonstrate that \tool{} <주 결과> while <부 결과>, and that <사람 평가>.`
6. `We hope that \tool{} helps students receive feedback on their own attempts rather than on the
   solutions of others.`

- 수치를 쓰지 않는다. 인용을 쓰지 않는다. 한계·향후 과제를 쓰지 않는다.
- `\section*{Data Availability}` 한 문장: 도구·벤치마크·실험 데이터를 익명 저장소 URL로.

---

## 9. ZPDPatch 점검 체크리스트

| # | 항목 | 확인 |
|---|---|---|
| 1 | 결과를 baseline 대비 상대 범위(`oo--oo\% more/less`)로 쓰는가 | |
| 2 | 신조어를 인용부호 + 동격절로 도입하는가 | |
| 3 | display 수식 앞 `Formally,`, 뒤 `Intuitively,`가 있는가 | |
| 4 | 단계를 고유명사(`the Mine stage`)로 쓰는가 | |
| 5 | 하이퍼파라미터가 `\eta` + 아래첨자이고 값이 알고리즘 주석과 산문 양쪽에 있는가 | |
| 6 | 알고리즘이 `\Procedure`로 감싸이고 `\Require`가 "명사 ($기호$)" 형태인가 | |
| 7 | 실패 반환이 `$\bot$`로 명시되는가 | |
| 8 | I2가 열린 문제 2개 + 분류 축 + 세 범주 + 칭찬인가 | |
| 9 | I3가 신조어 정의 + 배수 대조 + 근본 원인·귀결로 닫는가 | |
| 10 | I7이 헤드라인 + baseline 실명 + 주/부 지표 + ablation + 공정 조건인가 | |
| 11 | §2.2가 O + 형식 정의 + T + N(선행이 이미 시도) + G(난제 2개)인가 | |
| 12 | §3.1이 `processes these inputs in three stages` + 단계별 한 문장 + 차별점 2축인가 | |
| 13 | 불변 성질 문단이 있는가 | |
| 14 | 단계 하위절이 `The goal of the <Stage> stage is to ... (lines~a--b).`로 열리는가 | |
| 15 | 단계 안의 부분이 bold run-in 라벨(`\textbf{Merge.}`)로 나뉘는가 | |
| 16 | §4 도입이 RQ 네 개 + 하드웨어 한 문장인가 | |
| 17 | Settings가 Baselines / Benchmarks / Evaluation Metrics bold run-in 셋인가 | |
| 18 | Benchmarks가 규모 → 출처 → 번호 매긴 포함 기준 → 열 약어 → 누출 통제 순인가 | |
| 19 | 지표 선언에 사람 기준선(Student)이 포함되는가 | |
| 20 | RQ 문단이 목적·방법 → 표 읽기+지표별 → 하위군 분해 → 원인 → 자기비판 순인가 | |
| 21 | ablation이 설계 변형군과 신호 출처 통제군으로 나뉘고 줄 번호가 붙는가 | |
| 22 | 효과 없는 변형도 보고하고 왜 없는지 설명하는가 | |
| 23 | Threats가 위협마다 수치·설계 사실로 반박하는가 | |
| 24 | Related Work가 §2.1의 범주명을 재사용하고 제외 사유를 도구별로 밝히는가 | |
| 25 | Conclusion이 수치·인용 없이 6문장이고 교육 효과를 주장하지 않는가 | |
