# Error Feedback README

Use this file when you want to report a mistake in my logic, code change, assumption, or documentation.

The goal is simple:
- you write the issue here
- I can read it next time
- I can correct the logic faster and with less back-and-forth

## When To Use This

Use this file if I did one of these:
- changed behavior you did not want
- misunderstood a rule of the draft/game
- documented something incorrectly
- used the wrong endpoint shape
- made a scoring mistake
- made a bad architectural assumption
- ignored a real constraint from the frontend or backend
- kept dead code in the explanation as if it was active

## Preferred Reporting Format

Copy this block and fill it:

```text
Date:

Area:
- API
- scoring
- profiles
- draft flow
- frontend contract
- documentation
- other

What Codex said or changed:

Why it is wrong:

What the correct logic should be:

Impact:
- low
- medium
- high

Files involved:

Example payload / example case:

Expected behavior:

Actual behavior:

Anything that must never be changed again:
```

## Short Version

If you want to be fast, just write:

```text
Error:
Correct rule:
Files:
Example:
```

## Scoring-Specific Feedback Template

Use this when the score logic is wrong:

```text
Scoring error:

Candidate champion:

Our picks:

Enemy picks:

Target role:

Why the current score/result is wrong:

What should have happened instead:

Should this be fixed in code or only in config?
```

## Documentation Feedback Template

Use this when the README is wrong:

```text
Section:

Wrong sentence:

Correct sentence:

Why the distinction matters:
```

## Rule For Future Me

When this file contains feedback, I should treat it as higher-priority local project knowledge and align future edits to it.

If multiple reports exist and they conflict:
- newest report wins unless you explicitly say otherwise

Project documentation rule:
- if I add, remove, rename, or deactivate a meaningful project file/module/endpoint/flow, I should update `README.md` in the same task
- README maintenance is part of done, not an optional cleanup step

Known scoring mismatch already discovered:
- do not confuse `target` or draft pick order with the real role priority for recommendations
- role pools stay lane-bound, but recommendation priority must be calculated from enemy locked roles and our remaining open roles
- a fixed `target role` interpretation can produce bad logic, for example recommending around `jungle` while the relevant enemy pressure is on `adc` and `support`

Known payload/role-assignment mismatch:
- if `draftState.picks.blue/red` are sent in draft order instead of fixed role-slot order, role locking becomes wrong
- example: `red = [Azir, Bard, null, null, null]` is currently read as `top, jungle, ...`, not `mid, support`
- in that case the scorer will think enemy locked `top` and `jungle`, which explains bad `jungle` priority
- this means the backend/frontend contract for role assignment is still not aligned enough

Current resolution for that mismatch:
- the scorer should infer likely roles from `data/champions.json` champion role metadata instead of trusting array position
- this is better for current frontend constraints, but still imperfect for true flex picks because no explicit picked role is provided

Known profile-storage mismatch already discovered:
- the old backend assumed exactly one stored profile per role file
- that blocked valid use cases where multiple named profiles exist for the same role
- the corrected model is: many stored profiles per role, one active profile per role for scoring

## Suggested Workflow

1. Add the error here.
2. Keep the example payload or example draft state.
3. Mark whether the fix is logic, config, endpoint contract, or docs.
4. Next time, ask me to read this file before changing the system.
