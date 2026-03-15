import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import altair as alt

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

# --- 🔐 サイドバー（グローバルコンテキスト） ---
st.sidebar.title("⚙️ 設定")
st.sidebar.markdown("### 👤 選手選択")
# 🌟 モードを跨いで状態を保持する「グローバル選手」
global_user_name = st.sidebar.selectbox("あなた（対象選手）", user_names)
global_user_id = user_dict[global_user_name]

st.sidebar.markdown("---")
mode = st.sidebar.radio("モード選択", [
    "🏃‍♂️ 選手モード（記録確認）", 
    "📝 マネージャーモード（管理）", 
    "📱 練習日誌モード（入力）", 
    "📊 アナリティクス（分析）",
    "🎯 ピーキングモード（試合分析）"
])

# 🟩 モード1：選手モード
if mode == "🏃‍♂️ 選手モード（記録確認）":
    st.title("🏃‍♂️ トラック・アナリティクス v3.0")
    st.info(f"👤 **現在表示中:** {global_user_name} 選手のデータ") # 🌟 誰のデータか明確に表示
    
    # 👇 以前あった「パート選択」「選手選択」の冗長なUIを完全に削除し、グローバルIDを直結
    user_id = global_user_id
    
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

        # 🌟 ここから下の「競技履歴」のインデントを左に1つ（スペース4つ分）戻しました！
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
    
    # 🌟 この一番下の else も、`if history_res.status_code == 200` と同じインデントレベルに合わせました
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
                
                                # --- 試合データ入力表の初期値 ---
                init_df = pd.DataFrame([{
                    "選手名": user_names[0] if user_names else "", 
                    "種目": "100m", "ラウンド": "予選", "ステータス": "記録あり", 
                    "記録": 0.0, "風速": 0.0, 
                    "天気": "晴れ", "気温": 20.0, "カフェイン": 0, # 🌟 新規追加
                    "試技詳細": "", "試合メモ": "" # 🌟 新規追加
                }])
                
                edited_df = st.data_editor(init_df, num_rows="dynamic", use_container_width=True,
                    column_config={
                        "選手名": st.column_config.SelectboxColumn("選手名", options=user_names, required=True),
                        "種目": st.column_config.SelectboxColumn("種目", options=TRACK_AND_FIELD_EVENTS, required=True),
                        "ラウンド": st.column_config.SelectboxColumn("ラウンド", options=ROUNDS, required=True),
                        "ステータス": st.column_config.SelectboxColumn("状態", options=STATUSES, required=True),
                        "記録": st.column_config.NumberColumn("記録(DNS等は0)", format="%.2f"),
                        "風速": st.column_config.NumberColumn("風速", format="%.1f"),
                        "天気": st.column_config.SelectboxColumn("天気", options=["晴れ", "くもり", "雨", "雪", "屋内"]), # 🌟 新規追加
                        "気温": st.column_config.NumberColumn("気温(℃)", format="%.1f"), # 🌟 新規追加
                        "カフェイン": st.column_config.NumberColumn("カフェイン(mg)", format="%d"), # 🌟 新規追加
                        "試技詳細": st.column_config.TextColumn("試技詳細(跳・投用)"),
                        "試合メモ": st.column_config.TextColumn("試合メモ(感覚など)") # 🌟 新規追加
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
                                "status": row["ステータス"], "attempts_detail": row["試技詳細"],
                                "weather": row["天気"], "temperature": row["気温"], # 🌟 新規追加
                                "caffeine_mg": row["カフェイン"], "match_memo": row["試合メモ"] # 🌟 新規追加
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

# 🟩🟩🟩 モード3：練習日誌モード 🟩🟩🟩
elif mode == "📱 練習日誌モード（入力）":
    st.title("📱 ライフログ ＆ 練習日誌")
    st.info("食事のみの記録、または練習メニューと合わせての記録が可能です。")

    user_id = global_user_id
    st.write(f"👤 **対象選手:** {global_user_name}")


    if "menu_count" not in st.session_state:
        st.session_state.menu_count = 1

    def add_menu():
        st.session_state.menu_count += 1
    def remove_menu():
        if st.session_state.menu_count > 1:
            st.session_state.menu_count -= 1

    with st.expander("🍔 本日の食事・栄養・サプリ（独立して保存可能）", expanded=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1: cal = st.number_input("カロリー(kcal)", min_value=0, key="cal")
        with c2: pro = st.number_input("タンパク質(g)", min_value=0.0, key="pro")
        with c3: fat = st.number_input("脂質(g)", min_value=0.0, key="fat")
        with c4: carb = st.number_input("炭水化物(g)", min_value=0.0, key="carb")
        with c5: cre = st.number_input("クレアチン(g)", min_value=0.0, key="cre")
        
        if st.button("🍴 食事・サプリのみ保存"):
            payload = {
                "date": datetime.today().strftime('%Y-%m-%d'),
                "calorie": cal if cal > 0 else None,
                "protein": pro if pro > 0.0 else None,
                "fat": fat if fat > 0.0 else None,
                "carbo": carb if carb > 0.0 else None,
                "creatine_g": cre if cre > 0.0 else None,
                "menus": [] 
            }
            res = requests.post(f"{API_URL}/users/{user_id}/practices/", json=payload)
            if res.status_code == 200: st.success("✅ 食事・サプリ記録のみ保存しました！")
            else: st.error("保存エラー")

    st.markdown("---")

    with st.form("practice_form"):
        st.subheader("🏋️‍♂️ コンディション＆練習メニュー")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            p_date = st.date_input("日付", datetime.today())
            sleep = st.number_input("睡眠時間 (時間)", min_value=0.0, max_value=24.0, value=7.5, step=0.5)
        with col2:
            weight = st.number_input("体重 (kg) ※任意", min_value=0.0, value=0.0, step=0.1)
        with col3:
            waking_hr = st.number_input("起床時心拍数 (bpm)", min_value=0, max_value=200, value=0, step=1)
            st.caption("※0は未入力扱い")
        
        memo = st.text_area("練習全体のメモ・気づき・動きの感覚")

        st.markdown("---")
        
        menus_data = []
        for i in range(st.session_state.menu_count):
            st.markdown(f"**【 メニュー {i+1} 】**")
            mc1, mc2, mc3 = st.columns(3)
            with mc1:
                category = st.selectbox("カテゴリー", ["スプリント", "ウエイト", "ジャンプ", "ドリル", "その他"], key=f"cat_{i}")
                menu_name = st.text_input("メニュー名 (例: 60m, ハイクリーン)", key=f"name_{i}")
                purpose = st.selectbox("意図・目的", ["設定なし", "筋肥大", "最大筋力", "スピード(神経系)", "持久力", "技術", "回復"], key=f"purp_{i}")
            with mc2:
                distance = st.number_input("距離(m)", min_value=0.0, value=0.0, key=f"dist_{i}")
                time_str = st.text_input("タイム(秒) ※カンマ区切り可", placeholder="例: 7.10, 7.15", key=f"time_{i}")
                # 🌟 RPEがここに移動！メニューごとに独立した強度を持たせます
                rpe_val = st.number_input("RPE (1:楽〜10:限界)", min_value=1, max_value=10, value=5, key=f"rpe_{i}")
            with mc3:
                wt = st.number_input("重量(kg)", min_value=0.0, value=0.0, key=f"wt_{i}")
                reps = st.number_input("回数(Reps)", min_value=0, value=0, key=f"reps_{i}")
                sets = st.number_input("セット数", min_value=0, value=0, key=f"sets_{i}")
            
            best_time = None
            if time_str.strip():
                try:
                    times_list = [float(t.strip()) for t in time_str.split(",") if t.strip()]
                    if times_list: best_time = min(times_list)
                except ValueError: pass
            
            menus_data.append({
                "category": category,
                "menu_name": menu_name,
                "purpose": purpose if purpose != "設定なし" else None,
                "rpe": rpe_val, # 🌟 メニューごとのRPE
                "distance": distance if distance > 0 else None,
                "weight": wt if wt > 0 else None,
                "reps": reps if reps > 0 else None,
                "sets": sets if sets > 0 else None,
                "time_seconds": best_time,
                "times_detail": time_str.strip() if time_str.strip() else None
            })

        submitted = st.form_submit_button("💾 コンディション ＋ 練習を保存")

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1: st.button("➕ メニューを増やす", on_click=add_menu, use_container_width=True)
    with btn_col2: st.button("➖ メニューを減らす", on_click=remove_menu, use_container_width=True)

    if submitted:
        valid_menus = [m for m in menus_data if m["menu_name"].strip() != ""]
        payload = {
            "date": p_date.isoformat(), 
            "sleep_hours": sleep if sleep > 0 else None,
            "body_weight": weight if weight > 0 else None,
            "waking_hr": waking_hr if waking_hr > 0 else None,
            "memo": memo,
            "calorie": cal if cal > 0 else None,
            "protein": pro if pro > 0.0 else None,
            "fat": fat if fat > 0.0 else None,
            "carbo": carb if carb > 0.0 else None,
            "creatine_g": cre if cre > 0.0 else None,
            "menus": valid_menus
        }
        res = requests.post(f"{API_URL}/users/{user_id}/practices/", json=payload)
        if res.status_code == 200:
            st.success("✅ 全データを保存しました！")
            st.session_state.menu_count = 1
        else: st.error("🚨 保存エラー")


# 🟩🟩🟩 モード4：アナリティクス（分析） 🟩🟩🟩
elif mode == "📊 アナリティクス（分析）":
    st.title("📊 10.70秒への軌跡（データ分析ダッシュボード）")
    user_id = global_user_id
    st.write(f"👤 **対象選手:** {global_user_name}")


    res = requests.get(f"{API_URL}/users/{user_id}/practices/analytics", timeout=5)
    
    if res.status_code == 200 and res.json():
        df = pd.DataFrame(res.json())
        df["date"] = pd.to_datetime(df["date"])
        
        st.subheader("🏃‍♂️ スプリントタイム × コンディション")
        sprint_df = df[(df["category"] == "スプリント") & (df["time_seconds"].notnull()) & (df["time_seconds"] > 0)]
        
        if not sprint_df.empty:
            c1, c2 = st.columns(2)
            # 🌟 rpe がメニュー単位になったため、より正確な相関が出ます
            with c1: st.scatter_chart(sprint_df, x="rpe", y="time_seconds", color="menu_name")
            with c2: st.scatter_chart(sprint_df, x="sleep_hours", y="time_seconds", color="menu_name")
        else: st.warning("スプリントデータがありません。")

        st.markdown("---")
        st.subheader("🏋️‍♂️ ウエイトトレーニング推移（意図別）")
        weight_df = df[(df["category"] == "ウエイト") & (df["weight"].notnull()) & (df["weight"] > 0)].copy()
        
        if not weight_df.empty:
            weight_df["purpose_label"] = weight_df["purpose"].fillna("意図なし")
            weight_df["menu_with_purpose"] = weight_df["menu_name"] + " (" + weight_df["purpose_label"] + ")"
            max_weight_df = weight_df.groupby(["date", "menu_with_purpose"])["weight"].max().reset_index()
            pivot_df = max_weight_df.pivot(index="date", columns="menu_with_purpose", values="weight")
            st.line_chart(pivot_df)
        else: st.warning("ウエイトデータがありません。")
            
        st.markdown("---")
        st.subheader("📖 練習日誌アーカイブ")
        df_sorted = df.sort_values("date", ascending=False)
        
        for date, group in df_sorted.groupby("date", sort=False):
            first_row = group.iloc[0]
            date_str = date.strftime('%Y-%m-%d')
            hr_val = first_row.get('waking_hr')
            hr_str = f" | 心拍: {hr_val}bpm" if pd.notna(hr_val) else ""
            title = f"📅 {date_str} | 睡眠: {first_row.get('sleep_hours', 'N/A')}h{hr_str}"
            
            with st.expander(title):
                if pd.notna(first_row.get('memo')) and str(first_row['memo']).strip() != "":
                    st.info(f"**📝 メモ:** {first_row['memo']}")
                
                valid_group = group[group["menu_name"].notna()].copy()
                if not valid_group.empty:
                    # 🌟 RPEをメニューごとのテーブル列に表示
                    display_df = valid_group[["category", "menu_name", "rpe", "purpose", "time_seconds", "distance", "weight", "reps", "sets"]].copy()
                    display_df.columns = ["カテゴリー", "メニュー", "RPE", "意図", "ベスト(秒)", "距離", "重量", "回数", "セット"]
                    st.dataframe(display_df.fillna(""), hide_index=True, use_container_width=True)
                else:
                    st.write("※練習メニューの記録はありません")
    else:
        st.info("データがありません。")


# 🟩🟩🟩 モード5：ピーキングモード（試合分析） 🟩🟩🟩
elif mode == "🎯 ピーキングモード（試合分析）":
    st.title("🎯 ピーキング・アナリティクス")
    st.info("ターゲットレースへのカウントダウンと、過去の試合直前14日間のピーキングプロセスを可視化します。")

    user_id = global_user_id
    st.write(f"👤 **対象選手:** {global_user_name}")


    # --- 🌟 動的なターゲットレース設定 UI ---
    st.markdown("### 🎯 ターゲットレース設定")
    with st.expander("＋ 新しい目標大会を登録する", expanded=False):
        with st.form("target_form"):
            tc1, tc2, tc3 = st.columns(3)
            with tc1: t_name = st.text_input("大会名 (例: 三商戦)")
            with tc2: t_date = st.date_input("開催日")
            with tc3: t_time = st.number_input("目標タイム(秒)", min_value=0.0, format="%.2f")
            
            if st.form_submit_button("💾 目標を追加"):
                if t_name:
                    requests.post(f"{API_URL}/users/{user_id}/targets/", json={"race_name": t_name, "race_date": t_date.isoformat(), "target_time": t_time})
                    st.success("追加しました！画面をリロードしてください。")
                else:
                    st.error("大会名を入力してください。")

    # DBからターゲットレースを取得してカウントダウン表示
    targets_res = requests.get(f"{API_URL}/users/{user_id}/targets/")
    if targets_res.status_code == 200 and targets_res.json():
        target_races = targets_res.json()
        col_t1, col_t2 = st.columns(2)
        today = datetime.now().date()
        
        for i, race in enumerate(target_races):
            r_date = datetime.strptime(race["race_date"], "%Y-%m-%d").date()
            days_left = (r_date - today).days
            
            with [col_t1, col_t2][i % 2]:
                st.metric(label=f"🏆 {race['race_name']} まで", value=f"あと {days_left} 日", delta=f"Target: 100m {race['target_time']}秒", delta_color="off")
                if st.button("削除", key=f"del_tgt_{race['id']}"):
                    requests.delete(f"{API_URL}/targets/{race['id']}")
                    st.success("削除完了。画面をリロードしてください。")
    else:
        st.write("設定されているターゲットレースはありません。")

    st.markdown("---")

    # --- 📈 過去の試合の分析 ---
    st.markdown("### 📈 試合ごとのピーキング分析")
    matches_res = requests.get(f"{API_URL}/users/{user_id}/results/")
    if matches_res.status_code == 200 and matches_res.json():
        match_df = pd.DataFrame(matches_res.json())
        match_df["date"] = pd.to_datetime(match_df["date"])
        match_df = match_df.sort_values("date", ascending=False)
        
        match_options = [f"{row['date'].strftime('%Y/%m/%d')} - {row['competition_name']} ({row['event_name']})" for _, row in match_df.iterrows()]
        selected_match_str = st.selectbox("分析する試合を選択してください", match_options)
        selected_match_index = match_options.index(selected_match_str)
        match_data = match_df.iloc[selected_match_index]
        match_date = match_data["date"]
        
        st.markdown('<div class="riku-header">試合当日パフォーマンス</div>', unsafe_allow_html=True)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("種目 / 記録", f"{match_data['event_name']} : {match_data['time_seconds']}秒")
        m2.metric("風速", f"{match_data['wind']:+.1f} m/s" if pd.notna(match_data["wind"]) else "N/A")
        m3.metric("天気 / 気温", f"{match_data.get('weather', '未入力')} / {match_data.get('temperature', '-')}℃")
        m4.metric("カフェイン", f"{match_data.get('caffeine_mg', 0)} mg")
        
        if pd.notna(match_data.get("match_memo")) and match_data["match_memo"].strip():
            st.info(f"📝 **試合メモ:** {match_data['match_memo']}")

        st.markdown("---")
        st.markdown('<div class="riku-header">直前14日間のコンディション推移</div>', unsafe_allow_html=True)
        
        practices_res = requests.get(f"{API_URL}/users/{user_id}/practices/analytics")
        if practices_res.status_code == 200 and practices_res.json():
            prac_df = pd.DataFrame(practices_res.json())
            prac_df["date"] = pd.to_datetime(prac_df["date"])
            
            start_date = match_date - pd.Timedelta(days=14)
            period_df = prac_df[(prac_df["date"] >= start_date) & (prac_df["date"] <= match_date)].copy()
            
            if not period_df.empty:
                # 🌟 【負荷計算】RPEがメニューごとの値になったため、高精度の計算が実現します！
                # スプリント負荷 = (RPE^2) * 距離
                period_df["sprint_load"] = period_df.apply(lambda row: (row["rpe"]**2) * row["distance"] if row["category"] == "スプリント" and pd.notna(row["distance"]) and pd.notna(row["rpe"]) else 0, axis=1)
                # ウエイト負荷 = 重量 * 回数 * セット数
                period_df["weight_load"] = period_df.apply(lambda row: row["weight"] * row["reps"] * row["sets"] if row["category"] == "ウエイト" and pd.notna(row["weight"]) and pd.notna(row["reps"]) and pd.notna(row["sets"]) else 0, axis=1)
                
                daily_df = period_df.groupby("date").agg({
                    "sprint_load": "sum", "weight_load": "sum",
                    "sleep_hours": "max", "waking_hr": "max",
                    "protein": "max", "fat": "max", "carbo": "max", "creatine_g": "max"
                }).reset_index()

                st.write("**■ スプリント負荷（棒） × 睡眠時間（折れ線）**")
                base1 = alt.Chart(daily_df).encode(x=alt.X('date:T', title='日付', axis=alt.Axis(format='%m/%d')))
                bar1 = base1.mark_bar(opacity=0.6, color='#4682B4').encode(y=alt.Y('sprint_load:Q', title='スプリント総負荷'))
                line1 = base1.mark_line(color='#FF4500', point=True).encode(y=alt.Y('sleep_hours:Q', title='睡眠時間 (h)', scale=alt.Scale(domain=[0, 12])))
                st.altair_chart(alt.layer(bar1, line1).resolve_scale(y='independent'), use_container_width=True)

                st.write("**■ ウエイト負荷（棒） × 起床時心拍数（折れ線）**")
                base2 = alt.Chart(daily_df).encode(x=alt.X('date:T', title='日付', axis=alt.Axis(format='%m/%d')))
                bar2 = base2.mark_bar(opacity=0.6, color='#2E8B57').encode(y=alt.Y('weight_load:Q', title='ウエイト・トネージ(kg)'))
                line2 = base2.mark_line(color='#8A2BE2', point=True).encode(y=alt.Y('waking_hr:Q', title='起床時心拍数 (bpm)', scale=alt.Scale(zero=False)))
                st.altair_chart(alt.layer(bar2, line2).resolve_scale(y='independent'), use_container_width=True)

                st.markdown("#### 🍗 直前14日間の摂取栄養・サプリメント")
                nut_df = daily_df[["date", "protein", "fat", "carbo", "creatine_g"]].copy()
                nut_df["date"] = nut_df["date"].dt.strftime('%m/%d')
                nut_df.columns = ["日付", "タンパク質(g)", "脂質(g)", "炭水化物(g)", "クレアチン(g)"]
                nut_df = nut_df.fillna("-").set_index("日付").T
                st.dataframe(nut_df, use_container_width=True)

                st.markdown("#### 📖 直前2週間分の練習日誌")
                period_sorted = period_df.sort_values("date", ascending=False)
                for date, group in period_sorted.groupby("date", sort=False):
                    first_row = group.iloc[0]
                    date_str = date.strftime('%Y-%m-%d')
                    hr_val = first_row.get('waking_hr', 'N/A')
                    title = f"📅 {date_str} | 起床時心拍: {hr_val}bpm | 睡眠: {first_row.get('sleep_hours', 'N/A')}h"
                    
                    with st.expander(title):
                        valid_group = group[group["menu_name"].notna()].copy()
                        if not valid_group.empty:
                            display_df = valid_group[["category", "menu_name", "rpe", "purpose", "time_seconds", "distance", "weight", "reps", "sets"]].copy()
                            display_df.columns = ["カテゴリー", "メニュー", "RPE", "意図", "ベスト(秒)", "距離", "重量", "回数", "セット"]
                            st.dataframe(display_df.fillna(""), hide_index=True, use_container_width=True)
                        else:
                            st.write("※練習メニューなし")
            else:
                st.warning("この試合の直前14日間の練習記録がありません。")
    else:
        st.info("分析可能な試合記録がありません。")
