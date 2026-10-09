from sqlalchemy.orm import Session

from progress_fitness_api.models.users import User
from progress_fitness_api.schemas.users import UserCreate
from progress_fitness_api.core.security import verify_password, hash_password


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def create_user(user_schema: UserCreate, db: Session) -> User:
    new_user = User(
        name=user_schema.name,
        email=user_schema.email,
        hashed_password=hash_password(user_schema.password),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


def authenticate_user(email: str, password: str, db: Session) -> User | None:

    user = get_user_by_email(db, email)

    if user is None:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user
