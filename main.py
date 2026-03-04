from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models
import schemas
from typing import Optional

# テーブルの作成
Base.metadata.create_all(bind=engine)

app = FastAPI()

# DBセッションの取得
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "Hello, 10.70秒への第一歩！"}

@app.get("/db-test")
def test_db(db: Session = Depends(get_db)):
    return {"status": "success", "message": "データベースに接続できました！"}

# --- ここから下が今回追加する「書き込み」機能 ---

# 1. 選手を登録するAPI
@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # models.User（DBの型）に、schemas（入力されたデータ）を変換して入れる
    db_user = models.User(name=user.name)
    db.add(db_user)      # DBに追加の準備
    db.commit()          # 実際に保存（コミット）
    db.refresh(db_user)  # 保存したデータ（自動で付いたIDなど）を最新化して取り出す
    return db_user

# 2. 試合記録を登録するAPI
@app.post("/users/{user_id}/results/", response_model=schemas.MatchResult)
def create_result_for_user(user_id: int, result: schemas.MatchResultCreate, db: Session = Depends(get_db)):
    # 記録データに「誰の記録か（user_id）」を紐付けて保存する
    db_result = models.MatchResult(**result.model_dump(), user_id=user_id)
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result

# --- 読み込み（GET）機能を追加 ---

# 1. 登録されている選手の一覧を取得する
@app.get("/users/", response_model=list[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users

# 2. 特定の選手の記録を取得する（種目で絞り込み可能）
@app.get("/users/{user_id}/results/", response_model=list[schemas.MatchResult])
def read_results_for_user(user_id: int, event_name: Optional[str] = None, db: Session = Depends(get_db)):
    # まず「その選手の記録」というベースの検索条件を作る
    query = db.query(models.MatchResult).filter(models.MatchResult.user_id == user_id)
    
    # もし「種目(event_name)」が指定されていたら、さらに条件を重ねる
    if event_name:
        query = query.filter(models.MatchResult.event_name == event_name)
        
    return query.all()

# 3. 種目別の歴代ランキングを取得する（タイムが速い順）
@app.get("/rankings/{event_name}", response_model=list[schemas.MatchResult])
def read_event_ranking(event_name: str, limit: int = 10, db: Session = Depends(get_db)):
    # 指定された種目の記録を、タイムの昇順（少ない＝速い順）で並び替え、上位を取得する
    ranking = db.query(models.MatchResult)\
                .filter(models.MatchResult.event_name == event_name)\
                .order_by(models.MatchResult.time_seconds.asc())\
                .limit(limit)\
                .all()
    return ranking
