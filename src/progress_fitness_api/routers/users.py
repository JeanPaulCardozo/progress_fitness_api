from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse

from sqlalchemy.orm import Session

from progress_fitness_api.schemas.users import (
    UserCreate,
    Token,
    UserOut,
    ForgotPasswordIn,
    ResetPasswordIn,
)
from progress_fitness_api.database import get_db
from progress_fitness_api.core.dependencies import get_current_user
from progress_fitness_api.core.security import (
    create_access_token,
    create_reset_token,
    reset_password,
)
from progress_fitness_api.services import user_service
from progress_fitness_api.models.users import User
from progress_fitness_api.core.limiter import Limit
from progress_fitness_api.core.email import send_reset_email
from progress_fitness_api.core.google import google_login_url, fetch_google_user

import os

import secrets

import httpx

from dotenv import load_dotenv

load_dotenv()


FRONTEND_URL = os.getenv("FRONTEND_URL")
API_URL = os.getenv("API_URL", "")

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register_user(user: UserCreate, db: Session = Depends(get_db)):

    exist_user = user_service.get_user_by_email(db, user.email)

    if exist_user is not None:
        raise HTTPException(status_code=400, detail="User Already Registered")

    return user_service.create_user(user, db)


@router.post("/login", response_model=Token, status_code=200)
@Limit.limit("5/minute")
def login_user(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):

    user = user_service.authenticate_user(form_data.username, form_data.password, db)

    if user is None:
        raise HTTPException(status_code=401, detail="Email or Password Incorrect")

    access_token = create_access_token(data={"sub": str(user.id)})

    return Token(access_token=access_token)


@router.post("/forgot-password", status_code=204)
@Limit.limit("5/minute")
def forgot_password(
    background: BackgroundTasks,
    data: ForgotPasswordIn,
    request: Request,
    db: Session = Depends(get_db),
):
    user = user_service.get_user_by_email(db, data.email)

    if user is not None:
        token = create_reset_token(db, user)
        background.add_task(
            send_reset_email, data.email, f"{FRONTEND_URL}/?reset={token}"
        )


@router.post("/reset-password", status_code=204)
def restart_password(data: ResetPasswordIn, db: Session = Depends(get_db)):
    if not reset_password(db, data.token, data.password):
        raise HTTPException(
            status_code=400, detail="El enlace no es válido o ya caducó"
        )


@router.get("/google/login")
def google_login():
    state = secrets.token_urlsafe(16)
    response = RedirectResponse(google_login_url(state))

    response.set_cookie(
        "oauth_state",
        state,
        max_age=600,
        httponly=True,
        samesite="lax",
        secure=API_URL.startswith("https"),
    )
    return response


@router.get("/google/callback")
def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    db: Session = Depends(get_db),
):

    def back_to_app(fragment: str) -> RedirectResponse:
        response = RedirectResponse(f"{FRONTEND_URL}/#{fragment}")
        response.delete_cookie("oauth_state")

        return response

    expected = request.cookies.get("oauth_state")
    if (
        not code
        or not state
        or not expected
        or not secrets.compare_digest(state, expected)
    ):

        return back_to_app("error=google")

    try:
        info = fetch_google_user(code)
    except httpx.HTTPError as e:
        return back_to_app("error=google")

    user = user_service.get_create_google_user(db, info)

    if user is None:
        return back_to_app("error=google_email")

    token = create_access_token(data={"sub": str(user.id)})

    return back_to_app(f"token={token}")


@router.get("/me", response_model=UserOut, status_code=200)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user
