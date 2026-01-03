import bs4
from bs4 import BeautifulSoup
import re
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
from datetime import datetime, timedelta
import os
import glob
import math

# =========================================================
# [ユーザー設定エリア]
# 実行前にここを自分の環境・目的に合わせて書き換えてください
# =========================================================

# 1. 絞り込みたい攻撃側の国名 (ログ内の表記と一致させる必要があります)
#    例: 'Germany', 'Romania', 'Saudi Arabia', 'ドイツ' など
TARGET_ATTACKER_COUNTRY = 'Egypt'
#Iraq  Egypt  Sudan

# 2. ゲームスピード (1倍速なら 1, 4倍速なら 4)
GAME_SPEED = 4

# 3. 時間変換の基準点 (現実時間とゲーム内時間の対応ペア)
#    ゲーム内の「何日目の何時」が、現実の「いつ」だったかを指定します。
#    例: ゲーム内の 20日目 13:00:00 が、現実の 2025年12月23日 15:00:00 だった場合
REFERENCE_REAL_TIME_STR = "2026-01-02 00:11:00"  # 現実の日時 (YYYY-MM-DD HH:MM:SS)
REFERENCE_GAME_DAY      = 37                     # ゲーム内日数
REFERENCE_GAME_TIME_STR = "23:57:00"             # ゲーム内時刻 (HH:MM:SS)

# 4. 解析対象のフォルダ設定 (analyze_war_log.py と同じ設定)
TARGET_DIR = "data_zombi" 
FILE_PATTERN = "*.html"

# 5. 除外したい被害側の国名リスト
#    攻撃対象がここに該当する場合はプロットしません
EXCLUDED_VICTIM_COUNTRIES = ['Undead', 'アンデッド', 'Rogue State', '反乱軍']

# =========================================================
# =========================================================
# =========================================================

def parse_game_total_seconds(day_str, time_str):
    try:
        day = int(day_str)
        h, m, s = map(int, time_str.split(':'))
        return day * 86400 + h * 3600 + m * 60 + s
    except ValueError:
        return None

def get_real_time_from_game_time(game_day_str, game_time_str, ref_real_dt, ref_game_total_sec, speed):
    current_game_total_sec = parse_game_total_seconds(game_day_str, game_time_str)
    if current_game_total_sec is None: return None
    
    diff_game_seconds = current_game_total_sec - ref_game_total_sec
    diff_real_seconds = diff_game_seconds / speed
    return ref_real_dt + timedelta(seconds=diff_real_seconds)

def load_data():
    files_path = os.path.join(TARGET_DIR, FILE_PATTERN)
    input_files = glob.glob(files_path)
    
    if not input_files:
        print(f"エラー: '{TARGET_DIR}' にファイルが見つかりません。")
        return []

    try:
        ref_real_dt = datetime.strptime(REFERENCE_REAL_TIME_STR, "%Y-%m-%d %H:%M:%S")
        ref_game_total_sec = parse_game_total_seconds(str(REFERENCE_GAME_DAY), REFERENCE_GAME_TIME_STR)
    except Exception as e:
        print(f"設定エラー: {e}")
        return []

    combat_times = []
    regex_attacker = re.compile(r'(?:destroyed by|により撃破されました) .+? \((.+?)\)')

    for file_path in input_files:
        print(f"解析中: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f, 'html.parser')
        except: continue

        articles = soup.find_all('div', class_='newspaper_article')
        for article in articles:
            body = article.find('div', class_='newspaper_body')
            if not body: continue
            
            for p in body.find_all('p'):
                text = p.get_text().strip()
                if "destroyed by" in text or "により撃破されました" in text:
                    # 攻撃国チェック
                    attacker_match = regex_attacker.search(text)
                    if not attacker_match: continue
                    if attacker_match.group(1).strip() != TARGET_ATTACKER_COUNTRY: continue

                    # 被害国チェック (Undead除外)
                    if "destroyed by" in text: parts = text.split("destroyed by")
                    else: parts = text.split("により撃破されました")
                    
                    victim_part = parts[0]
                    brackets = re.findall(r'\((.+?)\)', victim_part)
                    victim_country = "Unknown"
                    if len(brackets) >= 2: victim_country = brackets[-2].strip()
                    elif len(brackets) == 1: victim_country = brackets[0].strip()
                    
                    if victim_country in EXCLUDED_VICTIM_COUNTRIES: continue

                    # 時間抽出
                    date_span = p.find('span', class_='event_time')
                    if date_span:
                        date_str = date_span.get_text().strip()
                        time_match = re.search(r'(\d+)\s+(\d{2}):(\d{2}):(\d{2})', date_str)
                        if time_match:
                            g_day, g_h, g_m, g_s = time_match.group(1), time_match.group(2), time_match.group(3), time_match.group(4)
                            g_time_str = f"{g_h}:{g_m}:{g_s}"
                            real_dt = get_real_time_from_game_time(g_day, g_time_str, ref_real_dt, ref_game_total_sec, GAME_SPEED)
                            if real_dt: combat_times.append(real_dt)
    return combat_times

def analyze_and_plot(combat_times):
    if not combat_times:
        print("データが見つかりませんでした。")
        return

    # 時間を 0.0 ~ 24.0 の数値に変換
    hours = np.array([t.hour + t.minute/60.0 + t.second/3600.0 for t in combat_times])
    n = len(hours)

    # -----------------------------------------------------
    # 1. 円統計 (Circular Statistics)
    # -----------------------------------------------------
    # 時間を角度 (0 ~ 2π) に変換して平均ベクトルを計算
    angles = hours * (2 * np.pi / 24)
    sin_sum = np.sum(np.sin(angles))
    cos_sum = np.sum(np.cos(angles))
    
    # 平均角度
    mean_angle = np.arctan2(sin_sum, cos_sum)
    if mean_angle < 0: mean_angle += 2 * np.pi
    
    # 平均時刻に変換し直す
    mean_hour = mean_angle * (24 / (2 * np.pi))
    mean_time_str = f"{int(mean_hour)}:{int((mean_hour%1)*60):02d}"
    
    # 集中度 R (0:バラバラ ~ 1:一点集中)
    R = np.sqrt(sin_sum**2 + cos_sum**2) / n

    # -----------------------------------------------------
    # 2. KDE (Kernel Density Estimation)
    # -----------------------------------------------------
    # 0時またぎを綺麗に描画するため、データを[-24h, 0h, +24h]の範囲に拡張して推定させる
    hours_extended = np.concatenate([hours - 24, hours, hours + 24])
    
    # 密度推定 (データ数が少ないため bw_method='silverman' を使用)
    kde = stats.gaussian_kde(hours_extended, bw_method='silverman')
    
    # 0～24時の範囲で評価
    x_grid = np.linspace(0, 24, 200)
    kde_values = kde(x_grid)
    
    # ピーク時刻 (最も密度が高い時間)
    peak_idx = np.argmax(kde_values)
    peak_hour = x_grid[peak_idx]
    peak_time_str = f"{int(peak_hour)}:{int((peak_hour%1)*60):02d}"

    # -----------------------------------------------------
    # 結果表示
    # -----------------------------------------------------
    print("\n" + "="*40)
    print("【アクティブ時間帯 推定結果】")
    print("="*40)
    print(f"サンプル数      : {n}")
    print(f"平均活動時刻    : {mean_time_str} (Circular Mean)")
    print(f"活動の集中度(R) : {R:.3f} (0=散乱, 1=集中)")
    print(f"推定ピーク時刻  : {peak_time_str} (最も確率が高い時間)")
    print("-" * 40)

    # プロット
    plt.figure(figsize=(10, 6))
    
    # ヒストグラム (実データ)
    plt.hist(hours, bins=24, range=(0, 24), density=True, alpha=0.3, color='gray', label='Raw Data (Hist)')
    
    # KDE曲線 (推定された傾向)
    # ※3倍データで学習しているためスケーリング補正して表示
    plt.plot(x_grid, kde_values * 3, color='blue', linewidth=2, label='Estimated Trend (KDE)')
    
    # 平均時刻ライン
    plt.axvline(mean_hour, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_time_str}')
    
    plt.xlim(0, 24)
    plt.xticks(np.arange(0, 25, 1))
    plt.xlabel('Hour of Day (Real Time)')
    plt.ylabel('Activity Density')
    plt.title(f'Active Time Analysis: {TARGET_ATTACKER_COUNTRY} (n={n})')
    plt.legend()
    plt.grid(True, alpha=0.5)

    plt.show()

if __name__ == "__main__":
    data = load_data()
    analyze_and_plot(data)