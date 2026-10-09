from sqlalchemy.orm import Session

from progress_fitness_api.schemas.sets import SetCreate
from progress_fitness_api.models.sets import Set

from datetime import datetime, timezone


def get_sets(db: Session, user_id: int) -> list[Set] | None:
    return db.query(Set).filter(Set.user_id == user_id)


def get_set(db: Session, set_id: int) -> Set:
    return db.query(Set).filter(Set.id == set_id).first()


def create_set(set: SetCreate, db: Session, user_id: int) -> Set:
    new_set = Set(
        user_id=user_id,
        date=set.date,
        day=set.day,
        exercise=set.exercise,
        reps=set.reps,
        weight=set.weight,
        volume=set.weight * set.reps,
        feel=set.feel,
        notes=set.notes,
        created_at=datetime.now(timezone.utc),
    )

    db.add(new_set)
    db.commit()
    db.refresh(new_set)

    return new_set


def delete_set(db: Session, set_id: int) -> bool:
    current_set = get_set(db, set_id)

    if current_set is None:
        return False

    db.delete(current_set)
    db.commit()

    return True
