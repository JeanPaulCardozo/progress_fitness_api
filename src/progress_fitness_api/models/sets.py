from sqlalchemy import Integer, String, DateTime, ForeignKey, Column, Float, Enum

from progress_fitness_api.database import Base

import enum


class TypeFeel(str, enum.Enum):
    easy = "Fácil"
    moderate = "Moderado"
    hard = "Difícil"
    to_failure = "Al Fallo"


class Set(Base):
    __tablename__ = "Sets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("Users.id"), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    day = Column(Integer, nullable=False)
    exercise = Column(String, nullable=False)
    reps = Column(Integer, nullable=False)
    weight = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    feel = Column(Enum(TypeFeel, name="set_type_feel"))
    notes = Column(String)
    created_at = Column(DateTime(timezone=True), nullable=False)
