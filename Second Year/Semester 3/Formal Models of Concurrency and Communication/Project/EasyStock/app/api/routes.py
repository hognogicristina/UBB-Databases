from fastapi import APIRouter, HTTPException, Query, Response

from app.models.author import Author
from app.models.book import BookCreate, BookUpdate, BookOut
from app.models.genre import Genre, GenreOut
from app.models.member import Member, MemberOut
from app.models.loan import LoanCreate, LoanOut
from app.models.response import (
    AuthorResponse,
    BookResponse,
    LoanResponse,
    MemberResponse,
    MessageOut,
    GenreResponse,
)
from app.models.report import (
    MemberActiveLoan,
    MemberBorrowRecord,
    OverdueLoan,
)

from app.service.author_service import AuthorService
from app.service.book_service import BookService
from app.service.member_service import MemberService
from app.service.loan_service import LoanService
from app.service.genre_service import GenreService

router = APIRouter()

author_service = AuthorService()
book_service = BookService()
member_service = MemberService()
loan_service = LoanService()
genre_service = GenreService()

PAGE = Query(1, ge=1)
LIMIT = Query(10, ge=1, le=1000)


@router.post("/authors", response_model=AuthorResponse, status_code=201)
def create_author(payload: Author):
    try:
        author = author_service.create_author(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "message": f'Author {author["name"]} created.',
        "data": author,
    }


@router.get("/authors", response_model=list[Author])
def list_authors(response: Response, page: int = PAGE, limit: int = LIMIT):
    response.headers["X-Total-Count"] = str(author_service.count_authors())
    return author_service.list_authors(page, limit)


@router.put("/authors/{author_id}", response_model=AuthorResponse)
def update_author(author_id: int, payload: Author):
    try:
        author = author_service.update_author(author_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "message": f'Author {author["name"]} updated.',
        "data": author,
    }


@router.delete("/authors/{author_id}", response_model=MessageOut)
def delete_author(author_id: int):
    try:
        author = author_service.get_author(author_id)
        author_service.delete_author(author_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"message": "Author " + f'{author["name"]} deleted.'}


@router.post("/books", response_model=BookResponse, status_code=201)
def create_book(payload: BookCreate):
    try:
        book = book_service.create_book(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "message": f'Book {book["title"]} created.',
        "data": book,
    }


@router.get("/books", response_model=list[BookOut])
def list_books(
        response: Response,
        page: int = PAGE,
        limit: int = LIMIT,
        genre: str | None = None,
):
    response.headers["X-Total-Count"] = str(book_service.count_books(genre))
    return book_service.list_books(page, limit, genre)


@router.get("/genres", response_model=list[GenreOut])
def list_genres(response: Response, page: int = PAGE, limit: int = LIMIT):
    response.headers["X-Total-Count"] = str(genre_service.count_genres())
    return genre_service.list_genres(page, limit)


@router.post("/genres", response_model=GenreResponse, status_code=201)
def create_genre(payload: Genre):
    try:
        genre = genre_service.create_genre(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"message": f'Genre {genre["name"]} created.', "data": genre}


@router.put("/genres/{genre_id}", response_model=GenreResponse)
def update_genre(genre_id: int, payload: Genre):
    try:
        genre = genre_service.update_genre(genre_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"message": f'Genre {genre["name"]} updated.', "data": genre}


@router.delete("/genres/{genre_id}", response_model=MessageOut)
def delete_genre(genre_id: int):
    try:
        genre = genre_service.get_genre(genre_id)
        genre_service.delete_genre(genre_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"message": "Genre " + f'{genre["name"]} deleted.'}


@router.get("/books/{book_id}", response_model=BookOut)
def get_book(book_id: int):
    book = book_service.get_book(book_id)
    return book


@router.put("/books/{book_id}", response_model=BookResponse)
def update_book(book_id: int, payload: BookUpdate):
    try:
        book = book_service.update_book(book_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "message": f'Book {book["title"]} updated.',
        "data": book,
    }


@router.delete("/books/{book_id}", response_model=MessageOut)
def delete_book(book_id: int):
    try:
        book = book_service.get_book(book_id)
        book_service.delete_book(book_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"message": "Book " + f'{book["title"]} deleted.'}


@router.post("/members", response_model=MemberResponse, status_code=201)
def create_member(payload: Member):
    try:
        member = member_service.create_member(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "message": f'Member {member["name"]} created.',
        "data": member,
    }


@router.get("/members", response_model=list[MemberOut])
def list_members(response: Response, page: int = PAGE, limit: int = LIMIT):
    response.headers["X-Total-Count"] = str(member_service.count_members())
    return member_service.list_members(page, limit)


@router.put("/members/{member_id}", response_model=MemberResponse)
def update_member(member_id: int, payload: Member):
    try:
        member = member_service.update_member(member_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "message": f'Member {member["name"]} updated.',
        "data": member,
    }


@router.delete("/members/{member_id}", response_model=MessageOut)
def delete_member(member_id: int):
    try:
        member = member_service.get_member(member_id)
        member_service.delete_member(member_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"message": "Member " + f'{member["name"]} deleted.'}


@router.get("/reports/members-with-loans", response_model=list[MemberActiveLoan])
def members_with_active_loans():
    return member_service.members_with_active_loans()


@router.get("/reports/overdue-loans", response_model=list[OverdueLoan])
def overdue_loans():
    return loan_service.overdue_loans()


@router.get("/members/{member_id}/history", response_model=list[MemberBorrowRecord])
def member_borrow_history(
        member_id: int,
        response: Response,
        page: int = PAGE,
        limit: int = LIMIT,
):
    try:
        response.headers["X-Total-Count"] = str(
            loan_service.count_member_history(member_id)
        )
        return loan_service.member_history(member_id, page, limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/loans/borrow", response_model=LoanResponse, status_code=201)
def borrow_book(payload: LoanCreate):
    try:
        loan = loan_service.borrow_book(payload.book_id, payload.member_id)
        book = book_service.get_book(payload.book_id)
        member = member_service.get_member(payload.member_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "message": f'{member["name"]} borrowed {book["title"]}".',
        "data": loan,
    }


@router.post("/loans/{loan_id}/return", response_model=LoanResponse)
def return_book(loan_id: int):
    try:
        loan = loan_service.return_book(loan_id)
        book = book_service.get_book(loan["book_id"])
        member = member_service.get_member(loan["member_id"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "message": f'{member["name"]} returned {book["title"]}".',
        "data": loan,
    }


@router.get("/loans/active", response_model=list[LoanOut])
def list_active_loans(response: Response, page: int = PAGE, limit: int = LIMIT):
    response.headers["X-Total-Count"] = str(loan_service.count_active_loans())
    return loan_service.list_active_loans(page, limit)
