import bs4
from bs4 import BeautifulSoup
import re
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
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
TARGET_ATTACKER_COUNTRY = 'Iraq'

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

def parse_game_total_seconds(day_str, time_str):
    """ゲーム内の '日' と 'HH:MM:SS' を、ゲーム開始からの総秒数に変換"""
    try:
        day = int(day_str)
        h, m, s = map(int, time_str.split(':'))
        return day * 86400 + h * 3600 + m * 60 + s
    except ValueError:
        return None

def get_real_time_from_game_time(game_day_str, game_time_str, ref_real_dt, ref_game_total_sec, speed):
    """ゲーム時間を現実時間に変換する"""
    current_game_total_sec = parse_game_total_seconds(game_day_str, game_time_str)
    if current_game_total_sec is None:
        return None
    
    diff_game_seconds = current_game_total_sec - ref_game_total_sec
    diff_real_seconds = diff_game_seconds / speed
    return ref_real_dt + timedelta(seconds=diff_real_seconds)

def main():
    files_path = os.path.join(TARGET_DIR, FILE_PATTERN)
    input_files = glob.glob(files_path)
    
    if not input_files:
        print(f"エラー: 指定されたフォルダ '{TARGET_DIR}' にファイルが見つかりません。")
        return

    try:
        ref_real_dt = datetime.strptime(REFERENCE_REAL_TIME_STR, "%Y-%m-%d %H:%M:%S")
        ref_game_total_sec = parse_game_total_seconds(str(REFERENCE_GAME_DAY), REFERENCE_GAME_TIME_STR)
    except ValueError as e:
        print(f"設定エラー: 時間のフォーマットを確認してください。\n{e}")
        return

    print(f"解析対象: 攻撃国='{TARGET_ATTACKER_COUNTRY}', 除外対象={EXCLUDED_VICTIM_COUNTRIES}")
    
    combat_times = []

    # ---------------------------------------------------------
    # 正規表現の定義
    # ---------------------------------------------------------
    # 1. 攻撃側（文末）の国名を抽出
    #    ... destroyed by [Unit] ([Country])
    regex_attacker = re.compile(r'(?:destroyed by|により撃破されました) .+? \((.+?)\)')

    # 2. 被害側（文頭寄り）の国名を抽出
    #    フォーマット: ... [兵種名]([国籍1])([英数字]) has been destroyed by ...
    #    「destroyed by」の直前にある (ID) の、さらに一つ前にある (国名) を狙います。
    #    ※IDがないケースも考慮し、destroyed byの前にある括弧書きを全て取得して判定します。
    
    for file_path in input_files:
        print(f"読み込み中: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f, 'html.parser')
        except Exception as e:
            print(f"ファイル読み込み失敗: {e}")
            continue

        articles = soup.find_all('div', class_='newspaper_article')
        for article in articles:
            body = article.find('div', class_='newspaper_body')
            if not body: continue
            
            paragraphs = body.find_all('p')
            for p in paragraphs:
                text = p.get_text().strip()
                
                # 戦闘ログかチェック
                if "destroyed by" in text or "により撃破されました" in text:
                    
                    # --- A. 攻撃側の判定 ---
                    attacker_match = regex_attacker.search(text)
                    if not attacker_match:
                        continue
                    
                    attacker_country = attacker_match.group(1).strip()
                    if attacker_country != TARGET_ATTACKER_COUNTRY:
                        continue

                    # --- B. 被害側の判定 (Undead除外など) ---
                    # テキストを "destroyed by" (または日本語) で分割して前半部分を解析
                    if "destroyed by" in text:
                        parts = text.split("destroyed by")
                    else:
                        parts = text.split("により撃破されました")
                    
                    victim_part = parts[0]
                    
                    # 前半部分に含まれる (...) をすべて抽出
                    # 例: "The 3rd Unit (Saudi Arabia) (J 3) has been" -> ['Saudi Arabia', 'J 3']
                    brackets = re.findall(r'\((.+?)\)', victim_part)
                    
                    victim_country = "Unknown"
                    if len(brackets) >= 2:
                        # 通常フォーマット: 末尾がID、その一つ前が国名
                        victim_country = brackets[-2].strip()
                    elif len(brackets) == 1:
                        # IDがないなどの例外: 唯一のカッコを国名とみなす
                        victim_country = brackets[0].strip()
                    
                    # 除外リストに含まれていたらスキップ
                    if victim_country in EXCLUDED_VICTIM_COUNTRIES:
                        # print(f"除外しました: {victim_country} (Attacker: {attacker_country})")
                        continue

                    # --- C. 日時の抽出と保存 ---
                    date_span = p.find('span', class_='event_time')
                    if date_span:
                        date_str = date_span.get_text().strip()
                        # "日 20 13:09:41"
                        time_match = re.search(r'(\d+)\s+(\d{2}):(\d{2}):(\d{2})', date_str)
                        if time_match:
                            g_day = time_match.group(1)
                            g_h, g_m, g_s = time_match.group(2), time_match.group(3), time_match.group(4)
                            g_time_str = f"{g_h}:{g_m}:{g_s}"
                            
                            real_dt = get_real_time_from_game_time(
                                g_day, g_time_str, 
                                ref_real_dt, ref_game_total_sec, 
                                GAME_SPEED
                            )
                            if real_dt:
                                combat_times.append(real_dt)

    # ---------------------------------------------------------
    # プロット処理
    # ---------------------------------------------------------
    if not combat_times:
        print("条件に一致する戦闘データが見つかりませんでした。")
        return

    print(f"\n抽出された戦闘イベント数 (Undead除外済み): {len(combat_times)}")

    hours_of_day = []
    for dt in combat_times:
        val = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
        hours_of_day.append(val)

    plt.figure(figsize=(10, 6))
    
    # 散布図 (Y軸に少しばらつきを持たせる)
    import random
    y_values = [1.0 + random.uniform(-0.1, 0.1) for _ in range(len(hours_of_day))]
    
    plt.scatter(hours_of_day, y_values, alpha=0.5, color='red', label='Combat Event')
    
    plt.title(f"Activity Time: {TARGET_ATTACKER_COUNTRY} (Excluding: {', '.join(EXCLUDED_VICTIM_COUNTRIES)})")
    plt.xlabel("Hour of Day (Real Time)")
    plt.ylabel("Events")
    
    plt.xlim(0, 24)
    plt.xticks(range(0, 25, 1))
    plt.yticks([])
    plt.grid(True, which='both', axis='x', linestyle='--', alpha=0.7)

    plt.tight_layout()
    output_img = "combat_time_distribution_filtered.png"
    plt.savefig(output_img)
    print(f"グラフを保存しました: {output_img}")
    plt.show()

if __name__ == "__main__":
    main()