# Repository Instructions

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
