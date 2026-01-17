from pydantic import BaseModel

from app.models.author import Author
from app.models.book import BookOut
from app.models.genre import GenreOut
from app.models.loan import LoanOut
from app.models.member import MemberOut


class MessageOut(BaseModel):
    message: str


class BookResponse(BaseModel):
    message: str
    data: BookOut


class AuthorResponse(BaseModel):
    message: str
    data: Author


class MemberResponse(BaseModel):
    message: str
    data: MemberOut


class LoanResponse(BaseModel):
    message: str
    data: LoanOut


class GenreResponse(BaseModel):
    message: str
    data: GenreOut
