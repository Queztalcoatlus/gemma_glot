import hashlib
import hmac
import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.models import AuthToken, User


PASSWORD_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected = stored_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), int(iterations))
    return hmac.compare_digest(digest.hex(), expected)


def issue_token(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    db.add(AuthToken(token_hash=hash_token(token), user_id=user.id))
    db.commit()
    return token


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to continue.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue.")

    auth_token = db.scalar(select(AuthToken).where(AuthToken.token_hash == hash_token(token)))
    if auth_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Your session is no longer valid.")
    return auth_token.user
