from pydantic import BaseModel, Field

class Author(BaseModel):
    id: int | None = None
    name: str
    birth_year: int | None
