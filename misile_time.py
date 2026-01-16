import math

# --- 設定値 ---
x1 = 6269
y1 = 3357

x2 = 6009
y2 = 4586

speed = 35        # ミサイルの速度（距離/分）
aa_range = 50    # 敵の対空範囲
aa_trigger = 4    # 敵が対空を行う分の1の位 (4, 14, 24...)
buffer_time = 2   # 対空後、何分待ってから突入するか

# --- 計算処理 ---

# 1. 全体の距離を求める
total_distance = math.hypot(x2 - x1, y2 - y1)

# 2. 「安全に飛行できる距離」を求める（全体の距離 - 対空範囲）
# ※ここが重要：着弾までの時間ではなく、対空圏の「フチ」に着くまでの時間を計算します
safe_distance = total_distance - aa_range

if safe_distance < 0:
    print("警告：すでに射程内です！即時着弾します。")
    safe_flight_time = 0
else:
    # 3. 安全圏を飛んでいる時間（ゲーム内時間）
    safe_flight_time = safe_distance / speed

# 4. 防空圏突入の目標タイム（1の位）
# 例：4分に対空なら、4 + 2 = 6分のタイミングでラインを越えたい
target_entry_digit = (aa_trigger + buffer_time) % 10

# 5. 発射すべきタイミング（1の位）を逆算
# 目標突入時刻 - 移動時間 = 発射時刻
# 10で割った余りを使うことで「分の1の位」を求めます
launch_trigger_digit = (target_entry_digit - safe_flight_time) % 10

# 分と秒に変換（表示用）
trigger_min = int(launch_trigger_digit)
trigger_sec = int((launch_trigger_digit - trigger_min) * 60)

# --- 結果出力 ---
print("-" * 30)
print(f"全距離: {total_distance:.2f}")
print(f"全飛行時間：{total_distance/speed:.2f}")
print(f"安全飛行時間（対空圏外）: {safe_flight_time:.2f} 分")
print(f"対空圏突入までのタイムラグ: {safe_flight_time:.2f} 分")
print("-" * 30)
print(f"【結論】")
print(f"ゲーム内時間の「分の1の位」が")
print(f"『 {launch_trigger_digit:.2f} 』 の時に発射してください。")
print(f"（例： {trigger_min}分 {trigger_sec:02d}秒、 {10+trigger_min}分 {trigger_sec:02d}秒 ...）")