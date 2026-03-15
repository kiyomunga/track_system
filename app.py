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
mode = st.sidebar.radio("モード選択", ["🏃‍♂️ 選手モード（記録確認）", "📝 マネージャーモード（管理）", "📱 練習日誌モード（入力）", "📊 アナリティクス（分析）"])

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

# 🟩🟩🟩 モード3：練習日誌モード（10.70秒へのデータ蓄積） 🟩🟩🟩
elif mode == "📱 練習日誌モード（入力）":
    st.title("📱 練習日誌 ＆ メニュー入力")
    st.info("日々のコンディションと練習メニューを記録し、10.70秒への相関を分析します。")

    selected_user = st.selectbox("選手を選択（あなた）", user_names)
    user_id = user_dict[selected_user]

    # 🌟 魔法の機能：メニュー数を一時記憶（Session State）して動的に増やす・減らす
    if "menu_count" not in st.session_state:
        st.session_state.menu_count = 1

    def add_menu():
        st.session_state.menu_count += 1
        
    def remove_menu():
        if st.session_state.menu_count > 1: # 1個未満には減らせないようにする安全装置
            st.session_state.menu_count -= 1

    with st.form("practice_form"):
        st.subheader("1. 本日のコンディション（親データ）")
        col1, col2 = st.columns(2)
        with col1:
            p_date = st.date_input("日付", datetime.today())
            sleep = st.number_input("睡眠時間 (時間)", min_value=0.0, max_value=24.0, value=7.5, step=0.5)
        with col2:
            rpe = st.slider("RPE (主観的疲労度 1:楽 〜 10:限界)", 1, 10, 5)
            weight = st.number_input("体重 (kg) ※任意", min_value=0.0, value=0.0, step=0.1)
        
        memo = st.text_area("練習全体のメモ・気づき・動きの感覚")

        st.markdown("---")
        st.subheader("2. 練習メニュー（子データ）")
        
        menus_data = []
        for i in range(st.session_state.menu_count):
            st.markdown(f"**【 メニュー {i+1} 】**")
            mc1, mc2, mc3 = st.columns(3)
            with mc1:
                category = st.selectbox("カテゴリー", ["スプリント", "ウエイト", "ジャンプ", "ドリル", "その他"], key=f"cat_{i}")
                menu_name = st.text_input("メニュー名 (例: 60m, ハイクリーン)", key=f"name_{i}")
            with mc2:
                distance = st.number_input("距離(m)", min_value=0.0, value=0.0, key=f"dist_{i}")
                # 🌟 変更：タイムを文字列入力（カンマ区切り）に変更
                time_str = st.text_input("タイム(秒) ※カンマ区切りで複数可", placeholder="例: 7.10, 7.15", key=f"time_{i}")
            with mc3:
                wt = st.number_input("重量(kg)", min_value=0.0, value=0.0, key=f"wt_{i}")
                reps = st.number_input("回数(Reps)", min_value=0, value=0, key=f"reps_{i}")
                sets = st.number_input("セット数", min_value=0, value=0, key=f"sets_{i}")
            
            # 🌟 魔法の処理：カンマ区切りの文字列から「一番速いタイム」を自動計算する
            best_time = None
            if time_str.strip():
                try:
                    # カンマで分割し、空白を消して小数に変換（例: ["7.10", "7.15"] -> [7.1, 7.15]）
                    times_list = [float(t.strip()) for t in time_str.split(",") if t.strip()]
                    if times_list:
                        best_time = min(times_list) # スプリントは値が小さい（速い）方がベスト
                except ValueError:
                    st.error(f"メニュー {i+1} のタイム入力に誤りがあります。数字とカンマのみを使用してください。")
            
            menus_data.append({
                "category": category,
                "menu_name": menu_name,
                "distance": distance if distance > 0 else None,
                "weight": wt if wt > 0 else None,
                "reps": reps if reps > 0 else None,
                "sets": sets if sets > 0 else None,
                "time_seconds": best_time,             # グラフ用のベストタイム
                "times_detail": time_str.strip() if time_str.strip() else None # 全タイムの文字列
            })
            st.markdown("---")

        submitted = st.form_submit_button("💾 今日の練習をデータベースに保存")

    # 🌟 フォームの外に「追加」と「削除」ボタンを横並びで配置
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        st.button("➕ メニューを増やす", on_click=add_menu, use_container_width=True)
    with btn_col2:
        st.button("➖ メニューを減らす", on_click=remove_menu, use_container_width=True)

    if submitted:
        # メニュー名が空欄の行は除外して送信する（安全装置）
        valid_menus = [m for m in menus_data if m["menu_name"].strip() != ""]
        
        payload = {
            "date": p_date.isoformat(),
            "rpe": rpe,
            "sleep_hours": sleep if sleep > 0 else None,
            "body_weight": weight if weight > 0 else None,
            "memo": memo,
            "menus": valid_menus
        }
        
        try:
            res = requests.post(f"{API_URL}/users/{user_id}/practices/", json=payload)
            if res.status_code == 200:
                st.success("✅ 練習記録を保存しました！10.70秒へのデータがまた一つ蓄積されました。")
                st.session_state.menu_count = 1 # 保存成功したら入力欄の数を1に戻す
            else:
                st.error("🚨 保存エラー: データを正しく入力してください。")
        except Exception as e:
            st.error(f"通信エラー: {e}")

# 🟩🟩🟩 モード4：アナリティクス（データ分析） 🟩🟩🟩
elif mode == "📊 アナリティクス（分析）":
    st.title("📊 10.70秒への軌跡（データ分析ダッシュボード）")
    st.info("日々のコンディション（RPE・睡眠）とスプリントタイム・挙上重量の相関を分析します。")

    selected_user = st.selectbox("分析する選手を選択", user_names)
    user_id = user_dict[selected_user]

    res = requests.get(f"{API_URL}/users/{user_id}/practices/analytics", timeout=5)
    
    if res.status_code == 200 and res.json():
        df = pd.DataFrame(res.json())
        df["date"] = pd.to_datetime(df["date"])
        
        # --- 分析1：コンディションとスプリントタイムの相関 ---
        st.subheader("🏃‍♂️ スプリントタイム × コンディション（RPE・睡眠）")
        # タイムが入力されているスプリントのデータだけを抽出
        sprint_df = df[(df["category"] == "スプリント") & (df["time_seconds"].notnull()) & (df["time_seconds"] > 0)]
        
        if not sprint_df.empty:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**疲労度(RPE)とタイムの相関**")
                st.scatter_chart(sprint_df, x="rpe", y="time_seconds", color="menu_name")
            with c2:
                st.markdown("**睡眠時間とタイムの相関**")
                st.scatter_chart(sprint_df, x="sleep_hours", y="time_seconds", color="menu_name")
            st.caption("※点が下にある（タイムが短い）ほど良い記録です。自分にとって最適な睡眠時間やRPEの『スイートスポット』を探しましょう。")
        else:
            st.warning("分析可能なスプリントのデータ（タイムあり）がまだありません。")

        st.markdown("---")

        # --- 分析2：ウエイトトレーニングの成長推移 ---
        st.subheader("🏋️‍♂️ ウエイトトレーニング（最大挙上重量の推移）")
        weight_df = df[(df["category"] == "ウエイト") & (df["weight"].notnull()) & (df["weight"] > 0)]
        
        if not weight_df.empty:
            # 日付ごとの最大重量をメニュー別に集計してグラフ化
            max_weight_df = weight_df.groupby(["date", "menu_name"])["weight"].max().reset_index()
            pivot_df = max_weight_df.pivot(index="date", columns="menu_name", values="weight")
            st.line_chart(pivot_df)
        else:
            st.warning("分析可能なウエイトトレーニングのデータがまだありません。")
            
        st.markdown("---")
        
        # --- 分析3：練習日誌アーカイブ（履歴一覧） ---
        st.subheader("📖 練習日誌アーカイブ")
        
        # 日付の降順（新しい順）でソート
        df_sorted = df.sort_values("date", ascending=False)
        
        # 日付ごとにグループ化して表示
        for date, group in df_sorted.groupby("date", sort=False):
            first_row = group.iloc[0]
            date_str = date.strftime('%Y-%m-%d')
            
            # アコーディオンのタイトル（日付とコンディション概要）
            title = f"📅 {date_str} | RPE: {first_row['rpe']} | 睡眠: {first_row['sleep_hours']}h"
            
            with st.expander(title):
                # メモがあれば強調表示
                if 'memo' in first_row and pd.notna(first_row['memo']) and str(first_row['memo']).strip() != "":
                    st.info(f"**📝 感覚・メモ:** {first_row['memo']}")
                
                # メニューをテーブル形式で綺麗に表示するため、列を整理
                display_df = group[["category", "menu_name", "time_seconds", "times_detail", "distance", "weight", "reps", "sets"]].copy()
                display_df.columns = ["カテゴリー", "メニュー", "ベスト(秒)", "全タイム", "距離(m)", "重量(kg)", "回数", "セット"]
                
                # 見栄えを良くするために、数値がない部分（NaN）を空白文字に変換
                display_df = display_df.fillna("")
                
                # 行番号（インデックス）を隠してスッキリ表示
                st.dataframe(display_df, hide_index=True, use_container_width=True)
            
    else:
        st.info("練習データがまだ登録されていないか、通信エラーです。")

