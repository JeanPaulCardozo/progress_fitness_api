from fastapi import APIRouter, HTTPException, Depends

from sqlalchemy.orm import Session

from progress_fitness_api.models.users import User
from progress_fitness_api.core.dependencies import get_current_user
from progress_fitness_api.database import get_db
from progress_fitness_api.services import plan_service
from progress_fitness_api.schemas.plan import PlanCreate, PlanOut

router = APIRouter(prefix="/plan", tags=["plan"])


@router.get("/", response_model=PlanOut, status_code=200)
def get_plan(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    plan = plan_service.get_plan(db, current_user.id)

    if plan is None:
        raise HTTPException(status_code=404, detail="Plan Not Found")

    return plan


@router.put("/", response_model=PlanOut, status_code=200)
def save_plan(
    plan: PlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return plan_service.save_plan(db, current_user.id, plan)
