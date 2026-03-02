from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

# 1. 選手（ユーザー）テーブル
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True) # 選手名

    # 1対多のリレーション
    results = relationship("MatchResult", back_populates="user")

# 2. 試合記録テーブル
class MatchResult(Base):
    __tablename__ = "match_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id")) # 誰の記録か
    date = Column(Date)             # 試合日
    event_name = Column(String)     # 種目
    time_seconds = Column(Float)    # 記録
    wind = Column(Float)            # 風速

    # 紐づくユーザー情報へのアクセス用
    user = relationship("User", back_populates="results")
