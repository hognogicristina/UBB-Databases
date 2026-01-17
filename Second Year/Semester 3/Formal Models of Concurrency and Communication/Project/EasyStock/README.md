# EasyStock Library

FastAPI + SQLite app for managing a small library catalog, members, and loans. It includes a REST API and a simple HTML/CSS/JS UI served by the backend.

## Project layout
- Web/API layer: `app/api/routes.py`
- Business/Service layer: `app/service/book_service.py`, `app/service/author_service.py`, `app/service/member_service.py`, `app/service/loan_service.py`
- Data layer: `app/data/book_repo.py`, `app/data/author_repo.py`, `app/data/member_repo.py`, `app/data/loan_repo.py`, `app/data/db.py`
- UI assets: `app/ui` (served at `/` and `/operations`)
- Database: SQLite file at `data/easystock.db`

## Database schema
- authors (id, name, birth_year)
- genres (id, name)
- books (id, title, isbn)
- book_authors (book_id, author_id)
- book_genres (book_id, genre_id)
- members (id, name, email, registered_at)
- loans (id, book_id, member_id, loan_date, return_date)

## API overview
Base URL: `/api`

- Authors: `POST /authors`, `GET /authors`, `PUT /authors/{author_id}`, `DELETE /authors/{author_id}`
- Books: `POST /books`, `GET /books`, `GET /books/{book_id}`, `PUT /books/{book_id}`, `DELETE /books/{book_id}`
- Members: `POST /members`, `GET /members`, `PUT /members/{member_id}`, `DELETE /members/{member_id}`
- Loans: `POST /loans/borrow`, `POST /loans/{loan_id}/return`, `GET /loans/active`
- Reports: `GET /reports/members-with-loans`, `GET /reports/overdue-loans`
- Member history: `GET /members/{member_id}/history`

Pagination:
- `GET /authors`, `GET /books`, `GET /members`, `GET /loans/active`, `GET /members/{member_id}/history`
- Query params: `page` (default 1), `limit` (default 10, max 1000)
- Total count in response header: `X-Total-Count`

Validation and behavior:
- Books require a 13-digit `isbn` and valid `author_id` and `genre_id`.
- Members require a valid email format.
- Authors with books, and books/members with active loans, cannot be deleted.

## Run the server
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload
```

API will be available at `http://127.0.0.1:8000`.

To reset the database, run the following commands:

```bash
rm data/easystock.db
uvicorn app.main:app --reload
```

## Web UI
With the server running, open:

- Catalog Management: `http://127.0.0.1:8000/`
- Library Operations: `http://127.0.0.1:8000/operations`

The UI is served by the backend and uses basic HTML/CSS/JS to call the API.

## Notes
- Database schema is created automatically on startup.
- Seed data is inserted if the database is empty.
- Logs are emitted by `app/main.py` and the service layer.
