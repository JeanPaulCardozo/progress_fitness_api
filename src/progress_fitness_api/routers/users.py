from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm

from sqlalchemy.orm import Session

from progress_fitness_api.schemas.users import UserCreate, Token, UserOut
from progress_fitness_api.database import get_db
from progress_fitness_api.core.dependencies import get_current_user
from progress_fitness_api.core.security import create_access_token
from progress_fitness_api.services import user_service
from progress_fitness_api.models.users import User

router = APIRouter(prefix="/auth",tags=["auth"])

@router.post("/register", response_model=UserOut, status_code=201)
def register_user(user: UserCreate, db: Session = Depends(get_db)):

    exist_user = user_service.get_user_by_email(db, user.email)

    if exist_user is not None:
        raise HTTPException(status_code=400,detail="User Already Registered")

    return user_service.create_user(user,db)

@router.post("/login", response_model=Token, status_code=200)
def login_user(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):

    user = user_service.authenticate_user(form_data.username, form_data.password,db)

    if user is None:
        raise HTTPException(status_code=401, detail="Email or Password Incorrect")

    access_token = create_access_token(data={"sub":str(user.id)})

    return Token(access_token=access_token)

@router.get("/me",response_model=UserOut, status_code=200)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user
    