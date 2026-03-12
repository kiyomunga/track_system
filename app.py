import streamlit as st
import requests
import pandas as pd
from datetime import datetime

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Track Analytics", page_icon="🏃‍♂️", layout="wide")

# --- 🏟️ マスタデータ ---
TRACK_AND_FIELD_EVENTS = (
    "100m", "200m", "400m", "800m", "1500m", "3000m", "5000m", "10000m",
    "100mH", "110mH", "400mH", "3000mSC", "走高跳", "棒高跳", "走幅跳", "三段跳", "砲丸投", "円盤投", "ハンマー投", "やり投"
)
COMPETITION_MASTER = (
    "関東学生陸上競技対校選手権大会(関カレ)", "日本学生陸上競技対校選手権大会(全カレ)",
    "国公立27大学対校陸上競技大会", "四大戦", "春季記録会", "秋季記録会", "その他"
)
ROUNDS = ("予選", "準決勝", "決勝", "タイムレース", "一発勝負")
STATUSES = ("記録あり", "DNS", "DNF", "DQ", "NM")

# --- 🧠 データ取得関数 ---
@st.cache_data(ttl=60)
def get_users():
    try:
        res = requests.get(f"{API_URL}/users/?limit=1000", timeout=5)
        return res.json() if res.status_code == 200 else []
    except:
        return []

users_data = get_users()
if not users_data:
    st.error("🚨 サーバー通信エラー、またはユーザーが0人です。Swagger UIからユーザーを登録してください。")
    st.stop()

# 辞書化（名前からIDや詳細情報を引けるようにする）
user_dict = {u["name"]: u["id"] for u in users_data}
user_names = list(user_dict.keys())

# --- 🔐 サイドバー ---
mode = st.sidebar.radio("モード選択", ["🏃‍♂️ 選手モード（記録確認）", "📝 マネージャーモード（管理）"])

# 🟩 モード1：選手モード（陸マガ風UI ＆ UB完全対応）
if mode == "🏃‍♂️ 選手モード（記録確認）":
    st.title("🏃‍♂️ トラック・アナリティクス v3.0")
    
    blocks = list(set([u.get("block", "未設定") for u in users_data if u.get("block")]))
    c_b, c_u = st.columns(2)
    with c_b:
        selected_block = st.selectbox("1. パートを選択", ["すべてのパート"] + blocks)
    
    filtered_users = [u["name"] for u in users_data if selected_block == "すべてのパート" or u.get("block") == selected_block]
    with c_u:
        selected_user = st.selectbox("2. 選手を選択", ["-- 選択してください --"] + filtered_users)

    if selected_user != "-- 選択してください --":
        user_id = user_dict[selected_user]
        
        # ユーザーの詳細情報（入学年度など）を取得
        target_user_info = next((u for u in users_data if u["id"] == user_id), {})
        enrollment_year = target_user_info.get("enrollment_year")
        
        st.markdown("""
            <style>
            .riku-header { background-color: #A52A2A; color: white; padding: 5px 15px; font-weight: bold; border-radius: 5px; margin-bottom: 10px; }
            .year-title { background-color: #f0f2f6; color: #A52A2A; padding: 5px 10px; font-size: 20px; font-weight: bold; text-align: center; border-radius: 5px; margin-top: 15px; }
            </style>
        """, unsafe_allow_html=True)

        history_res = requests.get(f"{API_URL}/users/{user_id}/results/")
        if history_res.status_code == 200 and history_res.json():
            df = pd.DataFrame(history_res.json())
            df["date"] = pd.to_datetime(df["date"])
            
            # --- 🏆 PB, SB, UB の計算 ---
            st.markdown('<div class="riku-header">自己ベスト(PB) / 大学ベスト(UB) / シーズンベスト(SB)</div>', unsafe_allow_html=True)
            current_year = datetime.now().year
            
            # "記録あり" のデータのみを対象とする（DNSなどはベスト記録から除外）
            valid_df = df[(df["status"] == "記録あり") | (df["status"].isnull())]
            
            if not valid_df.empty:
                for event in valid_df["event_name"].unique():
                    st.markdown(f"**【 {event} 】**")
                    event_df = valid_df[valid_df["event_name"] == event].copy()
                    is_field = "跳" in event or "投" in event
                    
                    # 昇順か降順か（トラックは数値が小さい方が良い、フィールドは大きい方が良い）
                    sort_asc = not is_field
                    
                    # PB
                    pb_row = event_df.sort_values("time_seconds", ascending=sort_asc).iloc[0]
                    pb_text = f"{pb_row['time_seconds']}"
                    
                    # SB
                    sb_df = event_df[event_df["date"].dt.year == current_year]
                    sb_text = f"{sb_df.sort_values('time_seconds', ascending=sort_asc).iloc[0]['time_seconds']}" if not sb_df.empty else "N/A"
                    
                    # 🌟 UB (大学ベスト) の算出ロジック！
                    ub_text = "N/A"
                    if enrollment_year:
                        ub_start_date = pd.to_datetime(f"{enrollment_year}-04-01")
                        ub_df = event_df[event_df["date"] >= ub_start_date]
                        if not ub_df.empty:
                            ub_text = f"{ub_df.sort_values('time_seconds', ascending=sort_asc).iloc[0]['time_seconds']}"
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("PB (自己ベスト)", pb_text)
                    c2.metric("UB (大学ベスト)", ub_text)
                    c3.metric("SB (今年のベスト)", sb_text)
            else:
                st.write("有効な記録がありません。")

            # --- 📜 競技履歴（ラウンド・試技詳細対応） ---
            st.markdown('<div class="riku-header">競技履歴</div>', unsafe_allow_html=True)
            df["year"] = df["date"].dt.year
            for year in sorted(df["year"].unique(), reverse=True):
                st.markdown(f'<div class="year-title">{year}</div>', unsafe_allow_html=True)
                year_df = df[df["year"] == year].sort_values("date", ascending=False)
                for _, row in year_df.iterrows():
                    # タイトルにラウンドやステータスを反映
                    status_str = f"[{row['status']}] " if pd.notna(row['status']) and row['status'] != "記録あり" else ""
                    round_str = f"（{row['round']}）" if pd.notna(row['round']) else ""
                    title = f"📅 {row['date'].strftime('%Y-%m-%d')} ~ {row['competition_name']} {round_str}"
                    
                    with st.expander(title):
                        ca, cb, cc = st.columns(3)
                        ca.metric("種目", row["event_name"])
                        
                        # DNSなどの場合は記録を出さない
                        if pd.notna(row['status']) and row['status'] != "記録あり":
                            cb.metric("結果", row['status'])
                        else:
                            cb.metric("記録", f"{row['time_seconds']}")
                            
                        cc.metric("風速", f"{row['wind']:+.1f}m" if pd.notna(row["wind"]) else "N/A")
                        
                        # 🌟 跳躍/投擲の試技配列（詳細）がある場合のみ表示
                        if pd.notna(row.get('attempts_detail')) and row['attempts_detail'].strip() != "":
                            st.info(f"**試技詳細:** {row['attempts_detail']}")
        else:
            st.info("まだ競技記録が登録されていません。")


# 🟦 モード2：マネージャーモード（入力 ＆ 削除機能）
elif mode == "📝 マネージャーモード（管理）":
    st.title("📝 マネージャー専用ダッシュボード")
    auth = st.text_input("アクセスキーを入力", type="password")
    
    if auth == "mgr2026":
        # 🌟 タブを3つに拡張
        tab_input, tab_delete_record, tab_delete_user = st.tabs(["➕ 大会記録一括入力", "🗑️ 記録の削除", "🚨 選手の削除"])
        
        with tab_input:
            with st.form("bulk_input"):
                col1, col2 = st.columns(2)
                with col1: d = st.date_input("開催日", datetime.today())
                with col2: n = st.selectbox("大会名", COMPETITION_MASTER)
                
                init_df = pd.DataFrame([{
                    "選手名": user_names[0] if user_names else "", 
                    "種目": "100m", "ラウンド": "予選", "ステータス": "記録あり", 
                    "記録": 0.0, "風速": 0.0, "試技詳細": ""
                }])
                
                edited_df = st.data_editor(init_df, num_rows="dynamic", use_container_width=True,
                    column_config={
                        "選手名": st.column_config.SelectboxColumn("選手名", options=user_names, required=True),
                        "種目": st.column_config.SelectboxColumn("種目", options=TRACK_AND_FIELD_EVENTS, required=True),
                        "ラウンド": st.column_config.SelectboxColumn("ラウンド", options=ROUNDS, required=True),
                        "ステータス": st.column_config.SelectboxColumn("状態", options=STATUSES, required=True),
                        "記録": st.column_config.NumberColumn("記録(DNS等は0)", format="%.2f"),
                        "風速": st.column_config.NumberColumn("風速", format="%.1f"),
                        "試技詳細": st.column_config.TextColumn("試技詳細(跳・投用)")
                    })
                if st.form_submit_button("一括保存"):
                    sc, err = 0, 0
                    for _, row in edited_df.iterrows():
                        if row["ステータス"] != "記録あり" or row["記録"] > 0:
                            record_val = row["記録"] if row["ステータス"] == "記録あり" else None
                            payload = {
                                "date": d.isoformat(), "event_name": row["種目"], 
                                "competition_name": n, "time_seconds": record_val, 
                                "wind": row["風速"], "round": row["ラウンド"],
                                "status": row["ステータス"], "attempts_detail": row["試技詳細"]
                            }
                            try:
                                res = requests.post(f"{API_URL}/users/{user_dict[row['選手名']]}/results/", json=payload)
                                if res.status_code == 200: sc += 1
                                else: err += 1
                            except: err += 1
                    if sc > 0: st.success(f"✅ {sc}件保存しました！"); st.cache_data.clear()
                    if err > 0: st.error(f"🚨 {err}件の保存に失敗しました。")
                    
        with tab_delete_record:
            st.subheader("誤って登録した競技記録を削除する")
            del_user = st.selectbox("選手を選択", user_names, key="del_record_user")
            del_user_id = user_dict[del_user]
            
            res_history = requests.get(f"{API_URL}/users/{del_user_id}/results/", timeout=5)
            if res_history.status_code == 200 and res_history.json():
                del_df = pd.DataFrame(res_history.json())
                for _, row in del_df.iterrows():
                    col_info, col_btn = st.columns([4, 1])
                    with col_info:
                        # 🌟 先ほど修正した文字列のちぎれも完璧に修復済み
                        st.write(f"ID:{row['id']} | {row['date']} | {row['competition_name']} | {row['event_name']} | {row['time_seconds']} ({row['status']})")
                    with col_btn:
                        # 個別の記録削除は手軽に消せるようにそのまま配置
                        if st.button("削除", key=f"del_rec_{row['id']}"):
                            d_res = requests.delete(f"{API_URL}/results/{row['id']}")
                            if d_res.status_code == 200:
                                st.success("削除しました！画面をリロードしてください。")
                                st.cache_data.clear()
            else:
                st.info("削除できる記録がありません。")

        with tab_delete_user:
            st.subheader("⚠️ 選手の登録をシステムから完全に削除する")
            st.error("※警告：選手を削除すると、その選手に紐づくすべての競技記録も参照できなくなります。")
            
            user_to_delete = st.selectbox("削除する選手を選択してください", user_names, key="del_user_target")
            
            # 🌟 フールプルーフ（誤操作防止）安全装置
            confirm_delete = st.checkbox(f"本当に「{user_to_delete}」を完全に削除しますか？（この操作は元に戻せません）")
            
            if confirm_delete:
                # チェックを入れた時だけ、この赤い破壊ボタンが出現する
                if st.button("この選手を完全に削除する", type="primary"):
                    target_id = user_dict[user_to_delete]
                    res = requests.delete(f"{API_URL}/users/{target_id}")
                    if res.status_code == 200:
                        st.success(f"✅ {user_to_delete} をシステムから完全に消去しました。画面をリロードしてください。")
                        st.cache_data.clear()
                    else:
                        st.error("🚨 削除に失敗しました。")
