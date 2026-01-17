import logging
from app.data import member_repo
from app.models.member import Member

logger = logging.getLogger(__name__)

class MemberService:
    def create_member(self, payload: Member) -> dict:
        self._ensure_email_unique(payload.email)
        self._validate_email(payload.email)
        self._validate_non_empty_string(payload.name, "Name")
        member = member_repo.create_member(payload)
        logger.info("Registered member name=%s", payload.name)
        return member

    def list_members(self, page: int, limit: int) -> list[dict]:
        offset = (page - 1) * limit
        return member_repo.list_members(limit, offset)

    def count_members(self) -> int:
        return member_repo.count_members()

    def delete_member(self, member_id: int) -> bool:
        self._validate_no_active_loans(member_id)
        deleted = member_repo.delete_member(member_id)
        logger.info("Deleted member successfully")
        return deleted

    def get_member(self, member_id: int) -> dict | None:
        return member_repo.get_member(member_id)

    def update_member(self, member_id: int, payload: Member) -> dict | None:
        self._ensure_email_unique_update(payload.email, member_id)
        self._validate_email(payload.email)
        self._validate_non_empty_string(payload.name, "Name")
        member = member_repo.update_member(member_id, payload)
        logger.info("Updated member name=%s", payload.name)
        return member

    def members_with_active_loans(self) -> list[dict]:
        return member_repo.members_with_active_loans()

    @staticmethod
    def _validate_email(email: str) -> None:
        if "@" not in email or "." not in email:
            raise ValueError("Invalid email address")


    @staticmethod
    def _ensure_email_unique(email: str) -> None:
        existing_members = member_repo.list_members(1000, 0)
        for member in existing_members:
            if member["email"] == email:
                raise ValueError("Email already in use.")

    @staticmethod
    def _ensure_email_unique_update(email: str, member_id: int) -> None:
        existing_members = member_repo.list_members(1000, 0)
        for member in existing_members:
            if member["email"] == email and member["id"] != member_id:
                raise ValueError("Email already in use.")

    @staticmethod
    def _validate_no_active_loans(member_id: int) -> None:
        if member_repo.has_active_loans(member_id):
            raise ValueError("Cannot delete member with active loans")

    @staticmethod
    def _validate_non_empty_string(value: str, field_name: str) -> None:
        if not value.strip():
            raise ValueError(f"{field_name} cannot be empty or just spaces.")