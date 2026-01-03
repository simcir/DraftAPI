from dataclasses import dataclass
from typing import Any, Dict

@dataclass(frozen=True)
class TurnInfo:
    phase_index: int
    side_to_act: str   # "blue" | "red"
    action_type: str   # "pick" | "ban"
    remaining_in_phase: int

class FormatEngine:
    def __init__(self, format_config: Dict[str, Any]):
        self.format_config = format_config

    def phases(self, mode: str):
        return self.format_config[mode]["phases"]

    def total_actions(self, mode: str) -> int:
        return sum(p["count"] for p in self.phases(mode))

    def get_turn(self, mode: str, actions_done: int) -> TurnInfo:
        phases = self.phases(mode)
        remaining = actions_done
        for i, ph in enumerate(phases):
            if remaining < ph["count"]:
                return TurnInfo(
                    phase_index=i,
                    side_to_act=ph["side"],
                    action_type=ph["type"],
                    remaining_in_phase=ph["count"] - remaining,
                )
            remaining -= ph["count"]

        last = phases[-1]
        return TurnInfo(
            phase_index=len(phases) - 1,
            side_to_act=last["side"],
            action_type=last["type"],
            remaining_in_phase=0,
        )
