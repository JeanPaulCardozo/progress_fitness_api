from pydantic import BaseModel, Field, EmailStr, ConfigDict


class UserBase(BaseModel):
    name: str = Field(..., min_length=5)
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserCreate(UserBase):
    pass


class UserUpdate(UserBase):
    pass


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)
