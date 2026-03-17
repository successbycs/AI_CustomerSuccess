# Definition Of Done

This document defines when the repository is considered done for internal launch and when an individual milestone is allowed to close.

## Project Done

The project is done only when all of the following are true:

- all milestones in `docs/implementation_plan.md` that define launch readiness are marked `complete`
- `scripts/verify_project.sh` passes from a clean local environment
- the pipeline can generate fresh directory and review artifacts from the current codebase
- public pages and admin/operator paths render from generated data without manual patching between steps
- persistence behavior is healthy enough that fallback artifacts are no longer masking schema drift
- docs accurately describe the runtime, config surfaces, serving model, and operational caveats
- no known launch blocker remains hidden behind a manual workaround

## Milestone Done

A milestone is done only when:

- its acceptance criteria are implemented
- relevant automated tests pass
- milestone verification commands succeed
- required runtime or manual checks have been completed
- review is recorded as pass
- QA is recorded as pass
- expected artifacts have been checked when the milestone produces or serves them
- affected docs are updated in the same cycle

## Not Done

A milestone is not done if any of the following are true:

- verification only proves code presence rather than runtime behavior
- tests are green but changed behavior is not actually covered
- manual checks are still pending
- fallback artifacts are hiding a broken persistence or runtime path
- milestone status and dependency state disagree
