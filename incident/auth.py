import secrets
import time
import jwt
from .identity import Actor
from .passwords import hash_password, verify_password


class AuthManager:
    def __init__(self, store, secret):
        if not isinstance(secret, str) or len(secret) < 32:
            raise ValueError("Set a private signing secret of at least 32 characters")
        self.store = store
        self.secret = secret
        self.issuer = "incident-workbench"
        self.audience = "incident-api"

    def create_account(self, tenant, subject, password, roles):
        actor = Actor(tenant, subject, frozenset(roles))
        self.store.add_account(
            {
                "tenant": tenant,
                "subject": subject,
                "roles": sorted(actor.roles),
                "password_hash": hash_password(password),
            }
        )

    def login(self, subject, password):
        account = self.store.account(subject)
        if (
            not account
            or not account["roles"]
            or not verify_password(password, account["password_hash"])
        ):
            raise PermissionError("Account or password was not accepted")
        now = int(time.time())
        claims = {
            "sub": subject,
            "tenant": account["tenant"],
            "jti": secrets.token_hex(24),
            "iat": now,
            "exp": now + 1800,
            "iss": self.issuer,
            "aud": self.audience,
        }
        self.store.add_session(claims["jti"], subject, claims["exp"])
        return jwt.encode(claims, self.secret, algorithm="HS256")

    def _claims(self, token):
        try:
            claims = jwt.decode(
                token,
                self.secret,
                algorithms=["HS256"],
                issuer=self.issuer,
                audience=self.audience,
                options={"require": ["sub", "tenant", "jti", "iat", "exp"]},
            )
            if any(
                not isinstance(claims[name], str) or not claims[name]
                for name in ["sub", "tenant", "jti"]
            ):
                raise PermissionError("Invalid session identity")
            return claims
        except jwt.PyJWTError as error:
            raise PermissionError("Session is invalid or expired") from error

    def actor(self, token):
        claims = self._claims(token)
        account = self.store.account(claims["sub"])
        if (
            not account
            or account["tenant"] != claims["tenant"]
            or not account["roles"]
            or not self.store.session_active(claims["jti"], claims["sub"], time.time())
        ):
            raise PermissionError("Session no longer has access")
        return Actor(account["tenant"], account["subject"], frozenset(account["roles"]))

    def logout(self, token):
        self.store.revoke_session(self._claims(token)["jti"])
