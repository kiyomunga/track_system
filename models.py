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
