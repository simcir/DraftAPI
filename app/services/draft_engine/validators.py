class DraftValidationError(Exception):
    pass

def ensure_not_picked_or_banned(champion_id: int, blue, red):
    if champion_id in blue["picks"] or champion_id in red["picks"] or champion_id in blue["bans"] or champion_id in red["bans"]:
        raise DraftValidationError("Champion déjà pick/ban.")
