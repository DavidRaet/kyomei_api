from dataclasses import dataclass


@dataclass(frozen=True)
class CurrentUser:
    external_identity_id: str
