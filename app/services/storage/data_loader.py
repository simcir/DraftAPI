from app.services.storage.json_repository import JsonRepository

ROLE_ORDER = ["top", "jungle", "mid", "adc", "support"]


class DataLoader:
    def __init__(self, repo: JsonRepository):
        self.repo = repo

    def champions(self):
        return self.repo.read("champions.json")

    def role_store(self, role: str):
        raw = self.repo.read(f"roles/{role}.json")
        return _normalize_role_store(raw, role)

    def role_profile(self, role: str, profile_name: str | None = None):
        store = self.role_store(role)
        target_profile = profile_name or store["activeProfile"]
        for profile in store["profiles"]:
            if profile.get("profile") == target_profile:
                return profile
        raise FileNotFoundError(f"Profile not found for role {role}: {target_profile}")

    def role_profiles(self):
        profiles = []
        for role in ROLE_ORDER:
            profile = self.role_profile(role)
            stored_role = profile.get("role")
            if stored_role != role:
                raise ValueError(f"Role profile mismatch for {role}: found {stored_role!r}")
            if not profile.get("profile"):
                raise ValueError(f"Missing profile name for role {role}")
            champions = profile.get("champions")
            if not isinstance(champions, list):
                raise ValueError(f"Invalid champions pool for role {role}")
            profiles.append(profile)
        return profiles

    def draft_formats(self):
        return self.repo.read("configs/draft_formats.json")

    def scoring_weights(self):
        return self.repo.read("configs/scoring_weights.json")

    def color_rules(self):
        return self.repo.read("configs/color_rules.json")


def _normalize_role_store(raw: dict, role: str) -> dict:
    if "profiles" in raw:
        profiles = raw.get("profiles", [])
        if not isinstance(profiles, list):
            raise ValueError(f"Invalid role profile catalog for {role}")
        active_profile = raw.get("activeProfile")
        normalized_profiles = []
        for profile in profiles:
            normalized_profile = _normalize_profile(profile, role)
            normalized_profiles.append(normalized_profile)
        if not normalized_profiles:
            raise ValueError(f"Role profile catalog is empty for {role}")
        if not active_profile:
            active_profile = normalized_profiles[0]["profile"]
        if active_profile not in {profile["profile"] for profile in normalized_profiles}:
            raise ValueError(f"Active profile mismatch for role {role}: {active_profile!r}")
        return {
            "role": role,
            "activeProfile": active_profile,
            "profiles": normalized_profiles,
        }
    return {
        "role": role,
        "activeProfile": raw.get("profile"),
        "profiles": [_normalize_profile(raw, role)],
    }


def _normalize_profile(profile: dict, role: str) -> dict:
    stored_role = profile.get("role")
    if stored_role != role:
        raise ValueError(f"Role profile mismatch for {role}: found {stored_role!r}")
    if not profile.get("profile"):
        raise ValueError(f"Missing profile name for role {role}")
    champions = profile.get("champions")
    if not isinstance(champions, list):
        raise ValueError(f"Invalid champions pool for role {role}")
    return {
        "profile": profile["profile"],
        "role": role,
        "champions": champions,
    }
