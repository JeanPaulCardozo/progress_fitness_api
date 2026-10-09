from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from progress_fitness_api.models.plan import Plan
from progress_fitness_api.schemas.plan import PlanCreate


def get_plan(db: Session, user_id: int) -> Plan | None:
    return db.query(Plan).filter(Plan.user_id == user_id).first()


def save_plan(db: Session, user_id: int, plan: PlanCreate) -> Plan:
    stmt = (
        insert(Plan)
        .values(user_id=user_id, text=plan.text)
        .on_conflict_do_update(index_elements=[Plan.user_id], set_={"text": plan.text})
        .returning(Plan)
    )

    plan = db.scalars(stmt).one()
    db.commit()

    return plan
