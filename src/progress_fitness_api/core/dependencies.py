from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from sqlalchemy.orm import Session

from progress_fitness_api.core.security import decode_access_token
from progress_fitness_api.models.users import User
from progress_fitness_api.database import get_db
from progress_fitness_api.services.user_service import get_user_by_id

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    exception = HTTPException(status_code=401, headers={"WWW-Authenticate": "Bearer"})

    if token is None:
        raise exception

    payload = decode_access_token(token)

    if payload is None:
        raise exception

    sub = payload.get("sub")
    if sub is None:
        raise exception
    
    user = get_user_by_id(db, int(sub))

    if user is None:
        raise exception

    return user
