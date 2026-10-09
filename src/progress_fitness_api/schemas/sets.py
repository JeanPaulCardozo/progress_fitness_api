from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional

from progress_fitness_api.models.sets import TypeFeel

from datetime import datetime, date, timedelta


class SetBase(BaseModel):
    date: date
    day: int = Field(..., ge=1, le=7)
    exercise: str
    reps: int
    weight: float
    feel: TypeFeel
    notes: Optional[str] = None

    @field_validator("date")
    @classmethod
    def not_future(cls, value: date) -> date:
        if value > date.today() + timedelta(days=1):
            raise ValueError("Date cannot be in the future.")

        return value


class SetCreate(SetBase):
    pass


class SetOut(SetBase):
    id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
