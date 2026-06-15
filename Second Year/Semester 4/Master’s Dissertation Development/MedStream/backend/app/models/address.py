from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    street: Mapped[str] = mapped_column(String(120))
    number: Mapped[str] = mapped_column(String(30))
    apartment: Mapped[str | None] = mapped_column(String(30), nullable=True)
    city: Mapped[str] = mapped_column(String(100))
    county: Mapped[str] = mapped_column(String(100))
    postal_code: Mapped[str] = mapped_column(String(20))
    country: Mapped[str] = mapped_column(String(100))
