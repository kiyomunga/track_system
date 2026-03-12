from pydantic import BaseModel
from datetime import date
from typing import List, Optional

# --- 記録（MatchResult）の型 ---
class MatchResultBase(BaseModel):
    date: str
    event_name: str
    competition_name: str
    time_seconds: Optional[float] = None
    wind: Optional[float] = None
    round: Optional[str] = None
    status: Optional[str] = None
    attempts_detail: Optional[str] = None

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
    block: Optional[str] = None
    enrollment_year: Optional[int] = None
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    results: List[MatchResult] = []

    class Config:
        from_attributes = True

# ＝＝＝ 📝 練習メニュー（子）の受け取りルール ＝＝＝
class PracticeMenuCreate(BaseModel):
    category: str
    menu_name: str
    distance: Optional[float] = None
    weight: Optional[float] = None
    reps: Optional[int] = None
    sets: Optional[int] = None
    time_seconds: Optional[float] = None

# ＝＝＝ 🏃‍♂️ 練習セッション（親）の受け取りルール ＝＝＝
class PracticeSessionCreate(BaseModel):
    date: date
    rpe: Optional[int] = None
    sleep_hours: Optional[float] = None
    body_weight: Optional[float] = None
    memo: Optional[str] = None
    # 🌟 ここで「複数の子メニュー」をリストとして丸ごと受け取る！
    menus: List[PracticeMenuCreate]
