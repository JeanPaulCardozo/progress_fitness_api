from pydantic import BaseModel, Field, ConfigDict


class PlanBase(BaseModel):
    text: str = Field(..., min_length=5)


class PlanCreate(PlanBase):
    pass


class PlanUpdate(PlanBase):
    pass


class PlanOut(PlanBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)
