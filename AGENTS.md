# AGENTS.md

This file defines repo-specific working rules for AI coding agents working in this project.

The goal is not just to make the code work. The goal is to keep the project understandable, documented, and maintainable for a human developer.

## Core Rules

### 1. Keep the README in sync

If you add, remove, rename, deactivate, or significantly change any of these:
- endpoint
- API contract
- scoring logic
- role/profile behavior
- project structure
- active module
- config behavior
- important workflow

Then you must update `README.md` in the same task.

README maintenance is part of done.
It is not optional cleanup.

### 2. Record mismatches, mistakes, and logic problems

If during the task you find:
- a mismatch between docs and code
- a mismatch between frontend contract and backend contract
- a logic issue
- an assumption that may be wrong
- a design inconsistency
- a known limitation that should be tracked
- an error you made during the task

Then you must add or update an entry in `ERROR_FEEDBACK_README.md`.

If the issue is not fully fixed yet, write it clearly so the next pass can handle it.

### 3. Pause and check before finalizing

Before finalizing any meaningful change, stop and check:
- Is this actually correct?
- Is this the most generic solution that still fits the project?
- Is this easy for a human developer to understand?
- Did I overfit the code to one temporary case?
- Did I update docs if the behavior changed?
- Did I leave hidden assumptions undocumented?

Do not rush from “it works” to “done”.
Take a short verification pass and simplify if needed.

### 4. Prefer generic and understandable code

When multiple implementations are possible:
- prefer the one a human developer can read quickly
- prefer clear naming over cleverness
- prefer explicit contracts over implicit assumptions
- prefer simple data flow over hidden magic
- prefer config-driven behavior when the project already uses config for that concern

Avoid:
- unnecessary abstractions
- placeholder architecture with no active use
- unclear hidden coupling between frontend and backend
- code that only makes sense with chat context

### 5. Explain the real project, not the imagined project

Document only what is active and true right now.

If a file/module/flow exists but is empty, unused, or inactive:
- do not describe it as a real feature
- either omit it from the main architecture docs or clearly label it as inactive

### 6. Protect human readability

Assume a human developer will open the repo later without the chat history.

Code, docs, and structure should make sense on their own.

Every meaningful change should leave behind:
- readable code
- updated docs
- explicit contracts
- enough context for a developer to continue without guessing

## Documentation Rules

### README.md

Update `README.md` when changes affect:
- architecture
- active files/modules
- endpoints
- request/response shapes
- scoring logic
- project behavior
- setup/run instructions
- known limitations

### ERROR_FEEDBACK_README.md

Update `ERROR_FEEDBACK_README.md` when:
- the agent made an error
- a mismatch was discovered
- a rule was clarified by the user
- a logic trap should be remembered for future work

If a new user instruction changes how agents should work in this repo, record it there unless it is better promoted into this `AGENTS.md`.

## Cleanup Rules

If you remove dead code, placeholders, or unused files:
- verify they are truly unused
- remove stale references
- update `README.md`

Do not keep empty placeholder files unless they provide real value.

## Verification Rules

After code changes, do a reasonable verification pass.

Examples:
- compile checks
- tests if available
- endpoint contract checks
- searching for stale references
- validating config/data assumptions

If you could not verify something important, say so clearly.

## Final Check

Before considering the task complete, ask yourself:

1. Did I change anything that should also change the README?
2. Did I discover any mismatch or mistake that belongs in the error feedback file?
3. Is the solution correct?
4. Is the solution generic enough?
5. Is the solution easy for a human developer to understand and maintain?

If any answer is “no”, fix that before finishing.
