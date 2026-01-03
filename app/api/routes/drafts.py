from fastapi import APIRouter, Depends, HTTPException
from uuid import uuid4

from app.core.config import settings
from app.services.storage.json_repository import JsonRepository
from app.services.storage.data_loader import DataLoader
from app.services.draft_engine.format_engine import FormatEngine
from app.services.draft_engine.validators import ensure_not_picked_or_banned, DraftValidationError
from app.models.schemas.draft_schemas import DraftCreateIn, DraftStateOut, DraftActionIn, DraftSideState, DraftTurn

router = APIRouter()
_DRAFTS: dict[str, dict] = {}

def get_loader():
    repo = JsonRepository(settings.data_dir)
    return DataLoader(repo)

@router.post("", response_model=DraftStateOut)
def create_draft(payload: DraftCreateIn, loader: DataLoader = Depends(get_loader)):
    draft_id = str(uuid4())
    state = {
        "draftId": draft_id,
        "mode": payload.mode,
        "status": "building",
        "blue": {"picks": [], "bans": []},
        "red": {"picks": [], "bans": []},
        "actionsDone": 0,
    }
    _DRAFTS[draft_id] = state
    return _to_out(state, loader)

@router.get("/{draft_id}", response_model=DraftStateOut)
def get_draft(draft_id: str, loader: DataLoader = Depends(get_loader)):
    if draft_id not in _DRAFTS:
        raise HTTPException(status_code=404, detail="Draft not found")
    return _to_out(_DRAFTS[draft_id], loader)

@router.post("/{draft_id}/action", response_model=DraftStateOut)
def apply_action(draft_id: str, action: DraftActionIn, loader: DataLoader = Depends(get_loader)):
    if draft_id not in _DRAFTS:
        raise HTTPException(status_code=404, detail="Draft not found")

    st = _DRAFTS[draft_id]
    fmt = FormatEngine(loader.draft_formats())
    turn = fmt.get_turn(st["mode"], st["actionsDone"])

    if action.side != turn.side_to_act or action.type != turn.action_type:
        raise HTTPException(status_code=400, detail="Not your turn / invalid action for this phase")

    try:
        ensure_not_picked_or_banned(action.championId, st["blue"], st["red"])
    except DraftValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    bucket = st[action.side]
    key = "picks" if action.type == "pick" else "bans"
    bucket[key].append(action.championId)
    st["actionsDone"] += 1

    if st["actionsDone"] >= fmt.total_actions(st["mode"]):
        st["status"] = "full"

    return _to_out(st, loader)

def _to_out(st: dict, loader: DataLoader) -> DraftStateOut:
    fmt = FormatEngine(loader.draft_formats())
    t = fmt.get_turn(st["mode"], st["actionsDone"])
    return DraftStateOut(
        draftId=st["draftId"],
        mode=st["mode"],
        status=st["status"],
        blue=DraftSideState(**st["blue"]),
        red=DraftSideState(**st["red"]),
        turn=DraftTurn(
            phaseIndex=t.phase_index,
            sideToAct=t.side_to_act,
            type=t.action_type,
            remainingInPhase=t.remaining_in_phase,
        )
    )
