from pydantic import BaseModel

class ChampionOut(BaseModel):
    id: int
    name: str
    slug: str
    img: str = ""