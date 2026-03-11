# DraftAdvisor API

Backend API for a League of Legends draft helper.

The current project is centered on one job:
- load champion + role-profile data from JSON files
- expose small REST endpoints
- compute draft recommendations from a role-based scoring system

This README documents only the code that is active today. Empty placeholder files such as `app/services/history/*` are intentionally excluded from the main architecture because they are not used by the running API right now.

## Current Scope

What the project does today:
- serves champion data
- serves role-profile data for `top`, `jungle`, `mid`, `adc`, `support`
- serves draft format config
- creates in-memory draft sessions
- computes champion recommendations from open role pools, prioritized dynamically from the draft state

What it does not do yet:
- persistent draft storage
- real history/stat tracking
- active state-machine-based draft orchestration
- automated tests
- auth

## Project Layout

Active files:
- `app/main.py`: FastAPI app and CORS setup
- `app/api/router.py`: mounts all active API routers
- `app/api/routes/health.py`: health check
- `app/api/routes/champions.py`: champion read endpoints
- `app/api/routes/profiles.py`: role-profile read/update endpoints
- `app/api/routes/drafts.py`: in-memory draft creation and action flow
- `app/api/routes/recommendations.py`: draft recommendation endpoint
- `app/api/routes/configs.py`: config read endpoints
- `app/services/storage/json_repository.py`: low-level JSON read/write
- `app/services/storage/data_loader.py`: typed access to data files + role-profile validation
- `app/services/draft_engine/format_engine.py`: draft turn resolution from config
- `app/services/draft_engine/validators.py`: duplicate pick/ban validation
- `app/services/scoring/scoring_engine.py`: recommendation logic
- `app/services/scoring/color_rules.py`: color modifier helpers
- `data/champions.json`: full champion list + roles
- `data/roles/*.json`: one role profile file per lane
- `data/configs/draft_formats.json`: draft phase definitions
- `data/configs/scoring_weights.json`: score tuning weights
- `data/configs/color_rules.json`: color-specific modifiers

Inactive or empty right now:
- `app/api/routes/history.py`
- `app/services/history/history_service.py`
- `app/services/history/scoring_systems.py`
- `app/models/domain/*`

## Runtime Model

### Data Source

The API is JSON-file driven.

All reads and writes go through:
- `JsonRepository.read()`
- `JsonRepository.write()`

The base data directory comes from:
- `app/core/config.py`
- default value: `data`

### Role-Profile Contract

The system now assumes a strict role model:
- there are exactly 5 role files
- the role order is always:
  `top`, `jungle`, `mid`, `adc`, `support`
- each file must contain a matching `role`
- each role can contain multiple named profiles
- each role still has exactly one active profile assignment for scoring

Current files:
- `data/roles/top.json`
- `data/roles/jungle.json`
- `data/roles/mid.json`
- `data/roles/adc.json`
- `data/roles/support.json`

Internal role file shape now supports both:
- legacy single-profile format
- catalog format with:
  - `role`
  - `activeProfile`
  - `profiles`

This is normalized in `app/services/storage/data_loader.py`.

## API Overview

### Health

- `GET /health`

Returns:
- `{ "status": "ok" }`

### Champions

- `GET /champions`
- `GET /champions/{champion_id}`

Reads from `data/champions.json`.

### Profiles

- `GET /profiles`
  returns the 5 active profile names in role order

- `GET /profiles/assignments`
  returns explicit active role assignments:
  `[{ "profile": "...", "role": "top" }, ...]`

- `GET /profiles/catalog`
  returns all stored profiles across all roles

- `GET /profiles/{role}`
  returns the active profile for that role

- `PUT /profiles/{role}`
  upserts one named profile for that role and makes it the active profile
  accepted request keys:
  - canonical: `profile`, `role`, `champions`
  - frontend-friendly aliases: `profileName`, `role`, `entries`

- `GET /profiles/entries?profileName=...&role=...`
  returns entries for that exact named profile inside the role catalog

- `POST /profiles/entries`
  creates a champion entry for that named profile
  if the named profile does not exist yet for the role, it is created automatically

- `PUT /profiles/entries/{champion_id}`
  updates a champion entry inside that named profile

- `DELETE /profiles/entries/{champion_id}`

Important:
- profile pools are lane-bound
- `mid` entries are not a shared pool with `top`, etc.
- multiple profiles can now exist for the same role with different champion ratings and perspectives
- scoring still reads only the active profile for each role

### Drafts

- `POST /drafts`
- `GET /drafts/{draft_id}`
- `POST /drafts/{draft_id}/action`

Draft state is stored in-memory in `_DRAFTS` inside `app/api/routes/drafts.py`.

Important limitation:
- restarting the API clears all draft sessions

### Recommendations

- `POST /draft/recommendations`

This is the core endpoint.

Important contract:
- `draftState.picks.blue` must contain exactly 5 slots
- `draftState.picks.red` must contain exactly 5 slots
- empty slots must stay `null`
- the backend infers likely locked roles from `data/champions.json` role metadata
- role pools stay lane-bound, but role priority is calculated dynamically from inferred enemy locked roles and our remaining open roles
- `target` can still be sent by the client, but it is not the fixed source of role selection for scoring

If this shape is not respected, the endpoint now returns `400`.

### Configs

- `GET /configs/draft-formats`
- `GET /configs/draft-formats/{format_key}`

## Recommendation Flow

High-level flow for `POST /draft/recommendations`:

1. Validate that the 5 role-profile files exist and are coherent.
2. Validate that both pick arrays contain exactly 5 role slots.
3. Resolve `ourSide` and `enemySide`.
4. Convert current picks/bans into blocked champion ids.
5. Infer likely locked roles for each side from champion role metadata in `data/champions.json`.
6. Compute enemy role pressure from enemy locked role slots.
7. Rank our remaining open roles from that pressure.
8. Load the remaining role pools in that dynamic priority order.
9. Score each available champion in those pools.
10. Merge duplicate champion ids if the same champion exists in multiple role pools.
11. Sort descending by score.

This means role pools are still strict by lane, but the recommendation priority is computed from the draft state, not forced by a fixed target role.

## Scoring System

This section is the important one to keep and paste back later.

### Data Used During Score Computation

The scoring engine combines:
- the current role pool from `data/roles/{role}.json`
- global weights from `data/configs/scoring_weights.json`
- color modifiers from `data/configs/color_rules.json`
- our current picks
- enemy current picks
- bans and already-picked champs for blocking

Each profile champion entry contains:
- `id`
- `howGoodIAm`
- `colors`
- `synergy`
- `counters`
- `strongInto`
- `meta`

### Score Formula Summary

For each candidate champion in the selected role pools:

1. Start with base comfort/meta score.
2. Apply color base multiplier.
3. Add team-color-fit bonus if the current team already leans into colors.
4. Apply role-based multiplier if the enemy has locked that same role and we have not.
5. Add synergy score against our picks.
6. Subtract counter penalty if enemy picks counter the champion.
7. Add strong-into bonus against enemy picks.
8. Add color stacking bonuses from special color rules.

### Exact Logic Snapshot

You can paste this section back into chat if you want to discuss or redesign the scoring.

```text
ROLE ORDER
- top
- jungle
- mid
- adc
- support

ROLE PRIORITIZATION
- role pools stay fixed by lane
- recommendation priority is computed from remaining open roles
- enemy locked roles create extra weight on the corresponding open role on our side
- the scorer ranks remaining roles by that computed weight
- this is not hard-mapped from target.idx

LOCKED ROLES
- locked roles are inferred from champion role metadata in `data/champions.json`
- for single-role champions, that role is locked directly
- for multi-role champions, the scorer finds the most coherent unique role assignment across the picked champions
- this avoids treating draft-order arrays as role-slot arrays

BLOCKED CHAMPIONS
- all blue picks
- all red picks
- all blue bans
- all red bans

ROLE ORDER FOR SCORING
- start from our remaining open roles
- if enemy has locked a role that we have not locked:
  that role gets weight("roleCounterMultiplier")
- otherwise the default weight is 1.0
- sort remaining roles by computed weight desc, then by base role order
- score candidates from those role pools

BASE SCORE
score =
  howGoodIAm * weight("howGoodIAm")
+ meta * weight("meta")

then:
score *= color_multiplier.base

TEAM COLOR FIT
- compute our current team color counts from already-picked champions
- take the top 2 most frequent colors as target colors
- if the candidate has colors matching those target colors:
  score += weight("colorFit") * number_of_matching_target_colors

ROLE MULTIPLIER
- if enemy role is locked in a role that we have not locked yet:
  role multiplier for that role = weight("roleCounterMultiplier")
- if candidate role is adc and no counter multiplier applied:
  role multiplier = weight("adcFlexMultiplier")
- final:
  score *= role_multiplier

SYNERGY BONUS
- synergy_count = number of ids from candidate.synergy present in our picks
- if synergy_count > 0:
  score += weight("synergy") * color_multiplier.synergyMultiplier * synergy_count

COUNTER PENALTY
- counters_count = number of ids from candidate.counters present in enemy picks
- if counters_count > 0:
  score -= weight("counters")
           * color_multiplier.counterMultiplier
           * weight("counterPenaltyMultiplier")
           * counters_count

STRONG INTO BONUS
- strong_into_count = number of ids from candidate.strongInto present in enemy picks
- if strong_into_count > 0:
  score += weight("strongInto")
           * color_multiplier.strongIntoMultiplier
           * strong_into_count

TEAM COLOR BONUS
- for each candidate color:
  add modifiers.teamColorBonus if present
- then evaluate color conditions:
  currently supported condition:
  if == "team_has_same_color"
- if team color count for that color >= min:
  add condition bonus

FINAL STEP
- collect reasons
- if the same champion appears in more than one role pool, merge it into one recommendation entry
- keep the best score for that champion
- keep all proposed roles for that champion
- merge reasons without duplicates
- sort candidates by score descending
```

### Where To Change the Score

If you want to change scoring behavior, these are the main files:

- `app/services/scoring/scoring_engine.py`
  change score structure, role logic, matching logic, sorting

- `app/services/scoring/color_rules.py`
  change how color multipliers and color condition bonuses are applied

- `data/configs/scoring_weights.json`
  tune numeric weights without changing code

- `data/configs/color_rules.json`
  tune color behavior without changing code

### Practical Meaning of Each Weight

From `data/configs/scoring_weights.json`:

- `howGoodIAm`
  how much personal comfort matters

- `meta`
  how much the champion's current strength matters

- `colorFit`
  reward for matching the team color direction

- `synergy`
  reward per friendly synergy hit

- `counters`
  size of penalty when enemy picks counter the champion

- `strongInto`
  reward when the champion is good into enemy picks

- `counterPenaltyMultiplier`
  global severity applied to counter penalties

- `roleCounterMultiplier`
  multiplier when enemy has locked a role and we want to answer that role

- `roleDualMultiplier`
  currently not used by the active scoring path

- `adcFlexMultiplier`
  special multiplier for ADC if no role counter multiplier overrides it

### Practical Meaning of Color Rules

From `data/configs/color_rules.json`:

- every color can define `modifiers`
- for each multiplier key, the current code uses the maximum value found among the candidate champion's colors
- supported multiplier keys:
  `base`
  `synergyMultiplier`
  `counterMultiplier`
  `strongIntoMultiplier`
  `teamColorBonus`

Current color bonus condition system:
- only `team_has_same_color` is supported

### Important Scoring Behavior Notes

- recommendations are role-pool based, not global all-champion recommendations
- the engine keeps one pool per lane, but dynamically prioritizes which open role pools matter most
- if a champion exists in multiple role pools, the API returns it only once after deduplication
- when that happens, the recommendation item exposes all proposed roles for that champion
- bans and already-picked champions are excluded before scoring
- enemy role pressure is derived from locked enemy role slots
- our own locked roles are derived from our filled role slots
- champion native roles from `data/champions.json` are no longer the main source for deciding our role priority

## Draft Format Logic

Draft phase order is configured in `data/configs/draft_formats.json`.

`FormatEngine.get_turn(mode, actions_done)` walks through phases and returns:
- phase index
- side to act
- action type
- remaining actions in the current phase

This is used by `app/api/routes/drafts.py`.

## Data Editing Rules

### Champion Data

`data/champions.json` stores:
- champion identity
- display data
- champion roles

### Role Profile Data

Each `data/roles/{role}.json` can now store a profile catalog:
- `role`
- `activeProfile`
- `profiles`

Each stored profile contains:
- `profile`
- `role`
- `champions`

Each champion entry inside a profile is a scoring entry for that lane-specific pool.

### Config Data

`data/configs/scoring_weights.json`
- code-free numeric tuning

`data/configs/color_rules.json`
- code-free color tuning

`data/configs/draft_formats.json`
- code-free draft sequence tuning

## Known Limitations

- no test suite yet
- no persistence for draft sessions
- no versioned config/data migration
- empty placeholder modules still exist in the tree
- some route files use direct inline loader/repo creation instead of shared dependency wiring
- recommendation logic is deterministic and simple; it does not yet simulate future draft branches

## Quick Start

Because dependency metadata is not documented yet in this repository, the usual local run is simply to start the FastAPI app with your existing environment.

Typical command:

```bash
uvicorn app.main:app --reload
```

Default local frontend origins currently allowed by CORS:
- `http://localhost:5173`
- `http://127.0.0.1:5173`

## Copy/Paste Section For Future Chat

If you want to ask for score changes later, paste this:

```text
DraftAdvisor score logic:
- role order is top, jungle, mid, adc, support
- picks arrays contain up to 5 visible pick slots with null for empty slots
- locked roles are inferred from champion role data, not from array index
- role pools are lane-bound
- role priority is computed dynamically from enemy locked roles vs our open roles
- score uses:
  base comfort/meta
  color base multiplier
  team color fit
  role multiplier
  synergy bonus
  counter penalty
  strong-into bonus
  team color bonus
- files involved:
  app/services/scoring/scoring_engine.py
  app/services/scoring/color_rules.py
  data/configs/scoring_weights.json
  data/configs/color_rules.json
```
