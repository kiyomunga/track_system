from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, Boolean
from sqlalchemy.orm import relationship
from database import Base

# --- User クラスの変更 ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    block = Column(String, index=True, nullable=True)
    
    # 🌟 ここを追加！：スケーラビリティとUB計算のための属性
    enrollment_year = Column(Integer, nullable=True) # 入学年度（例：2025）
    is_active = Column(Boolean, default=True)        # 現役/引退フラグ（デフォは現役）

    results = relationship("MatchResult", back_populates="user")

# --- MatchResult クラスの変更 ---
class MatchResult(Base):
    __tablename__ = "match_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(String, index=True)
    event_name = Column(String, index=True)
    competition_name = Column(String)
    time_seconds = Column(Float, nullable=True) # DQやDNSの時はここは空(Null)になる
    wind = Column(Float, nullable=True)
    
    # 🌟 ここを追加！：競技ドメインへの完全対応
    round = Column(String, nullable=True)           # 予選、準決勝、決勝など
    status = Column(String, nullable=True)          # DNS, DNF, DQ, NM など
    attempts_detail = Column(String, nullable=True) # 跳躍/投擲の全試技（カンマ区切り等）

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
