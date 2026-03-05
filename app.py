import streamlit as st
import requests
from datetime import datetime

# バックエンドAPIのURL（FastAPIの窓口）
API_URL = "http://localhost:8000"
# MVP用戦略：自分自身のID「1」に固定
USER_ID = 1

st.set_page_config(page_title="Track Analytics", page_icon="🏃‍♂️")
st.title("🏃‍♂️ トラック・アナリティクス v1.0")
st.write("表記揺れを許さない、厳格なデータ入力フォーム")

# ＝＝＝ 📝 データ入力セクション ＝＝＝
with st.form("result_form"):
    date = st.date_input("日付", datetime.today())
    competition_name = st.text_input("大会名（または練習メニュー）", placeholder="例：春季記録会")
    
    event_name = st.selectbox(
        "種目",
        ("100m", "200m", "400m", "110mH", "走幅跳", "砲丸投", "やり投")
    )
    
    time_seconds = st.number_input("記録（タイムまたは距離）", min_value=0.0, step=0.01, format="%.2f")
    wind = st.number_input("風速（m/s）※跳躍・短距離のみ", value=0.0, step=0.1, format="%.1f")
    
    submitted = st.form_submit_button("記録を保存する")

if submitted:
    if competition_name == "" or time_seconds == 0.0:
        st.error("エラー：大会名と記録は必ず入力してください。")
    else:
        payload = {
            "date": date.isoformat(),
            "event_name": event_name,
            "competition_name": competition_name,
            "time_seconds": time_seconds,
            "wind": wind
        }
        try:
            response = requests.post(f"{API_URL}/users/{USER_ID}/results/", json=payload)
            if response.status_code == 200:
                st.success("✅ 記録が正常に金庫に保存されました！")
            else:
                st.error(f"保存失敗: {response.text}")
        except requests.exceptions.ConnectionError:
            st.error("🚨 サーバー通信エラー：APIサーバーが動いているか確認してください。")

# ＝＝＝ 🏆 PB確認セクション ＝＝＝
st.markdown("---")
st.subheader("🏆 自己ベスト (PB) の確認")

pb_event_name = st.selectbox(
    "PBを確認する種目", 
    ("100m", "200m", "400m", "110mH", "走幅跳", "砲丸投", "やり投"), 
    key="pb_select" 
)

if st.button(f"{pb_event_name} のPBを呼び出す"):
    try:
        pb_response = requests.get(f"{API_URL}/users/{USER_ID}/pb/{pb_event_name}")
        
        if pb_response.status_code == 200:
            pb_data = pb_response.json()
            st.success(f"🔥 {pb_event_name} の自己ベスト: {pb_data['time_seconds']} （大会名: {pb_data['competition_name']} / 記録日: {pb_data['date']}）")
        elif pb_response.status_code == 404:
            st.info(f"まだ {pb_event_name} の記録がありません。まずは上のフォームから登録してください。")
        else:
            st.error(f"取得失敗: {pb_response.text}")
            
    except requests.exceptions.ConnectionError:
        st.error("🚨 サーバー通信エラー：APIサーバーが動いているか確認してください。")
