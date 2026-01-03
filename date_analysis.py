from datetime import datetime, timedelta

class GameTimeVerifier:
    def __init__(self):
        self.data_points = []
        self.TARGET_SPEED = 4.0  # 想定している倍率

    def _game_time_to_seconds(self, day, time_str):
        """ ゲーム内日時（日数+時刻）を総秒数に変換 """
        try:
            parts = list(map(int, time_str.split(':')))
            h = parts[0]
            m = parts[1]
            s = parts[2] if len(parts) > 2 else 0
            return (day * 86400) + (h * 3600) + (m * 60) + s
        except Exception as e:
            print(f"変換エラー: {day}日 {time_str} -> {e}")
            return None

    def _format_seconds_to_time(self, seconds):
        """ 秒数を「D日 HH:MM:SS」形式の文字列に変換 """
        is_negative = seconds < 0
        seconds = abs(int(seconds))
        
        d = seconds // 86400
        h = (seconds % 86400) // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        
        sign = "-" if is_negative else "+"
        if d > 0:
            return f"{sign}{d}日 {h:02}:{m:02}:{s:02}"
        else:
            return f"{sign}{h:02}:{m:02}:{s:02}"

    def add_point(self, real_time_str, game_day, game_time_str):
        """ 測定データを追加 """
        fmt = "%Y-%m-%d %H:%M:%S"
        try:
            r_time = datetime.strptime(real_time_str, fmt)
            g_seconds = self._game_time_to_seconds(game_day, game_time_str)
            
            if g_seconds is not None:
                self.data_points.append({
                    'real': r_time,
                    'game_seconds': g_seconds,
                    'label_day': game_day,
                    'label_time': game_time_str
                })
        except ValueError as e:
            print(f"日時フォーマットエラー: {e}")

    def verify(self):
        if not self.data_points:
            print("データがありません。")
            return

        # 日時順にソート
        sorted_points = sorted(self.data_points, key=lambda x: x['real'])
        
        # 最初のデータを基準点（スタート）とする
        start_point = sorted_points[0]
        
        print(f"{'='*85}")
        print(f" 基準点: 現実 {start_point['real']} | ゲーム {start_point['label_day']}日目 {start_point['label_time']}")
        print(f"{'='*85}")
        print(f"{'現実時刻':^20} | {'ゲーム現在時刻':^16} | {'本来あるべき時刻':^16} | {'ズレ (実際-本来)':^18}")
        print(f"{'-'*85}")

        for i, point in enumerate(sorted_points):
            # 基準点からの現実経過時間（秒）
            real_elapsed = (point['real'] - start_point['real']).total_seconds()
            
            # 本来進んでいるはずのゲーム内秒数 (現実経過 * 4倍)
            expected_progress = real_elapsed * self.TARGET_SPEED
            
            # 本来あるべきゲーム内の総秒数
            expected_game_total = start_point['game_seconds'] + expected_progress
            
            # 実際のゲーム内の総秒数
            actual_game_total = point['game_seconds']
            
            # 差分計算 (実際 - 本来)
            diff_seconds = actual_game_total - expected_game_total
            
            # --- 表示用データの作成 ---
            
            # 本来あるべき時刻の文字列化
            exp_day = int(expected_game_total // 86400)
            exp_rem = int(expected_game_total % 86400)
            exp_h = exp_rem // 3600
            exp_m = (exp_rem % 3600) // 60
            exp_s = exp_rem % 60
            expected_str = f"{exp_day}日 {exp_h:02}:{exp_m:02}" # 秒は省略

            # 実際の時刻文字列
            actual_str = f"{point['label_day']}日 {point['label_time'][:5]}" # 秒は省略

            # ズレのフォーマット
            diff_str = self._format_seconds_to_time(diff_seconds)
            
            # 基準点（0行目）はズレなしなので別表記でも良いが、そのまま0表示
            if i == 0:
                print(f"{str(point['real'])[5:-3]:^20} | {actual_str:^18} | {'(基準点)':^18} | {'00:00:00':^18}")
            else:
                # 判定コメント（遅れが大きい場合など）
                status = ""
                if diff_seconds < -60: status = " (遅延)"
                elif diff_seconds > 60: status = " (進行過多)"
                
                print(f"{str(point['real'])[5:-3]:^20} | {actual_str:^18} | {expected_str:^18} | {diff_str:<10}{status}")

        print(f"{'='*85}")
        print(" ※ マイナス(-) はゲーム内時間が遅れている（ラグ等）ことを示します。")
        print(" ※ プラス(+) はゲーム内時間が進みすぎていることを示します。")

# --- 実行部分 ---

verifier = GameTimeVerifier()

# 使い方:
# verifier.add_point('現実の日時', ゲーム内日数, 'ゲーム内時刻')

#verifier.add_point('2026-01-02 00:11:00', 37, '23:57:00')

verifier.add_point("2025-12-30 21:31:00", 25, "14:16:00")

verifier.add_point("2025-12-31 20:27:00", 29, "09:03:00")

verifier.add_point("2026-01-01 02:36:00", 30, "09:36:00")

verifier.add_point("2026-01-01 16:19:00", 32, "17:27:00")

verifier.add_point('2026-01-03 14:42:00', 40, '11:02:00')

verifier.add_point("2026-01-03 14:47:00", 40, "11:21:00")

verifier.add_point('2026-01-03 14:52:00', 40, '11:41:00')

verifier.verify()