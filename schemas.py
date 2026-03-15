from pydantic import BaseModel
from datetime import date
from typing import List, Optional

# 🌟 新規追加：ターゲットレース
class TargetRaceBase(BaseModel):
    race_name: str
    race_date: date
    target_time: float

class TargetRaceCreate(TargetRaceBase):
    pass

class TargetRace(TargetRaceBase):
    id: int
    user_id: int
    class Config:
        from_attributes = True

class MatchResultBase(BaseModel):
    date: str
    event_name: str
    competition_name: str
    time_seconds: Optional[float] = None
    wind: Optional[float] = None
    round: Optional[str] = None
    status: Optional[str] = None
    attempts_detail: Optional[str] = None
    weather: Optional[str] = None
    temperature: Optional[float] = None
    caffeine_mg: Optional[int] = None
    match_memo: Optional[str] = None

class MatchResultCreate(MatchResultBase):
    pass

class MatchResult(MatchResultBase):
    id: int
    user_id: int
    class Config:
        from_attributes = True

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
    targets: List[TargetRace] = [] # 🌟 新規追加
    class Config:
        from_attributes = True

class PracticeMenuCreate(BaseModel):
    category: str
    menu_name: str
    purpose: Optional[str] = None
    rpe: Optional[int] = None # 🌟 ここに移動！
    distance: Optional[float] = None
    weight: Optional[float] = None
    reps: Optional[int] = None
    sets: Optional[int] = None
    time_seconds: Optional[float] = None
    times_detail: Optional[str] = None

class PracticeSessionCreate(BaseModel):
    date: date
    # 🚨 rpe はここから削除
    sleep_hours: Optional[float] = None
    body_weight: Optional[float] = None
    memo: Optional[str] = None
    calorie: Optional[int] = None
    protein: Optional[float] = None
    fat: Optional[float] = None
    carbo: Optional[float] = None
    waking_hr: Optional[int] = None
    creatine_g: Optional[float] = None
    menus: List[PracticeMenuCreate]
