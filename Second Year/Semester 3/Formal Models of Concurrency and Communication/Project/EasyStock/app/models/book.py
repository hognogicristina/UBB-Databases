from pydantic import BaseModel

class BookBase(BaseModel):
    title: str
    isbn: str

class BookCreate(BookBase):
    author_id: int
    genre_id: int

class BookUpdate(BaseModel):
    title: str | None
    isbn: str | None
    author_id: int | None
    genre_id: int | None

class BookOut(BookBase):
    id: int
    author_id: int | None
    author: str | None
    genre_id: int | None
    genre: str | None
    is_borrowed: bool
