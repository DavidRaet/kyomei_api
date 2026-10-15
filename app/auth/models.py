from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class CurrentUser:
    external_identity_id: str
    kyomei_user_id: UUID
