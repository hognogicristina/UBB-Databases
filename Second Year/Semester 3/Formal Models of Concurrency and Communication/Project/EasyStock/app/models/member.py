from pydantic import BaseModel, Field

class Member(BaseModel):
    name: str
    email: str

class MemberOut(BaseModel):
    id: int
    name: str
    email: str
    registered_at: str
