from pydantic import BaseModel
from datetime import date
from typing import List, Optional

# --- 記録（MatchResult）の型 ---
class MatchResultBase(BaseModel):
    date: date
    event_name: str
    time_seconds: float
    wind: float

class MatchResultCreate(MatchResultBase):
    pass

class MatchResult(MatchResultBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True

# --- 選手（User）の型 ---
class UserBase(BaseModel):
    name: str

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    results: List[MatchResult] = []

    class Config:
        from_attributes = True
