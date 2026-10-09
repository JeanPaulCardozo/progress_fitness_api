from sqlalchemy import Integer, String, ForeignKey, Column

from progress_fitness_api.database import Base


class Plan(Base):
    __tablename__ = "Plans"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("Users.id"), nullable=False, unique=True)
