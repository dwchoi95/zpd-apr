# Repository Instructions

## User-requested experiment deadline (2026-10-21)

The user limited ZPD-APR improvement experiments to **2026-10-21 13:00 KST**.
Read `analysis_protocols/zpd-deadline-20261021.json` before any experimental
launch or automatic continuation. This newer instruction overrides older
"continue until improved" messages. Do not launch/retry/resume experiments at
or after that time. Before the deadline prioritize finishing the current
matched training and its fixed evaluation over opening unrelated branches.
Do not alter the active frozen release, datasets, gate, or reporting denominator.

At the deadline the scoped server timer stops still-running project experiment
services (coordinators first). Preserve their files, mark interrupted work as
incomplete, and never manufacture a normal-exit/COMPLETE certificate. Analysis,
verification and the final report remain authorized after the cutoff. Summarize
all improvements and negative results, distinguish incomparable cohorts, and
recommend the best supported method using the original correctness/regression/
unknown/C-H-HS-U gate. Report the highest observed RR separately if it fails the
gate; retain the incumbent if no candidate qualifies. No claim of educational
or confirmatory benefit. Only a newer explicit user instruction can extend this
deadline. Keep the deadline policy and final-report callback when registering
new families. Existing experiment source snapshots must remain unchanged.

## Independent FSE 2027 paper review

Every review of the paper must be performed by a newly spawned, independent
sub-agent. Never reuse a reviewer agent, and never let the agent that edited the
paper review its own work.

- Spawn the reviewer with no conversation history (`fork_turns="none"`).
- Give it the latest `paper/main.pdf`, not prior reviews, author rebuttals,
  desired scores, or descriptions of earlier changes.
- Include this exact request:

  `FSE 2027(https://conf.researchr.org/track/fse-2027/fse-2027-papers)에 제출할 논문인데 평가해줘.`

- Explicitly ask it to report an `Overall Merit` score and justification using
  the FSE 2027 criteria.
- Ask for the review in Korean and preserve the raw review without rewriting
  its score or criticism.
- Do not prompt the reviewer to reach a target score such as Accept. Paper
  improvement and paper review are separate turns handled by separate agents.
- Each subsequent review must use another new independent sub-agent, even when
  reviewing a revision of the same PDF.
