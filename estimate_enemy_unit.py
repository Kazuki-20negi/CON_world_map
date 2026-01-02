import bs4
from bs4 import BeautifulSoup
import re
import pandas as pd
import os
import glob

# =========================================================
# [ユーザー設定エリア]
# =========================================================

# 1. 解析対象のフォルダ
TARGET_DIR = "data_zombi"
FILE_PATTERN = "*.html"

# 2. 解析したい国名リスト
#    空リスト [] にすると、除外対象以外の「全ての国」を表示します。
#    例: TARGET_COUNTRIES = ['Sudan', 'Germany', 'Japan']
TARGET_COUNTRIES = ["Iraq","Egypt","Sudan"] 

# 3. 除外したい国名リスト
EXCLUDED_COUNTRIES = ['Undead', 'アンデッド', 'AI', 'Rogue State', '反乱軍', "Insurgencies"]

# =========================================================
# 【翻訳辞書】
# =========================================================
TRANSLATION_DICT = {
    # --- 国名 ---
    'Great Britain': 'イギリス', 'United Kingdom': 'イギリス',
    'France': 'フランス', 'Germany': 'ドイツ', 'German Empire': 'ドイツ帝国',
    'Austria-Hungary': 'オーストリア=ハンガリー', 'Italy': 'イタリア',
    'Russia': 'ロシア', 'Russian Empire': 'ロシア帝国',
    'Ottoman Empire': 'オスマン帝国', 'Turkey': 'トルコ',
    'Spain': 'スペイン', 'Portugal': 'ポルトガル',
    'Sweden': 'スウェーデン', 'Norway': 'ノルウェー', 'Denmark': 'デンマーク',
    'Finland': 'フィンランド', 'Iceland': 'アイスランド',
    'Poland': 'ポーランド', 'Ukraine': 'ウクライナ',
    'Lithuania': 'リトアニア', 'Latvia': 'ラトビア', 'Estonia': 'エストニア',
    'Romania': 'ルーマニア', 'Bulgaria': 'ブルガリア', 'Greece': 'ギリシャ',
    'Serbia': 'セルビア', 'Albania': 'アルバニア',
    'Egypt': 'エジプト', 'Libya': 'リビア', 'Algeria': 'アルジェリア',
    'Morocco': 'モロッコ', 'Tunisia': 'チュニジア',
    'West Africa': '西アフリカ', 'East Africa': '東アフリカ', 'South Africa': '南アフリカ',
    'Arabia': 'アラビア', 'Syria': 'シリア', 'Iraq': 'イラク', 'Persia': 'ペルシャ',
    'India': 'インド', 'United States': 'アメリカ', 'Canada': 'カナダ',
    'Greenland': 'ｸﾞﾘｰﾝﾗﾝﾄﾞ', 'Brazil': 'ブラジル', 'Argentina': 'アルゼンチン',
    'Caucasus': 'カフカース', 'Kazakhstan': 'カザフスタン', 'Belarus': 'ベラルーシ',
    'Balkan Union': 'ﾊﾞﾙｶﾝ連邦', 'Sudan': 'スーダン', 'Turkmenistan': 'ﾄﾙｸﾒﾆｽﾀﾝ',
    'Mongolia': 'モンゴル', 'China': '中国', 'Japan': '日本', 'Australia': 'オーストラリア',
    'New Zealand': 'ﾆｭｰｼﾞｰﾗﾝﾄﾞ', 'Philippines': 'フィリピン', 'Indonesia': 'インドネシア',
    'Myanmar': 'ミャンマー', 'Thailand': 'タイ', 'Vietnam': 'ベトナム',
    'North Korea': '北朝鮮', 'South Korea': '韓国', 'Colombia': 'コロンビア',
    'Venezuela': 'ベネズエラ', 'Peru': 'ペルー', 'Chile': 'チリ', 'Bolivia': 'ボリビア',
    'Mexico': 'メキシコ', 'Cuba': 'キューバ', 'DR Congo': "コンゴ", 'Cambodia': 'カンボジア',
    'Korea': '朝鮮', 'Uruguay': 'ウルグアイ', "Uzbekistan":"ウズベキスタン", "Mauritania":"モーリタニア",
    "Patagonia":"パタゴニア", "Nigeria":"ナイジェリア", "Bangladesh": "バングラデシュ",
    "Republic of the Congo": "コンゴ共和国", "Papua New Guinea": "パプアニューギニア",
    "Caribbean Coalition": "カリブ連合", "Baltic States": "バルト三国",

    # --- 部隊名 ---
    'Infantry Battalion': '歩兵大隊',
    'Motorized Infantry': '自動車化歩兵', 'Motorized Infantry Battalion': '自動車化歩兵大隊',
    'Mechanized Infantry': '機械化歩兵', 'Mechanized Infantry Battalion': '機械化歩兵大隊',
    'Naval Infantry': '海兵隊', 'Naval Infantry Battalion': '海兵隊大隊',
    'Airborne Infantry': '空挺歩兵', 'Airborne Infantry Battalion': '空挺歩兵大隊',
    'Special Forces': '特殊部隊', 'Special Forces Battalion': '特殊部隊大隊',
    'National Guard': '州兵', 'National Guard Battalion': '州兵大隊', 'Ntl. Guard Division': '州兵師団',
    'Mercenary': '傭兵',
    
    'Combat Recon Vehicle': '戦闘偵察車', 'Combat Recon Vehicle Battalion': '戦闘偵察車大隊',
    'Armored Fighting Vehicle': '装甲戦闘車', 'Armored Fighting Vehicle Battalion': '装甲戦闘車大隊',
    'Amphibious Combat Vehicle': '水陸両用戦闘車', 
    'Main Battle Tank': '主力戦車', 'Main Battle Tank Division': '主力戦車師団', 'Tank Division': '戦車師団',
    'Tank Destroyer': '駆逐戦車', 'Tank Destroyer Division': '駆逐戦車師団',

    'Towed Artillery': '榴弾砲', 'Artillery Division': '砲兵師団',
    'Mobile Artillery': '自走砲', 'Mobile Artillery Division': '自走砲師団',
    'Multiple Rocket Launcher': '多連装ﾛｹｯﾄ', 'Multiple Rocket Launcher Division': '多連装ﾛｹｯﾄ師団',
    'Mobile Anti-Air Vehicle': '自走対空砲', 'Mobile Anti-Air Division': '自走対空砲師団',
    'Mobile SAM Launcher': 'SAM', 'SAM Launcher Division': 'SAM師団',
    'Theater Defense System': 'TDS', 'Theater Defense System Division': 'TDS師団',
    'Mobile Radar': '地上レーダー', 

    'Helicopter Gunship': '武装ヘリ', 'Helicopter Gunship Squadron': '武装ヘリ飛行隊',
    'Attack Helicopter': '攻撃ヘリ', 'Attack Helicopter Squadron': '攻撃ヘリ飛行隊',
    'ASW Helicopter': '対潜ヘリ', 'ASW Helicopter Squadron': '対潜ヘリ飛行隊',
    'Transport Helicopter': '輸送ヘリ', 

    'Air Superiority Fighter': '制空戦闘機', 'Air Superiority Squadron': '制空戦闘機飛行隊',
    'Strike Fighter': '打撃戦闘機', 'Strike Wing': '打撃戦闘機航空団', 'Strike Fighter Squadron': '打撃戦闘機飛行隊',
    'UAV': 'UAV', 
    'Naval Patrol Aircraft': '哨戒機', 'Naval Patrol Squadron': '哨戒機飛行隊',
    'AWACS': '早期警戒管制機',
    'Heavy Bomber': '重爆撃機', 'Bomber Wing': '爆撃航空団',
    'Stealth Air Superiority Fighter': 'ステルス制空', 
    'Stealth Strike Fighter': 'ステルス打撃',
    
    'Corvette': 'コルベット', 
    'Frigate': 'フリゲート', 
    'Destroyer': '駆逐艦', 
    'Cruiser': '巡洋艦', 
    'Aircraft Carrier': '空母',
    'Attack Submarine': '攻撃型潜水艦', 
    'Ballistic Missile Submarine': '弾道ミサイル潜水艦',

    'Military Unit': '部隊(正体不明)', 
    'Undead Horde': 'ゾンビの大群',
    
    'Elite Anti-Air Division': '精鋭対空師団',
    'Elite Infantry Division': '精鋭歩兵師団',
    'Elite Fighter Wing': '精鋭戦闘機航空団',
    'Elite Fighter Squadron': '精鋭戦闘機飛行隊',
    'Drone Operator': 'ドローンオペレーター',
}

def translate(text):
    if not text: return text
    if text in TRANSLATION_DICT:
        return TRANSLATION_DICT[text]
    
    sorted_keys = sorted(TRANSLATION_DICT.keys(), key=len, reverse=True)
    translated_text = text
    for key in sorted_keys:
        if key in translated_text:
            translated_text = translated_text.replace(key, TRANSLATION_DICT[key])
    return translated_text

# =========================================================
# メイン処理
# =========================================================

def get_files():
    files_path = os.path.join(TARGET_DIR, FILE_PATTERN)
    return glob.glob(files_path)

def parse_time(date_str):
    """ '日 36 22:40:06' のような文字列を秒単位の数値(ソート用)に変換 """
    if not date_str: return 0
    match = re.search(r'(\d+)\s+(\d{2}):(\d{2}):(\d{2})', date_str)
    if match:
        day = int(match.group(1))
        h, m, s = map(int, match.groups()[1:])
        return day * 86400 + h * 3600 + m * 60 + s
    return 0

def extract_units(files):
    unit_records = []
    
    # 正規表現パターンの修正
    # ---------------------------------------------------------
    # 解説:
    # 1. (?:The\s+|by\s+the\s+)? 
    #    -> "The " または "by the " が直前にある場合（マッチしなくてもOK）
    # 2. (\d+)
    #    -> 部隊番号 (キャプチャグループ1)
    # 3. (st|nd|rd|th)
    #    -> 序数接尾辞 (キャプチャグループ2)。【ここを必須にすることで単なる数字を除外】
    # 4. \s+
    #    -> 空白
    # 5. ([^(]+?)
    #    -> 兵種名 (キャプチャグループ3)。括弧 "(" が来るまでの文字列（非貪欲マッチ）
    # 6. \s+\(([^)]+)\)
    #    -> 空白 + "(" + 国名(キャプチャグループ4) + ")"
    # ---------------------------------------------------------
    regex_unit = re.compile(r'(?:The\s+|by\s+the\s+)?(\d+)(st|nd|rd|th)\s+([^(]+?)\s+\(([^)]+)\)')

    for file_path in files:
        if not os.path.exists(file_path): continue
        
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                soup = BeautifulSoup(f, 'html.parser')
            except:
                continue

        articles = soup.find_all('div', class_='newspaper_article')
        
        for article in articles:
            body = article.find('div', class_='newspaper_body')
            if not body: continue
            
            paragraphs = body.find_all('p')
            for p in paragraphs:
                text = p.get_text().strip()
                
                date_span = p.find('span', class_='event_time')
                date_str = date_span.get_text().strip() if date_span else "Unknown"
                time_val = parse_time(date_str)

                # 正規表現検索を実行
                matches = regex_unit.finditer(text)
                for m in matches:
                    unit_num_str = m.group(1) # 数字
                    # m.group(2) は接尾辞(thなど)なので使わない
                    unit_name_raw = m.group(3).strip() # 兵種名
                    country_raw = m.group(4).strip() # 国名
                    
                    country_jp = translate(country_raw)
                    unit_name_jp = translate(unit_name_raw)

                    # --- 国フィルタリング ---
                    if country_raw in EXCLUDED_COUNTRIES or country_jp in EXCLUDED_COUNTRIES:
                        continue
                    
                    if TARGET_COUNTRIES:
                        if (country_raw not in TARGET_COUNTRIES) and (country_jp not in TARGET_COUNTRIES):
                            continue

                    unit_records.append({
                        'Country': country_jp,
                        'UnitNumber': int(unit_num_str),
                        'UnitName': unit_name_jp,
                        'TimeVal': time_val,
                        'LastSeen': date_str,
                        'RawText': f"{unit_num_str}{m.group(2)} {unit_name_raw}"
                    })

    return pd.DataFrame(unit_records)

def main():
    input_files = get_files()
    print(f"解析対象ファイル数: {len(input_files)}")
    
    if TARGET_COUNTRIES:
        print(f"絞り込み対象国: {TARGET_COUNTRIES}")
    else:
        print("絞り込みなし（全対象国を表示）")

    df = extract_units(input_files)
    
    if df.empty:
        print("\n該当する部隊情報が見つかりませんでした。")
        return

    # 重複排除: 同じ国・番号なら最新のログを残す
    df_sorted = df.sort_values(by=['Country', 'UnitNumber', 'TimeVal'], ascending=[True, True, False])
    df_unique = df_sorted.drop_duplicates(subset=['Country', 'UnitNumber'], keep='first')

    countries = df_unique['Country'].unique()
    
    print("\n" + "="*50)
    print("【部隊番号による戦力推定リスト (修正版)】")
    print("確認された部隊番号を大きい順に列挙します。")
    print("="*50)

    for country in sorted(countries):
        country_df = df_unique[df_unique['Country'] == country]
        country_df = country_df.sort_values(by='UnitNumber', ascending=False)
        
        max_num = country_df['UnitNumber'].max()
        count = len(country_df)
        
        print(f"\n■ {country} (確認数: {count}, 最大番号: {max_num})")
        print(f"{'番号':<6} | {'現在の部隊名 (推定)':<25} | {'最終確認日時'}")
        print("-" * 60)
        
        for _, row in country_df.iterrows():
            u_num = row['UnitNumber']
            u_name = row['UnitName']
            l_seen = row['LastSeen']
            print(f"#{u_num:<5} | {u_name:<32} | {l_seen}")

if __name__ == "__main__":
    main()