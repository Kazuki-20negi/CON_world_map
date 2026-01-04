import bs4
from bs4 import BeautifulSoup
import re
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from datetime import datetime, timedelta
import os
import glob

# =========================================================
# [ユーザー設定エリア]
# 実行前にここを自分の環境・目的に合わせて書き換えてください
# =========================================================

# 1. 絞り込みたい攻撃側の国名 (ログ内の表記と一致させる必要があります)
#    例: 'Germany', 'Romania', 'Saudi Arabia', 'ドイツ' など
TARGET_ATTACKER_COUNTRY = 'Sudan'
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
    
    # 時系列順にソートしておく
    combat_times.sort()
    return combat_times

def analyze_and_plot(combat_times):
    if not combat_times:
        print("データが見つかりませんでした。")
        return

    # 時間を 0.0 ~ 24.0 の数値に変換
    hours = np.array([t.hour + t.minute/60.0 + t.second/3600.0 for t in combat_times])
    n = len(hours)

    print("\n" + "="*40)
    print("【アクティブ時間帯 時系列フロー解析】")
    print("="*40)
    print(f"サンプル数 : {n}")
    print(f"期間       : {combat_times[0].strftime('%Y-%m-%d %H:%M')} ~ {combat_times[-1].strftime('%Y-%m-%d %H:%M')}")
    print("-" * 40)

    # グラフ描画設定
    fig, ax1 = plt.subplots(figsize=(10, 8))

    # --- 1. 背景ヒストグラム (右軸: 頻度) ---
    ax2 = ax1.twinx()
    ax2.hist(hours, bins=24, range=(0, 24), color='gray', alpha=0.15, edgecolor='none', label='Total Frequency')
    ax2.set_ylabel('Event Frequency (Histogram)', color='gray')
    ax2.tick_params(axis='y', labelcolor='gray')
    # ヒストグラムの上限を少し余裕持たせて、散布図の邪魔にならないようにする
    ax2.set_ylim(0, ax2.get_ylim()[1] * 1.2)

    # --- 2. 時系列散布図 (左軸: 日付) ---
    # Y軸を日付にするため、plot_dateやscatterを使うが、単純なscatterだと数値扱いになるので注意が必要
    # matplotlibでは日付を内部的にfloatで扱っているため、そのまま渡してyaxis_date()でフォーマットする
    
    ax1.scatter(hours, combat_times, color='red', s=50, alpha=0.8, edgecolors='black', label='Combat Event')
    
    # Y軸を日付フォーマットに設定
    ax1.yaxis_date()
    date_format = mdates.DateFormatter('%m/%d') # 月/日 (必要なら %H:%M も追加可)
    ax1.yaxis.set_major_formatter(date_format)
    
    # 「上が古いデータ、下が新しいデータ」にするためY軸を反転
    # 反転前: 下が古い(小)、上が新しい(大) -> invert -> 上が古い、下が新しい
    ax1.invert_yaxis()
    
    ax1.set_xlabel('Hour of Day (Real Time)')
    ax1.set_ylabel('Date (Older -> Newer)')
    ax1.set_title(f'Timeline of Combat Activities: {TARGET_ATTACKER_COUNTRY}')
    
    # X軸の設定 (0時~24時)
    ax1.set_xlim(0, 24)
    ax1.set_xticks(np.arange(0, 25, 1))
    ax1.grid(True, axis='x', linestyle='--', alpha=0.6)
    
    # グリッド (Y軸の日付グリッドも見やすくする)
    ax1.grid(True, axis='y', linestyle='-', alpha=0.3)

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    data = load_data()
    analyze_and_plot(data)