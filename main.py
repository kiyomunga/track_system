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
    db_user = models.User(name=user.name, block=user.block)
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

# 4. 特定の選手の特定種目における自己ベスト（PB）を取得する
@app.get("/users/{user_id}/pb/{event_name}", response_model=schemas.MatchResult)
def read_personal_best(user_id: int, event_name: str, db: Session = Depends(get_db)):
    # 🌟 魔法のルール：名前に「跳」か「投」が含まれていればフィールド種目判定
    is_field_event = "跳" in event_name or "投" in event_name

    # ベースとなる検索条件（この選手、この種目）
    query = db.query(models.MatchResult)\
              .filter(models.MatchResult.user_id == user_id)\
              .filter(models.MatchResult.event_name == event_name)

    # 種目特性によって並び替え（ソート）の向きを逆転させる
    if is_field_event:
        # フィールド種目：値が大きい方が良いので、降順（desc）で並べて一番上を取る
        pb = query.order_by(models.MatchResult.time_seconds.desc()).first()
    else:
        # トラック種目：値が小さい方が良いので、昇順（asc）で並べて一番上を取る
        pb = query.order_by(models.MatchResult.time_seconds.asc()).first()
           
    if pb is None:
        raise HTTPException(status_code=404, detail="該当する記録が見つかりません")
        
    return pb

# 5. 登録されている全ユーザー（選手）のリストを取得する
@app.get("/users/", response_model=list[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users

# 6. 特定の選手の全競技履歴を日付の降順（新しい順）で取得する
@app.get("/users/{user_id}/results/", response_model=list[schemas.MatchResult])
def read_user_results(user_id: int, db: Session = Depends(get_db)):
    # .order_by(models.MatchResult.date.desc()) が「日付の新しい順」というSQLの魔法です
    results = db.query(models.MatchResult)\
                .filter(models.MatchResult.user_id == user_id)\
                .order_by(models.MatchResult.date.desc())\
                .all()
    return results

# 7. 練習記録（親）とメニュー（子）を一括で保存する
@app.post("/users/{user_id}/practices/")
def create_practice(user_id: int, practice: schemas.PracticeSessionCreate, db: Session = Depends(get_db)):
    # ① まず親（その日のコンディション等）を保存する
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
    db.refresh(db_session) # 🌟 これで親の「ID」が確定する

    # ② 送られてきたメニュー（子）をループして、すべて親のIDと紐づけて保存する
    for menu in practice.menus:
        db_menu = models.PracticeMenu(
            session_id=db_session.id, # 確定した親IDをセット！
            category=menu.category,
            menu_name=menu.menu_name,
            distance=menu.distance,
            weight=menu.weight,
            reps=menu.reps,
            sets=menu.sets,
            time_seconds=menu.time_seconds
        )
        db.add(db_menu)
    
    db.commit() # 最後にまとめて金庫の扉を閉める
    return {"message": "練習記録とメニューの保存に成功しました！"}

# ＝＝＝ 🗑️ ユーザー削除API ＝＝＝
@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    # データベースから該当のIDを持つユーザーを探す
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    
    if db_user:
        db.delete(db_user) # 見つかったら削除
        db.commit()        # 金庫の変更を確定
        return {"message": f"ユーザーID {user_id} を完全に削除しました。"}
    
    return {"error": "そのユーザーは見つかりません。"}
