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

# ＝＝＝ 👤 ユーザー関連API ＝＝＝

@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # 🌟 魔法のメソッド model_dump() を採用！
    # これにより、block, enrollment_year, is_active 等が増えても自動でマッピングされます
    db_user = models.User(**user.model_dump())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/", response_model=list[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.User).offset(skip).limit(limit).all()

@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user:
        db.delete(db_user)
        db.commit()
        return {"message": f"ユーザーID {user_id} を完全に削除しました。"}
    return {"error": "そのユーザーは見つかりません。"}

# ＝＝＝ 🏃‍♂️ 競技記録関連API ＝＝＝

@app.post("/users/{user_id}/results/", response_model=schemas.MatchResult)
def create_result_for_user(user_id: int, result: schemas.MatchResultCreate, db: Session = Depends(get_db)):
    # 🌟 ここも model_dump() のおかげで、round, status, attempts_detail 等の新規カラムが自動保存されます
    db_result = models.MatchResult(**result.model_dump(), user_id=user_id)
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result

@app.get("/users/{user_id}/results/", response_model=list[schemas.MatchResult])
def read_user_results(user_id: int, db: Session = Depends(get_db)):
    return db.query(models.MatchResult)\
                .filter(models.MatchResult.user_id == user_id)\
                .order_by(models.MatchResult.date.desc())\
                .all()

@app.get("/rankings/{event_name}", response_model=list[schemas.MatchResult])
def read_event_ranking(event_name: str, limit: int = 10, db: Session = Depends(get_db)):
    return db.query(models.MatchResult)\
                .filter(models.MatchResult.event_name == event_name)\
                .order_by(models.MatchResult.time_seconds.asc())\
                .limit(limit)\
                .all()

@app.get("/users/{user_id}/pb/{event_name}", response_model=schemas.MatchResult)
def read_personal_best(user_id: int, event_name: str, db: Session = Depends(get_db)):
    is_field_event = "跳" in event_name or "投" in event_name
    query = db.query(models.MatchResult)\
              .filter(models.MatchResult.user_id == user_id)\
              .filter(models.MatchResult.event_name == event_name)
    
    if is_field_event:
        pb = query.order_by(models.MatchResult.time_seconds.desc()).first()
    else:
        pb = query.order_by(models.MatchResult.time_seconds.asc()).first()
           
    if pb is None:
        raise HTTPException(status_code=404, detail="該当する記録が見つかりません")
    return pb

@app.delete("/results/{result_id}")
def delete_result(result_id: int, db: Session = Depends(get_db)):
    db_result = db.query(models.MatchResult).filter(models.MatchResult.id == result_id).first()
    if db_result:
        db.delete(db_result)
        db.commit()
        return {"message": f"記録ID {result_id} を完全に削除しました。"}
    return {"error": "その記録は見つかりません。"}

# ＝＝＝ 📝 練習記録関連API ＝＝＝

@app.post("/users/{user_id}/practices/")
def create_practice(user_id: int, practice: schemas.PracticeSessionCreate, db: Session = Depends(get_db)):
    db_session = models.PracticeSession(
        user_id=user_id,
        date=practice.date,
        rpe=practice.rpe,
        sleep_hours=practice.sleep_hours,
        body_weight=practice.body_weight,
        memo=practice.memo
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session) 

    for menu in practice.menus:
        db_menu = models.PracticeMenu(
            session_id=db_session.id, 
            category=menu.category,
            menu_name=menu.menu_name,
            distance=menu.distance,
            weight=menu.weight,
            reps=menu.reps,
            sets=menu.sets,
            time_seconds=menu.time_seconds,
            times_detail=menu.times_detail
        )
        db.add(db_menu)
    
    db.commit() 
    return {"message": "練習記録とメニューの保存に成功しました！"}

# ＝＝＝ 📊 分析用データ取得API（新規追加） ＝＝＝
@app.get("/users/{user_id}/practices/analytics")
def get_practice_analytics(user_id: int, db: Session = Depends(get_db)):
    # 親（コンディション）と子（メニュー）を結合し、Pandasで使いやすいフラットなリストにする
    query = db.query(
        models.PracticeSession.date,
        models.PracticeSession.rpe,
        models.PracticeSession.sleep_hours,
        models.PracticeSession.body_weight,
        models.PracticeSession.memo,
        models.PracticeMenu.category,
        models.PracticeMenu.menu_name,
        models.PracticeMenu.distance,
        models.PracticeMenu.time_seconds,
        models.PracticeMenu.times_detail,
        models.PracticeMenu.weight,
        models.PracticeMenu.reps,
        models.PracticeMenu.sets
    ).join(models.PracticeMenu, models.PracticeSession.id == models.PracticeMenu.session_id)\
     .filter(models.PracticeSession.user_id == user_id).all()
    
    # クエリ結果を辞書（JSON）のリストに変換して返す
    return [dict(row._mapping) for row in query]
