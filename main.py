from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models
import schemas

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
