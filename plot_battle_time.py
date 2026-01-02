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
TARGET_ATTACKER_COUNTRY = 'Romania'

# 2. ゲームスピード (1倍速なら 1, 4倍速なら 4)
GAME_SPEED = 4

# 3. 時間変換の基準点 (現実時間とゲーム内時間の対応ペア)
#    ゲーム内の「何日目の何時」が、現実の「いつ」だったかを指定します。
#    例: ゲーム内の 20日目 13:00:00 が、現実の 2025年12月23日 15:00:00 だった場合
REFERENCE_REAL_TIME_STR = "2025-12-23 15:00:00"  # 現実の日時 (YYYY-MM-DD HH:MM:SS)
REFERENCE_GAME_DAY      = 20                     # ゲーム内日数
REFERENCE_GAME_TIME_STR = "13:00:00"             # ゲーム内時刻 (HH:MM:SS)

# 4. 解析対象のフォルダ設定 (analyze_war_log.py と同じ設定)
TARGET_DIR = "data" 
FILE_PATTERN = "*.html"

# =========================================================

def parse_game_total_seconds(day_str, time_str):
    """ゲーム内の '日' と 'HH:MM:SS' を、ゲーム開始(0日目00:00:00)からの総秒数に変換"""
    try:
        day = int(day_str)
        h, m, s = map(int, time_str.split(':'))
        # 1日は86400秒
        return day * 86400 + h * 3600 + m * 60 + s
    except ValueError:
        return None

def get_real_time_from_game_time(game_day_str, game_time_str, ref_real_dt, ref_game_total_sec, speed):
    """ゲーム時間を現実時間に変換する"""
    current_game_total_sec = parse_game_total_seconds(game_day_str, game_time_str)
    if current_game_total_sec is None:
        return None
    
    # 基準点とのゲーム内時間の差分（秒）
    diff_game_seconds = current_game_total_sec - ref_game_total_sec
    
    # 現実世界での経過時間（秒） = ゲーム内差分 / スピード
    diff_real_seconds = diff_game_seconds / speed
    
    # 現実時間に加算
    return ref_real_dt + timedelta(seconds=diff_real_seconds)

def main():
    # パスの構築
    files_path = os.path.join(TARGET_DIR, FILE_PATTERN)
    input_files = glob.glob(files_path)
    
    if not input_files:
        print(f"エラー: 指定されたフォルダ '{TARGET_DIR}' にファイルが見つかりません。")
        return

    # 基準時間の計算準備
    try:
        ref_real_dt = datetime.strptime(REFERENCE_REAL_TIME_STR, "%Y-%m-%d %H:%M:%S")
        ref_game_total_sec = parse_game_total_seconds(str(REFERENCE_GAME_DAY), REFERENCE_GAME_TIME_STR)
    except ValueError as e:
        print(f"設定エラー: 時間のフォーマットを確認してください。\n{e}")
        return

    print(f"解析対象国: {TARGET_ATTACKER_COUNTRY}")
    print(f"解析ファイル数: {len(input_files)}")
    
    combat_times = [] # (datetimeオブジェクト) のリスト

    # 正規表現: "destroyed by [Unit] ([Country])" のパターン
    # HTMLタグが除去されたテキストに対して適用します
    # 例: "destroyed by the 5th Tank Division (Romania)" -> Group 1: Romania
    regex_attacker = re.compile(r'destroyed by .+? \((.+?)\)')

    for file_path in input_files:
        print(f"読み込み中: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f, 'html.parser')
        except Exception as e:
            print(f"ファイル読み込み失敗: {e}")
            continue

        # 記事のループ
        articles = soup.find_all('div', class_='newspaper_article')
        for article in articles:
            body = article.find('div', class_='newspaper_body')
            if not body: continue
            
            paragraphs = body.find_all('p')
            for p in paragraphs:
                text = p.get_text().strip()
                
                # "destroyed by" が含まれるかチェック
                if "destroyed by" in text or "により撃破されました" in text:
                    
                    # 攻撃国の抽出
                    match = regex_attacker.search(text)
                    if match:
                        attacker_country = match.group(1).strip()
                        
                        # ユーザー指定の国と一致するか確認
                        if attacker_country == TARGET_ATTACKER_COUNTRY:
                            
                            # 日時の抽出
                            # <span class="event_time">日 20 13:09:41</span>
                            date_span = p.find('span', class_='event_time')
                            if date_span:
                                date_str = date_span.get_text().strip()
                                # "日 20 13:09:41" から数字を抜き出す
                                time_match = re.search(r'(\d+)\s+(\d{2}):(\d{2}):(\d{2})', date_str)
                                if time_match:
                                    g_day = time_match.group(1)
                                    g_h, g_m, g_s = time_match.group(2), time_match.group(3), time_match.group(4)
                                    g_time_str = f"{g_h}:{g_m}:{g_s}"
                                    
                                    # 現実時間に変換
                                    real_dt = get_real_time_from_game_time(
                                        g_day, g_time_str, 
                                        ref_real_dt, ref_game_total_sec, 
                                        GAME_SPEED
                                    )
                                    
                                    if real_dt:
                                        combat_times.append(real_dt)
                                        # デバッグ用出力
                                        # print(f"Found: Game Day {g_day} {g_time_str} -> Real {real_dt}")

    # 集計結果のプロット
    if not combat_times:
        print("条件に一致する戦闘データが見つかりませんでした。")
        print("・国名が正しいか (ログの表記通りか)")
        print("・対象ファイルに 'destroyed by' のログが含まれているか")
        print("を確認してください。")
        return

    print(f"\n抽出された戦闘イベント数: {len(combat_times)}")

    # プロット用にデータを加工
    # 日付を無視して、00:00 ~ 23:59 の数値(float: 13.5 = 13:30)に変換
    hours_of_day = []
    for dt in combat_times:
        # 時間 + 分/60 + 秒/3600
        val = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
        hours_of_day.append(val)

    # グラフ描画
    plt.figure(figsize=(10, 6))
    
    # 散布図でプロット (Y軸はランダムにして重なりを防ぐか、あるいは全て1にして分布を見る)
    # ここでは見やすくするために、Y軸はすべて1とし、透明度を設定して濃淡で頻度を見ます
    # あるいはヒストグラムの方が見やすい場合が多いですが、今回は「プロットする」ため散布図風にします
    # 少し上下に散らして(ジッター)重なりを見やすくします
    import random
    y_values = [1.0 + random.uniform(-0.1, 0.1) for _ in range(len(hours_of_day))]
    
    plt.scatter(hours_of_day, y_values, alpha=0.5, color='red', label='Combat Event')
    
    plt.title(f"Activity Time Distribution (Real Time): {TARGET_ATTACKER_COUNTRY}")
    plt.xlabel("Hour of Day (Real Time)")
    plt.ylabel("Events (Jittered)")
    
    # X軸の設定 (0時から24時)
    plt.xlim(0, 24)
    plt.xticks(range(0, 25, 1)) # 1時間刻み
    plt.grid(True, which='both', axis='x', linestyle='--', alpha=0.7)
    
    # Y軸の目盛りは意味がないので消す
    plt.yticks([])

    plt.tight_layout()
    output_img = "combat_time_distribution.png"
    plt.savefig(output_img)
    print(f"グラフを保存しました: {output_img}")
    plt.show()

if __name__ == "__main__":
    main()