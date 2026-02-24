from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base

# プログラム起動時に、database.pyの定義に基づいてDBにテーブルを作成する
Base.metadata.create_all(bind=engine)

app = FastAPI()

# DBセッション（通信の窓口）を管理する関数
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