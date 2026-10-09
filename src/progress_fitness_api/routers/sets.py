from fastapi import APIRouter, HTTPException, Depends

from sqlalchemy.orm import Session

from progress_fitness_api.core.dependencies import get_current_user
from progress_fitness_api.models.users import User
from progress_fitness_api.database import get_db
from progress_fitness_api.services import set_service
from progress_fitness_api.schemas.sets import SetCreate, SetOut

router = APIRouter(prefix="/sets", tags=["sets"])


@router.get("/", response_model=list[SetOut], status_code=200)
def get_sets(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return set_service.get_sets(db, current_user.id)


@router.post("/", response_model=SetOut, status_code=201)
def create_set(
    set: SetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return set_service.create_set(set, db, current_user.id)


@router.delete("/{set_id}", status_code=204)
def delete_set(
    set_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    current_set = set_service.get_set(db, set_id)

    if current_set is None:
        raise HTTPException(status_code=404, detail="Set Not Found")

    if current_set.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not Authorized To Access This Set")

    return set_service.delete_set(db, set_id)
