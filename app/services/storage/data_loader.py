from app.services.storage.json_repository import JsonRepository

class DataLoader:
    def __init__(self, repo: JsonRepository):
        self.repo = repo

    def champions(self):
        return self.repo.read("champions.json")

    def role_profile(self, role: str):
        return self.repo.read(f"roles/{role}.json")

    def draft_formats(self):
        return self.repo.read("configs/draft_formats.json")
