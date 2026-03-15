from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models, schemas

Base.metadata.create_all(bind=engine)
app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ＝＝＝ 👤 ユーザー関連 ＝＝＝
@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
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
        return {"message": "ユーザーを削除しました。"}
    return {"error": "ユーザーが見つかりません。"}

# ＝＝＝ 🎯 ターゲットレース関連（新規） ＝＝＝
@app.post("/users/{user_id}/targets/", response_model=schemas.TargetRace)
def create_target(user_id: int, target: schemas.TargetRaceCreate, db: Session = Depends(get_db)):
    db_target = models.TargetRace(**target.model_dump(), user_id=user_id)
    db.add(db_target)
    db.commit()
    db.refresh(db_target)
    return db_target

@app.get("/users/{user_id}/targets/", response_model=list[schemas.TargetRace])
def read_targets(user_id: int, db: Session = Depends(get_db)):
    return db.query(models.TargetRace).filter(models.TargetRace.user_id == user_id).order_by(models.TargetRace.race_date.asc()).all()

@app.delete("/targets/{target_id}")
def delete_target(target_id: int, db: Session = Depends(get_db)):
    db_target = db.query(models.TargetRace).filter(models.TargetRace.id == target_id).first()
    if db_target:
        db.delete(db_target)
        db.commit()
        return {"message": "目標レースを削除しました。"}
    return {"error": "目標レースが見つかりません。"}

# ＝＝＝ 🏃‍♂️ 試合記録関連 ＝＝＝
@app.post("/users/{user_id}/results/", response_model=schemas.MatchResult)
def create_result_for_user(user_id: int, result: schemas.MatchResultCreate, db: Session = Depends(get_db)):
    db_result = models.MatchResult(**result.model_dump(), user_id=user_id)
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result

@app.get("/users/{user_id}/results/", response_model=list[schemas.MatchResult])
def read_user_results(user_id: int, db: Session = Depends(get_db)):
    return db.query(models.MatchResult).filter(models.MatchResult.user_id == user_id).order_by(models.MatchResult.date.desc()).all()

@app.delete("/results/{result_id}")
def delete_result(result_id: int, db: Session = Depends(get_db)):
    db_result = db.query(models.MatchResult).filter(models.MatchResult.id == result_id).first()
    if db_result:
        db.delete(db_result)
        db.commit()
        return {"message": "記録を削除しました。"}
    return {"error": "記録が見つかりません。"}

# ＝＝＝ 📝 練習記録関連 ＝＝＝
@app.post("/users/{user_id}/practices/")
def create_practice(user_id: int, practice: schemas.PracticeSessionCreate, db: Session = Depends(get_db)):
    db_session = models.PracticeSession(
        user_id=user_id,
        date=practice.date,
        sleep_hours=practice.sleep_hours,
        body_weight=practice.body_weight,
        waking_hr=practice.waking_hr,
        memo=practice.memo,
        calorie=practice.calorie,
        protein=practice.protein,
        fat=practice.fat,
        carbo=practice.carbo,
        creatine_g=practice.creatine_g
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session) 

    for menu in practice.menus:
        db_menu = models.PracticeMenu(
            session_id=db_session.id, 
            category=menu.category,
            menu_name=menu.menu_name,
            purpose=menu.purpose,
            rpe=menu.rpe, # 🌟 メニューごとに保存
            distance=menu.distance,
            weight=menu.weight,
            reps=menu.reps,
            sets=menu.sets,
            time_seconds=menu.time_seconds,
            times_detail=menu.times_detail
        )
        db.add(db_menu)
    
    db.commit() 
    return {"message": "保存に成功しました！"}

@app.get("/users/{user_id}/practices/analytics")
def get_practice_analytics(user_id: int, db: Session = Depends(get_db)):
    query = db.query(
        models.PracticeSession.date,
        models.PracticeSession.sleep_hours,
        models.PracticeSession.body_weight,
        models.PracticeSession.memo,
        models.PracticeSession.calorie,
        models.PracticeSession.protein,
        models.PracticeSession.fat,
        models.PracticeSession.carbo,
        models.PracticeSession.waking_hr,
        models.PracticeSession.creatine_g,
        models.PracticeMenu.category,
        models.PracticeMenu.menu_name,
        models.PracticeMenu.purpose,
        models.PracticeMenu.rpe, # 🌟 ここから取得
        models.PracticeMenu.distance,
        models.PracticeMenu.time_seconds,
        models.PracticeMenu.times_detail,
        models.PracticeMenu.weight,
        models.PracticeMenu.reps,
        models.PracticeMenu.sets
    ).outerjoin(models.PracticeMenu, models.PracticeSession.id == models.PracticeMenu.session_id)\
     .filter(models.PracticeSession.user_id == user_id).all()
    
    return [dict(row._mapping) for row in query]
