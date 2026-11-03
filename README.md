# ZPDPatch

## Dataset

output.tar.xz : the results the paper reports; unpacks into `output/` (README.md inside describes every file and field)

```text
|-output
    |-benchmark      # inputs, the students' own steps, corpus counts (no source code)
    |-approaches     # ZPDPatch, the existing techniques, and the base model on the 1,753 RQ1 inputs
    |-differential   # every plausible RQ1 patch on generated inputs
    |-selection      # the nine checkpoints on the validation inputs
    |-targets        # Answer, Strict, and Progress targets (Seen, Unseen, Java)
    |-ablation       # each variant and the configuration it is compared with
    |-generality     # the 1.5B model and Java
    |-models         # the trained adapters (in the repository, not in the archive)
```

output/models : the adapters of base model `Qwen/Qwen2.5-Coder-7B-Instruct` (revision
`c03e6d358207e414f1eca0bb1891e29f1db0e242`)

```text
|-output/models
    |-{answer,strict,progress}-{2027,2028,2029}   # the nine checkpoints of Train, on the Seen training trajectories
    |-rq1/answer-{2027,2028,2029}                 # the cascade run on the RQ1 benchmark, trained without its students
    |-SHA256SUMS
```

> The nine checkpoints are those Select ran on `output/selection` and the Seen and Unseen results use. `rq1/` holds the
> Answer checkpoints trained without the RQ1 students, run in this order by Algorithm 1 for RQ1 and RQ2. Each adapter's
> weights are split into parts below GitHub's file size limit; join and check them before use (Setup).
>
> Student programs are not redistributed. `run.py build-data` rebuilds the data from Project CodeNet (Python, with the
> test cases AtCoder released) and the TIKTOC release of CodeWorkout (Java).

## Setup

1. Python >= 3.11 (tested with 3.13) on Linux with a CUDA GPU for training and generation; judging runs on CPU, and Java
   judging in Docker.
2. Install the packages at the versions of the paper's runs; `generate-greedy` and `generate-samples` run vLLM, which
   pins its own torch, so they need a second environment:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-vllm.txt   # in a separate environment, for the two vLLM commands
   ```
3. Unpack the results and join the adapters:
   ```bash
   tar -xJf output.tar.xz
   cd output/models
   for d in $(awk '{print $2}' SHA256SUMS | xargs -n1 dirname); do cat $d/adapter_model.safetensors.part-* > $d/adapter_model.safetensors; done
   sha256sum -c SHA256SUMS && cd ../..
   ```
4. For Java only, build the judge image (building the Java data also needs `bwrap`):
   ```bash
   docker build -t zpdpatch-java:21 docker/java
   ```

## How to Run

+ Build the data (Project CodeNet for Python, the TIKTOC release for Java):
  ```bash
  python run.py build-data --benchmark rq1 --source-root <Project_CodeNet> --output-root data-rq1
  python run.py build-data --benchmark seen-unseen --source-root <Project_CodeNet> --output-root data
  python run.py build-data --benchmark codeworkout --source-root <TIKTOC> --output-root data-java --base-model Qwen/Qwen2.5-Coder-7B-Instruct
  ```
  `data-java/` then holds the Java datasets (`datasets/`, `problem-holdout/datasets/`, `paired-java-control/`) and test cases.
+ Execute every submission once, then mine the training pairs of each target rule (Mine); repeat with `seen_valid` for
  the validation datasets:
  ```bash
  python run.py build-outcome-cache --data-root data --split seen_train --output outcomes/seen_train.jsonl
  python run.py build-repair-data --data-root data --split seen_train --target-mode answer --output datasets/train-answer.jsonl
  python run.py build-repair-data --data-root data --split seen_train --target-mode strict --output datasets/train-strict.jsonl
  python run.py build-repair-data --data-root data --split seen_train --target-mode progress --outcome-cache outcomes/seen_train.jsonl --output datasets/train-progress.jsonl
  python run.py make-current-code-only datasets/train-answer.jsonl datasets/train-answer.current-only.jsonl
  ```
  For RQ1, drop the benchmark's students from training first:
  ```bash
  python run.py hold-out-students data-rq1/splits/test.jsonl datasets/train-answer.jsonl datasets/train-answer.rq1.jsonl
  ```
+ Build the test inputs: each trajectory's last wrong submission that still fails locally, with the student's accepted
  program (`--data-root data-rq1 --split test` for RQ1, `seen_test` and `unseen_test` for Seen and Unseen, `seen_valid`
  for the validation inputs):
  ```bash
  python run.py build-outcome-cache --data-root data-rq1 --split test --output outcomes/rq1-test.jsonl
  python run.py build-repair-data --data-root data-rq1 --split test --target-mode final-accepted --outcome-cache outcomes/rq1-test.jsonl --output datasets/rq1-test.raw.jsonl
  python run.py filter-rq1-data datasets/rq1-test.raw.jsonl outcomes/rq1-test.jsonl datasets/rq1-test.jsonl
  python run.py make-current-code-only datasets/rq1-test.jsonl datasets/rq1-test.current-only.jsonl
  ```
+ Train one adapter per rule and seed (Train):
  ```bash
  python run.py train-qlora datasets/train-answer.current-only.jsonl checkpoints/answer-2027 --prompt D \
    --validation-dataset datasets/valid-answer.current-only.jsonl --seed 2027
  ```
+ Run every checkpoint on one validation input per problem and choose the cascade (Select):
  ```bash
  python run.py sample-validation datasets/seen-valid.jsonl datasets/validation.jsonl --seed 2027
  python run.py make-current-code-only datasets/validation.jsonl datasets/validation.current-only.jsonl
  python run.py generate datasets/validation.current-only.jsonl val/Answer2027.generations.jsonl --method Answer2027 --prompt D \
    --adapter checkpoints/answer-2027 --max-new-tokens 4096
  python run.py evaluate datasets/validation.current-only.jsonl val/Answer2027.generations.jsonl val/Answer2027.evaluation.jsonl --data-root data
  python run.py select --evaluation Answer2027:Answer=val/Answer2027.evaluation.jsonl ... --output selection.json
  ```
+ Repair the test inputs with each member (`--adapter output/models/rq1/answer-2027` uses a released adapter) and run
  them as a cascade (Algorithm 1):
  ```bash
  python run.py compose datasets/rq1-test.current-only.jsonl zpdpatch.evaluation.jsonl --forward-fallback \
    --stage Answer2027=eval/Answer2027.evaluation.jsonl --stage Answer2028=eval/Answer2028.evaluation.jsonl \
    --stage Answer2029=eval/Answer2029.evaluation.jsonl
  ```
+ Judge an existing technique's returns with the same runner:
  ```bash
  python run.py evaluate datasets/rq1-test.current-only.jsonl <technique>.generations.jsonl <technique>.evaluation.jsonl --data-root data-rq1
  ```
+ Draw candidates from the base model or from one adapter at temperature 0.8 (RQ2's base model, RQ3's training and
  distinct-checkpoint variants), then evaluate each sample and compose them like the cascade:
  ```bash
  python run.py generate-samples datasets/rq1-test.current-only.jsonl base/ --base-model Qwen/Qwen2.5-Coder-7B-Instruct \
    --method-prefix Base --sampling-seed 4101 --sampling-seed 4102 --sampling-seed 4103
  python run.py generate-greedy datasets/seen-test.current-only.jsonl greedy/ --base-model Qwen/Qwen2.5-Coder-7B-Instruct \
    --adapter Answer2027=output/models/answer-2027 --adapter Answer2028=output/models/answer-2028
  ```
+ Isolate the target rule and the target source (RQ3, RQ4), then train, repair, and compose as above:
  ```bash
  python run.py paired-control datasets/train-progress.jsonl datasets/train-answer.jsonl paired/train-progress.jsonl paired/train-answer.jsonl --summary paired/train.json
  python run.py paired-strict paired/train-answer.jsonl datasets/train-answer.jsonl datasets/train-strict.jsonl paired/train-strict.jsonl --summary paired/strict.json
  python run.py cross-user-control datasets/train-progress.jsonl shards/same-0.jsonl shards/cross-0.jsonl --summary shards/summary-0.json --maximum-target-reuse 3
  python run.py finalize-cross-user shards/ source/train-same-user.jsonl source/train-cross-user.jsonl --base-model Qwen/Qwen2.5-Coder-7B-Instruct \
    --prompt D --maximum-tokens 4096 --summary source/train.json
  ```
+ Judge Java returns in the judge image:
  ```bash
  python run.py java-prepare data-java/datasets/test-final.jsonl java.generations.jsonl data-java/tests/test_cases-1-26-24.csv data-java/tests/test_case_37.csv harness/sources
  python run.py java-judge harness/sources harness/status
  python run.py java-collect harness/manifest.jsonl harness/status java.evaluation.jsonl --summary java.summary.json
  ```
+ Run every plausible patch on generated inputs, against the majority output of the students' accepted programs:
  ```bash
  export ZPD_DIFF_DATA=data-rq1 ZPD_DIFF_TEST=datasets/rq1-test.jsonl ZPD_DIFF_OUT=differential
  python run.py differential-check
  for step in validate inputs references patches summarize; do python run.py differential $step; done
  python run.py differential patches --set targets && python run.py differential-own
  ```

## Command Line Arguments

| Command | What it does |
| --- | --- |
| `build-data` | builds a data root (`--benchmark rq1`, `seen-unseen`, `codeworkout`) from `--source-root` |
| `build-outcome-cache` | executes every submission of a split once and stores its per-test outcomes |
| `build-repair-data` | pairs each buggy submission with its target (`--target-mode answer`, `strict`, `progress`, `final-accepted`) |
| `make-current-code-only` | keeps only the current submission in each prompt |
| `filter-rq1-data` | keeps the inputs whose buggy program fails and whose accepted program passes locally |
| `train-qlora` | fine-tunes one QLoRA adapter (`--base-model`, `--seed`, `--epochs`, `--learning-rate`, ...) |
| `generate` | generates one repair per input with a base model and an optional `--adapter` |
| `evaluate` | judges returned programs on the test suite and computes TED and retention |
| `hold-out-students` | drops the RQ1 benchmark's students from a training dataset |
| `sample-validation` | draws one validation input per problem for Select |
| `select` | chooses the cascade from the checkpoints' validation evaluations |
| `compose` | runs evaluated checkpoints as a cascade (`--forward-fallback`: Algorithm 1's forward step; `--max-ted`: a step budget) |
| `normalize-baseline` | takes the submission's verdict and pass rate from a reference evaluation |
| `generate-greedy`, `generate-samples` | generate with vLLM: greedily for several adapters, or sampled from one model |
| `paired-control`, `paired-strict` | build the target-rule control: the same examples with Answer, Progress, and Strict targets |
| `cross-user-control`, `finalize-cross-user` | build the target-source control: another student's submission as the target |
| `java-prepare`, `java-judge`, `java-collect` | judge Java returns in the judge image |
| `differential`, `differential-check`, `differential-own` | run plausible patches on generated inputs and compare with the student's accepted program |
| `sampled-ted` | TED of the repaired returns of the sampled ablation variants |
| `codenet-attempts` | attempts to acceptance and verdict changes on every AtCoder problem of Project CodeNet |

`python run.py <command> --help` lists each command's arguments.

## Project Structure

```text
zpdpatch/
├── output.tar.xz              # Results reported in the paper; unpacks into output/
├── output/models/             # Trained adapters, weights split into parts
├── docker/java/Dockerfile     # Java 21 judge image
├── src/
│   ├── cli.py                 # The run.py commands
│   ├── core/                  # The technique: Mine (dataset, outcomes), Train (train), generation and judging
│   │   ├── prompts/           # Prompt templates
│   │   └── runner/            # Sandboxed execution of Python submissions
│   └── experiments/           # Data builders, Select and the cascade, controls, Java judging
│       ├── codenet/           # Project CodeNet data (RQ1 benchmark, Seen/Unseen corpus)
│       └── differential/      # Input generators and differential testing
├── run.py                     # Main entry point
├── requirements.txt           # Packages at the versions of the paper's runs
├── requirements-vllm.txt      # The environment of the two vLLM commands
├── README.md
└── LICENSE
```
