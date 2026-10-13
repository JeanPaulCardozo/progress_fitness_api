from passlib.context import CryptContext

import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

from jose import jwt, JWTError

import hashlib
import secrets

from sqlalchemy.orm import Session
from progress_fitness_api.models.users import User

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"])

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))

RESET_MINUTES = int(os.getenv("RESET_MINUTES", "10"))


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_reset_token(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    user.reset_token_hash = _hash_token(token)
    user.reset_token_expires = datetime.now(timezone.utc) + timedelta(
        minutes=RESET_MINUTES
    )

    db.commit()
    return token


def reset_password(db: Session, token: str, password: str) -> bool:
    user = (
        db.query(User)
        .filter(
            User.reset_token_hash == _hash_token(token),
            User.reset_token_expires > datetime.now(timezone.utc),
        )
        .first()
    )

    if user is None:
        return False

    user.hashed_password = hash_password(password)
    user.reset_token_expires = None
    user.reset_token_hash = None

    db.commit()

    return True
