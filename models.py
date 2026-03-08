from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    results = relationship("MatchResult", back_populates="user")

class MatchResult(Base):
    __tablename__ = "match_results"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(Date)
    
    # DB上は単なる文字列（String）に戻す！
    event_name = Column(String)
    
    # 大会名を追加
    competition_name = Column(String) 
    
    time_seconds = Column(Float)
    wind = Column(Float)
    
    user = relationship("User", back_populates="results")

# ＝＝＝ 🏃‍♂️ 練習記録（親）テーブル ＝＝＝
class PracticeSession(Base):
    __tablename__ = "practice_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True) # 誰の練習か
    date = Column(Date, index=True)       # 日付
    
    # コンディション指標（AI解析の最重要変数）
    rpe = Column(Integer, nullable=True)         # 主観的疲労度 (1〜10)
    sleep_hours = Column(Float, nullable=True)   # 睡眠時間
    body_weight = Column(Float, nullable=True)   # 体重
    memo = Column(String, nullable=True)         # その日の総括メモ

# ＝＝＝ 📝 練習メニュー（子）テーブル ＝＝＝
class PracticeMenu(Base):
    __tablename__ = "practice_menus"

    id = Column(Integer, primary_key=True, index=True)
    # どの練習日（親）に紐づくかを示すカギ（外部キー）
    session_id = Column(Integer, ForeignKey("practice_sessions.id")) 
    
    category = Column(String, index=True)    # 大分類（スプリント、ウエイト、跳躍など）
    menu_name = Column(String)               # メニュー名（例: "30m", "スクワット"）
    
    # 「どんなタイムでこなしたか」を残すための変数群
    distance = Column(Float, nullable=True)  # 距離(m)
    weight = Column(Float, nullable=True)    # 重量(kg)
    reps = Column(Integer, nullable=True)    # 本数/回数
    sets = Column(Integer, nullable=True)    # セット数
    time_seconds = Column(Float, nullable=True) # タイム（かかった秒数）
