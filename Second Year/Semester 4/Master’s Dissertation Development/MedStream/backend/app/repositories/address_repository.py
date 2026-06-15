from __future__ import annotations

from app.models.address import Address
from app.validators.address_validators import validate_address_create, validate_address_update


class AddressRepository:
    def create_address_with_session(self, db, payload: dict) -> Address:
        address_data = validate_address_create(payload)
        address = Address(**address_data)
        db.add(address)
        db.flush()
        return address

    def upsert_address_with_session(self, db, existing_address: Address | None, payload: dict | None) -> Address | None:
        address_data = validate_address_update(payload)
        if address_data is None:
            return existing_address

        if existing_address is None:
            return self.create_address_with_session(db, address_data)

        for field, value in address_data.items():
            setattr(existing_address, field, value)

        db.flush()
        return existing_address
