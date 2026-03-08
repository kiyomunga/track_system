import streamlit as st
import requests
from datetime import datetime
import pandas as pd

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Track Analytics", page_icon="🏃‍♂️")

# ＝＝＝ 🧠 Session State（状態管理）の初期化 ＝＝＝
# 「現在選ばれている選手」の記憶がなければ、空（None）にしておく
if "selected_user_id" not in st.session_state:
    st.session_state.selected_user_id = None
if "selected_user_name" not in st.session_state:
    st.session_state.selected_user_name = None

TRACK_AND_FIELD_EVENTS = (
    "100m", "200m", "400m", "800m", "1500m", "3000m", "5000m", "10000m",
    "100mH", "110mH", "400mH", "3000mSC", "4x100mR", "4x400mR",
    "走高跳", "棒高跳", "走幅跳", "三段跳",
    "砲丸投", "円盤投", "ハンマー投", "やり投",
    "十種競技", "七種競技", "5000mW", "10000mW", "20kmW"
)

# 🟩🟩🟩 画面①：トップページ（誰も選ばれていない時） 🟩🟩🟩
if st.session_state.selected_user_id is None:
    st.title("🏃‍♂️ トラック・アナリティクス v2.0")
    st.write("一橋大学・津田塾大学 陸上競技部 短距離ブロック専用プラットフォーム")
    
    st.markdown("---")
    st.subheader("🔍 選手の検索・選択")
    
    try:
        users_response = requests.get(f"{API_URL}/users/?limit=1000")
        if users_response.status_code == 200:
            user_list = users_response.json()
            if not user_list:
                st.warning("⚠️ 登録されている選手がいません。")
                st.stop()
                
            user_options = {user["name"]: user["id"] for user in user_list}
            
            # ドロップダウン（Streamlitのselectboxは文字入力で検索も可能です）
            selected_name = st.selectbox(
                "選手名を選択、または入力して検索してください", 
                ["-- 選択してください --"] + list(user_options.keys())
            )
            
            if st.button("選手のページへ移動 ➡️"):
                if selected_name != "-- 選択してください --":
                    # 選ばれた選手を「記憶」に書き込み、画面をリロード（rerun）する
                    st.session_state.selected_user_id = user_options[selected_name]
                    st.session_state.selected_user_name = selected_name
                    st.rerun()
                else:
                    st.error("選手を選択してください。")
        else:
            st.error("ユーザー情報の取得に失敗しました。")
    except requests.exceptions.ConnectionError:
        st.error("🚨 サーバー通信エラー。")


# 🟦🟦🟦 画面②：選手個別ページ（誰かが選ばれている時） 🟦🟦🟦
else:
    # 記憶から選手情報を引き出す
    USER_ID = st.session_state.selected_user_id
    selected_user_name = st.session_state.selected_user_name
    
    # ヘッダー領域（戻るボタン付き）
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title(f"🏃‍♂️ {selected_user_name} のページ")
    with col2:
        if st.button("🔙 検索に戻る"):
            # 記憶を消去して画面をリロードし、トップページに戻る
            st.session_state.selected_user_id = None
            st.session_state.selected_user_name = None
            st.rerun()

    st.markdown("---")
    tab_match, tab_practice = st.tabs(["🏆 試合記録", "🏃‍♂️ 練習メニュー"])

    # ▼▼▼ タブ1：試合記録 ▼▼▼
    with tab_match:
        with st.form("result_form"):
            st.write(f"**【 {selected_user_name} 】の試合記録を登録**")
            date = st.date_input("日付", datetime.today())
            competition_name = st.text_input("大会名", placeholder="例：春季記録会")
            event_name = st.selectbox("種目", TRACK_AND_FIELD_EVENTS)
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
                        st.success(f"✅ {selected_user_name} の記録が正常に保存されました！")
                    else:
                        st.error(f"保存失敗: {response.text}")
                except requests.exceptions.ConnectionError:
                    st.error("🚨 サーバー通信エラー。")

        st.markdown("---")
        st.subheader(f"🏆 {selected_user_name} の自己ベスト (PB)")
        pb_event_name = st.selectbox("PBを確認する種目", TRACK_AND_FIELD_EVENTS, key="pb_select")

        if st.button(f"{pb_event_name} のPBを呼び出す"):
            try:
                pb_response = requests.get(f"{API_URL}/users/{USER_ID}/pb/{pb_event_name}")
                if pb_response.status_code == 200:
                    pb_data = pb_response.json()
                    st.success(f"🔥 {pb_event_name} の自己ベスト: {pb_data['time_seconds']} （大会名: {pb_data['competition_name']} / 記録日: {pb_data['date']}）")
                elif pb_response.status_code == 404:
                    st.info(f"まだ {pb_event_name} の記録がありません。")
                else:
                    st.error("取得失敗")
            except requests.exceptions.ConnectionError:
                st.error("🚨 サーバー通信エラー。")

        st.markdown("---")
        st.subheader(f"📜 {selected_user_name} の競技履歴")
        try:
            history_response = requests.get(f"{API_URL}/users/{USER_ID}/results/")
            if history_response.status_code == 200:
                history_data = history_response.json()
                if not history_data:
                    st.info("まだ競技履歴が登録されていません。")
                else:
                    grouped_history = {}
                    for result in history_data:
                        group_key = f"📅 {result['date']} ｜ {result['competition_name']}"
                        if group_key not in grouped_history:
                            grouped_history[group_key] = []
                        grouped_history[group_key].append(result)

                    for group_key, results_list in grouped_history.items():
                        with st.expander(group_key):
                            for res in results_list:
                                wind_text = f" / **風速**: {res['wind']} m/s" if res['wind'] != 0.0 else ""
                                st.write(f"🏃‍♂️ **{res['event_name']}** ｜ **記録**: {res['time_seconds']} {wind_text}")
        except requests.exceptions.ConnectionError:
            st.error("🚨 サーバー通信エラー。")

        # ▼▼▼ タブ2：練習メニュー ▼▼▼
    with tab_practice:
        st.subheader(f"🏃‍♂️ {selected_user_name} の練習メニューを登録")
        
        with st.form("practice_form"):
            st.write("**① コンディション入力（親データ）**")
            p_date = st.date_input("練習日", datetime.today(), key="p_date")
            
            # 3列に分けて数値を入力しやすくする
            col1, col2, col3 = st.columns(3)
            with col1:
                rpe = st.number_input("疲労度(RPE 1-10)", min_value=1, max_value=10, value=5)
            with col2:
                sleep = st.number_input("前夜の睡眠時間(h)", min_value=0.0, step=0.5, value=7.0)
            with col3:
                weight = st.number_input("体重(kg)", min_value=0.0, step=0.1, value=65.0)
                
            memo = st.text_area("総括メモ", placeholder="例：アップ時のハムストリングスの張り感など")

            st.markdown("---")
            st.write("**② 練習メニュー入力（子データ）**")
            st.info("💡 下の表を直接クリックして編集できます。左下の「＋」マークで行の追加・削除が可能です。")
            
            # 初期データ（サンプルの行を1つ用意）
            init_df = pd.DataFrame([
                {"category": "スプリント", "menu_name": "30m", "distance": 30.0, "weight": 0.0, "reps": 3, "sets": 2, "time_seconds": 4.10}
            ])
            
            # Streamlitの超強力な「編集可能データフレーム」
            edited_df = st.data_editor(init_df, num_rows="dynamic", use_container_width=True)
            
            p_submitted = st.form_submit_button("練習記録とメニューを保存する")

        if p_submitted:
            # 表（データフレーム）のデータを、APIに送れる形式（辞書のリスト）に変換
            menus_list = edited_df.to_dict(orient="records")
            
            payload = {
                "date": p_date.isoformat(),
                "rpe": rpe,
                "sleep_hours": sleep,
                "body_weight": weight,
                "memo": memo,
                "menus": menus_list
            }
            
            try:
                p_res = requests.post(f"{API_URL}/users/{USER_ID}/practices/", json=payload)
                if p_res.status_code == 200:
                    st.success("✅ 練習記録とメニューが金庫に保存されました！")
                else:
                    st.error(f"保存失敗: {p_res.text}")
            except requests.exceptions.ConnectionError:
                st.error("🚨 サーバー通信エラー。")

