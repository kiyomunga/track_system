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

# --- 🧠 データ取得関数 ---
@st.cache_data(ttl=60)
def get_users():
    try:
        res = requests.get(f"{API_URL}/users/?limit=1000")
        return res.json() if res.status_code == 200 else []
    except:
        return []

users_data = get_users()
if not users_data:
    st.error("🚨 サーバー通信エラー、またはユーザーが0人です。")
    st.stop()

user_dict = {u["name"]: u["id"] for u in users_data}
user_names = list(user_dict.keys())

# --- 🔐 サイドバー ---
mode = st.sidebar.radio("モード選択", ["🏃‍♂️ 選手モード（記録確認）", "📝 マネージャーモード（一括入力）"])

# 🟩 モード1：選手モード（陸マガ風UI）
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
        
        # --- 🎨 陸マガ風カスタムCSS ---
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
            
            # 1. 年次ベスト
            st.markdown('<div class="riku-header">年次ベスト（公認のみ）</div>', unsafe_allow_html=True)
            for event in df["event_name"].unique():
                st.markdown(f"**{event} 年次ベスト**")
                event_df = df[df["event_name"] == event]
                pb_row = event_df.sort_values("time_seconds").iloc[0]
                
                c1, c2, c3 = st.columns([1, 1, 2])
                c1.caption("年月日"); c2.caption("区分"); c3.caption("記録")
                r1, r2, r3 = st.columns([1, 1, 2])
                r1.write(pb_row["date"].strftime("%y/%m/%d"))
                r2.write("大学")
                r3.write(f"**<span style='color:red'>PB</span> {pb_row['time_seconds']}**", unsafe_allow_html=True)

            # 2. 競技履歴
            st.markdown('<div class="riku-header">競技履歴</div>', unsafe_allow_html=True)
            df["year"] = df["date"].dt.year
            for year in sorted(df["year"].unique(), reverse=True):
                st.markdown(f'<div class="year-title">{year}</div>', unsafe_allow_html=True)
                year_df = df[df["year"] == year].sort_values("date", ascending=False)
                for _, row in year_df.iterrows():
                    with st.expander(f"📅 {row['date'].strftime('%Y-%m-%d')} ~ {row['competition_name']}"):
                        ca, cb, cc = st.columns(3)
                        ca.metric("種目", row["event_name"])
                        cb.metric("記録", f"{row['time_seconds']}秒")
                        cc.metric("風速", f"{row['wind']:+.1f}m")
        else:
            st.info("まだ競技記録が登録されていません。")

# 🟦 モード2：マネージャーモード
elif mode == "📝 マネージャーモード（一括入力）":
    st.title("📝 一括入力ダッシュボード")
    auth = st.text_input("アクセスキーを入力", type="password")
    if auth == "mgr2026":
        with st.form("bulk_input"):
            col1, col2 = st.columns(2)
            with col1: d = st.date_input("開催日", datetime.today())
            with col2: n = st.selectbox("大会名", COMPETITION_MASTER)
            
            init_df = pd.DataFrame([{"選手名": user_names[0] if user_names else "", "種目": "100m", "記録": 0.0, "風速": 0.0}])
            edited_df = st.data_editor(init_df, num_rows="dynamic", use_container_width=True,
                column_config={
                    "選手名": st.column_config.SelectboxColumn("選手名", options=user_names, required=True),
                    "種目": st.column_config.SelectboxColumn("種目", options=TRACK_AND_FIELD_EVENTS, required=True),
                    "記録": st.column_config.NumberColumn("記録", min_value=0.0, format="%.2f", required=True),
                    "風速": st.column_config.NumberColumn("風速", format="%.1f")
                })
            if st.form_submit_button("一括保存"):
                sc = 0
                for _, row in edited_df.iterrows():
                    if row["記録"] > 0:
                        requests.post(f"{API_URL}/users/{user_dict[row['選手名']]}/results/", 
                                      json={"date": d.isoformat(), "event_name": row["種目"], "competition_name": n, "time_seconds": row["記録"], "wind": row["風速"]})
                        sc += 1
                if sc > 0:
                    st.success(f"{sc}件保存完了"); st.cache_data.clear()
