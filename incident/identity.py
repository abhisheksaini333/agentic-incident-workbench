from dataclasses import dataclass
import re

ROLES = frozenset({"viewer", "operator", "approver", "admin"})
PERMISSIONS = {
    "read": ROLES,
    "collect": frozenset({"operator", "admin"}),
    "edit": frozenset({"operator", "admin"}),
    "approve": frozenset({"approver", "admin"}),
    "admin": frozenset({"admin"}),
}


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9-]{1,47}", value):
        raise ValueError(
            "Use a lowercase identifier of 2 to 48 letters, digits or hyphens"
        )
    return value


@dataclass(frozen=True)
class Actor:
    tenant: str
    subject: str
    roles: frozenset[str]

    def __post_init__(self):
        identifier(self.tenant)
        if not isinstance(self.subject, str) or not 1 <= len(self.subject) <= 100:
            raise ValueError("Invalid account identifier")
        if not self.roles.issubset(ROLES):
            raise ValueError("Unknown application role")


def require(actor, operation):
    if operation not in PERMISSIONS or not actor.roles.intersection(
        PERMISSIONS[operation]
    ):
        raise PermissionError("This account cannot perform this operation")
