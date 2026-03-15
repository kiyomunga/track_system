from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, Boolean
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    block = Column(String, index=True, nullable=True)
    enrollment_year = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)

    results = relationship("MatchResult", back_populates="user")
    targets = relationship("TargetRace", back_populates="user") # 🌟 新規追加

# 🌟 新規追加：ターゲットレース（目標）テーブル
class TargetRace(Base):
    __tablename__ = "target_races"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    race_name = Column(String)
    race_date = Column(Date)
    target_time = Column(Float)

    user = relationship("User", back_populates="targets")

class MatchResult(Base):
    __tablename__ = "match_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(String, index=True)
    event_name = Column(String, index=True)
    competition_name = Column(String)
    time_seconds = Column(Float, nullable=True)
    wind = Column(Float, nullable=True)
    round = Column(String, nullable=True)
    status = Column(String, nullable=True)
    attempts_detail = Column(String, nullable=True)
    weather = Column(String, nullable=True)
    temperature = Column(Float, nullable=True)
    caffeine_mg = Column(Integer, nullable=True)
    match_memo = Column(String, nullable=True)

    user = relationship("User", back_populates="results")

class PracticeSession(Base):
    __tablename__ = "practice_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    date = Column(Date, index=True)
    # 🚨 rpe はここから削除し、子メニューへ移動しました
    sleep_hours = Column(Float, nullable=True)
    body_weight = Column(Float, nullable=True)
    memo = Column(String, nullable=True)
    calorie = Column(Integer, nullable=True)
    protein = Column(Float, nullable=True)
    fat = Column(Float, nullable=True)
    carbo = Column(Float, nullable=True)
    waking_hr = Column(Integer, nullable=True)
    creatine_g = Column(Float, nullable=True)

    menus = relationship("PracticeMenu", back_populates="session")

class PracticeMenu(Base):
    __tablename__ = "practice_menus"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("practice_sessions.id")) 
    category = Column(String, index=True)
    menu_name = Column(String)
    purpose = Column(String, nullable=True)
    rpe = Column(Integer, nullable=True) # 🌟 ここに移動！メニューごとの主観的強度
    distance = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)
    reps = Column(Integer, nullable=True)
    sets = Column(Integer, nullable=True)
    time_seconds = Column(Float, nullable=True)
    times_detail = Column(String, nullable=True)
    
    session = relationship("PracticeSession", back_populates="menus")
