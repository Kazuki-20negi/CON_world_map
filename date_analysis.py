from datetime import datetime

class GameTimeVerifier:
    def __init__(self):
        self.data_points = []

    def _game_time_to_seconds(self, day, time_str):
        """
        ゲーム内の「日数」と「時刻」を、0日目0時からの総秒数に変換します。
        1日 = 24時間 = 86400秒 と仮定します。
        """
        try:
            # 時刻文字列 (HH:MM または HH:MM:SS) を分解
            parts = list(map(int, time_str.split(':')))
            h = parts[0]
            m = parts[1]
            s = parts[2] if len(parts) > 2 else 0
            
            # 総秒数計算
            total_seconds = (day * 86400) + (h * 3600) + (m * 60) + s
            return total_seconds
        except Exception as e:
            print(f"エラー: ゲーム時刻の変換に失敗しました ({day}日目 {time_str}) -> {e}")
            return None

    def add_point(self, real_time_str, game_day, game_time_str):
        """
        データを追加します。
        real_time_str: 現実の日時 '2023-10-27 10:00:00'
        game_day     : ゲーム内の日数 (int) 例: 30
        game_time_str: ゲーム内の時刻 (str) 例: '14:30' または '14:30:00'
        """
        fmt = "%Y-%m-%d %H:%M:%S"
        try:
            r_time = datetime.strptime(real_time_str, fmt)
            g_total_seconds = self._game_time_to_seconds(game_day, game_time_str)
            
            if g_total_seconds is not None:
                self.data_points.append({
                    'real': r_time, 
                    'game_seconds': g_total_seconds,
                    'label': f"{game_day}日目 {game_time_str}" # 表示用
                })
        except ValueError as e:
            print(f"エラー: 現実日時のフォーマットが正しくありません。 {e}")

    def verify(self):
        if len(self.data_points) < 2:
            print("検証には少なくとも2つのデータセットが必要です。")
            return

        # 現実時間順にソート
        sorted_points = sorted(self.data_points, key=lambda x: x['real'])
        
        print(f"{'='*70}")
        print(f"{'区間':^6} | {'現実経過':^10} | {'ゲーム内経過':^14} | {'倍率':^10}")
        print(f"{'-'*70}")

        total_real_delta = 0
        total_game_delta = 0
        
        for i in range(1, len(sorted_points)):
            prev = sorted_points[i-1]
            curr = sorted_points[i]

            # 現実時間の差（秒）
            delta_real = (curr['real'] - prev['real']).total_seconds()
            
            # ゲーム内時間の差（秒）
            delta_game = curr['game_seconds'] - prev['game_seconds']

            if delta_real == 0:
                print(f"区間 {i}: エラー (現実時間が経過していません)")
                continue

            ratio = delta_game / delta_real
            
            # 表示用（分換算）
            r_min = delta_real / 60
            g_min = delta_game / 60
            
            print(f"#{i:<5} | {r_min:>7.1f} 分 | {g_min:>8.1f} 分 (約{g_min/60:.1f}h)| {ratio:>8.2f}倍")

            total_real_delta += delta_real
            total_game_delta += delta_game

        if total_real_delta > 0:
            avg_ratio = total_game_delta / total_real_delta
            print(f"{'='*70}")
            print(f"【全体平均倍率】: {avg_ratio:.4f}倍")
            
            diff = abs(4.0 - avg_ratio)
            if diff < 0.1:
                print(">> 判定: おおむね「4倍速」です。")
            else:
                print(f">> 判定: 4倍速から {diff:.4f} ズレています。")
        print(f"{'='*70}")

# --- 実行部分 ---

verifier = GameTimeVerifier()

# 使い方:
# verifier.add_point('現実の日時', ゲーム内日数, 'ゲーム内時刻')

# 例: 現実の10:00に、ゲーム内は 30日目の 06:00 だった
verifier.add_point('2026-01-02 00:11:00', 37, '23:57:00')

# 例: 現実で1時間経過(11:00)。ゲーム内は4時間進んで 30日目の 10:00 になるはず
verifier.add_point('2026-01-03 14:42:00', 40, '11:02:00')

# 例: 現実でさらに1日経過(翌日11:00)。
# 4倍速ならゲーム内は4日進んで、34日目の 10:00 になっているはず
#verifier.add_point('2024-01-02 11:00:00', 34, '10:00:00')

verifier.verify()