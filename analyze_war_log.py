import bs4
from bs4 import BeautifulSoup
import re
import pandas as pd
import folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import os
import unicodedata

# ---------------------------------------------------------
# 設定
# ---------------------------------------------------------
# 解析したいファイル名をリストに追加してください
INPUT_FILES = [
                'test.html', "test2.html", "test3.html", "test30.html",
                "test31.html", "test32.html", "test33.html",
               ]
OUTPUT_MAP = 'war_map_con_wiki.html'

# 除外リスト
EXCLUDED_COUNTRIES = ['Undead', 'アンデッド', 'AI', 'Rogue State', '反乱軍']

# =========================================================
# 【翻訳辞書】 Conflict of Nations Wiki準拠
# =========================================================
TRANSLATION_DICT = {
    # --- 国名 (Countries) は長いカタカナは半角 ---
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
    'Korea': '朝鮮', 'Uruguay': 'ウルグアイ',

    # --- 歩兵 (Infantry) ---
    'Motorized Infantry': '自動車化歩兵',
    'Mechanized Infantry': '機械化歩兵',
    'Naval Infantry': '海兵隊',
    'Airborne Infantry': '空挺歩兵', 
    'Special Forces': '特殊部隊',
    'National Guard': '州兵',
    'Mercenary': '傭兵',

    # --- 装甲車 (Armored) ---
    'Combat Recon Vehicle': '戦闘偵察車',
    'Armored Fighting Vehicle': '装甲戦闘車',
    'Amphibious Combat Vehicle': '水陸両用戦闘車',
    'Main Battle Tank': '主力戦車',
    'Tank Destroyer': '駆逐戦車',
    
    # --- 支援 (Support) ---
    'Towed Artillery': '榴弾砲',
    'Mobile Artillery': '自走砲',
    'Multiple Rocket Launcher': '多連装ﾛｹｯﾄﾗﾝﾁｬｰ',
    'Mobile Anti-Air Vehicle': '自走対空砲',
    'Mobile SAM Launcher': 'SAM',
    'Theater Defense System': '戦域防衛ｼｽﾃﾑ',
    'Mobile Radar': '地上レーダー',

    # --- ヘリコプター (Helicopters) ---
    'Helicopter Gunship': '武装ﾍﾘｺﾌﾟﾀｰ',
    'Attack Helicopter': '攻撃ﾍﾘｺﾌﾟﾀｰ',
    'ASW Helicopter': '対潜ﾍﾘｺﾌﾟﾀｰ',
    'Transport Helicopter': '輸送ﾍﾘｺﾌﾟﾀｰ', 

    # --- 戦闘機 (Fighters) ---
    'Air Superiority Fighter': '制空戦闘機',
    'Strike Fighter': '打撃戦闘機',
    'UAV': 'UAV',
    'Naval Patrol Aircraft': '哨戒機',
    'AWACS': '早期警戒管制機',
    'Stealth Air Superiority Fighter': 'ｽﾃﾙｽ制空',
    'Stealth Strike Fighter': 'ｽﾃﾙｽ打撃',

    # --- 爆撃機 (Heavy) ---
    'Heavy Bomber': '重爆撃機',
    'Stealth Bomber': 'ｽﾃﾙｽ爆撃機',

    # --- 海軍 (Naval) ---
    'Corvette': 'コルベット',
    'Frigate': 'フリゲート',
    'Destroyer': '駆逐艦',
    'Cruiser': '巡洋艦',
    'Aircraft Carrier': '航空母艦',
    
    # --- 潜水艦 (Submarines) ---
    'Attack Submarine': '攻撃型潜水艦',
    'Ballistic Missile Submarine': '弾道ﾐｻｲﾙ潜水艦',

    # --- 将校 (Officers) ---
    'Infantry Officer': '歩兵将校',
    'Tank Commander': '戦車指揮官', 
    'Air Ace': '空軍将校',
    'Naval Veteran': '海軍将校',
    'Submarine Commander': '潜水艦指揮官',
    'Rotor Commander': '回転翼機指揮官', 
    
    # --- シーズン ---
    'Elite Satellite': '精鋭人工衛星', 'Elite Drone Operator': 'ﾄﾞﾛｰﾝｵﾍﾟﾚｰﾀｰ',
    'Elite Attack Aircraft': "精鋭攻撃機", 'Elite Railgun':'レールガン',
    'Elite AIP Submarine': '精鋭潜水艦',

    # --- その他・キーワード (Keywords) ---
    'Division': '師団', 'Brigade': '旅団', 'Battalion': '大隊',
    'Regiment': '連隊', 'Squadron': '飛行隊', 'Flotilla': '戦隊',
    'Wing': '航空団', 'Group': '軍集団',
    'Unit': '部隊', 'Army': '軍',
    'Missile': 'ミサイル', 'Warhead': '弾頭',
    'Conventional': '通常', 'Chemical': '化学', 'Nuclear': '核',
    'ICBM': 'ICBM', 'Cruise': '巡航'
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

AVAILABLE_COLORS = [
    'red', 'blue', 'green', 'purple', 'orange', 'darkred',
    'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue',
    'darkpurple', 'pink', 'lightblue', 'lightgreen', 'black', 'gray'
]
country_color_map = {}

def get_dynamic_color(country_name):
    if country_name not in country_color_map:
        color_index = len(country_color_map) % len(AVAILABLE_COLORS)
        country_color_map[country_name] = AVAILABLE_COLORS[color_index]
    return country_color_map[country_name]
def get_display_width(text):
    """文字列の表示幅を計算（全角2、半角1）"""
    width = 0
    for c in str(text):
        if unicodedata.east_asian_width(c) in 'FWA':
            width += 2
        else:
            width += 1
    return width

def print_aligned_table(df, cols):
    """データフレームを日本語対応の左揃えで綺麗に出力する"""
    if df.empty:
        return

    # 各列の最大幅を計算
    col_widths = {}
    for col in cols:
        max_w = get_display_width(col)
        for val in df[col]:
            w = get_display_width(val)
            if w > max_w:
                max_w = w
        col_widths[col] = max_w + 2  # 余裕を持たせる（2スペース）

    # ヘッダー出力
    header_line = ""
    for col in cols:
        val = str(col)
        padding = col_widths[col] - get_display_width(val)
        header_line += val + " " * padding
    print(header_line)
    print("-" * get_display_width(header_line))

    # データ行出力
    for _, row in df.iterrows():
        line = ""
        for col in cols:
            val = str(row[col])
            padding = col_widths[col] - get_display_width(val)
            line += val + " " * padding
        print(line)
# ---------------------------------------------------------
# 1. 解析とデータ抽出
# ---------------------------------------------------------
all_casualties = [] 
all_map_events = [] 

print(f"対象ファイル: {INPUT_FILES}")

for file_path in INPUT_FILES:
    if not os.path.exists(file_path):
        print(f"警告: ファイルが見つかりません -> {file_path}")
        continue

    with open(file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, 'html.parser')
    articles = soup.find_all('div', class_='newspaper_article')
    
    print(f"[{file_path}] {len(articles)} 件の記事を解析中...")

    for article in articles:
        body = article.find('div', class_='newspaper_body')
        if not body: continue
        
        paragraphs = body.find_all('p')
        for p in paragraphs:
            text = p.get_text().strip()
            
            # --- 日時取得 ---
            date_span = p.find('span', class_='event_time')
            date_str = date_span.get_text().strip() if date_span else "Unknown"
            day_label = "Unknown Day"
            if len(date_str.split()) >= 2:
                day_label = f"{date_str.split()[0]} {date_str.split()[1]}"

            sort_key = 0
            time_match = re.search(r'(\d+)\s+(\d{2}):(\d{2}):(\d{2})', date_str)
            if time_match:
                d, h, m, s = map(int, time_match.groups())
                sort_key = d * 86400 + h * 3600 + m * 60 + s
            
            # --- A. 損失データ ---
            if "lost" in text or "を失いました" in text:
                country_links = p.find_all(class_='func_country_link')
                raw_victim = country_links[0].get_text().strip() if country_links else "Unknown"
                victim_translated = translate(raw_victim)

                if raw_victim in EXCLUDED_COUNTRIES or victim_translated in EXCLUDED_COUNTRIES:
                    continue

                match = re.search(r'(?:lost:?|を失いました)\s*(\d+)\s*(.+)', text)
                if match:
                    raw_unit = match.group(2).strip()
                    if raw_unit.endswith('.'): raw_unit = raw_unit[:-1]
                    # 【over除去】
                    if " over " in raw_unit:
                        raw_unit = raw_unit.split(" over ")[0]

                    unit_translated = translate(raw_unit)
                    all_casualties.append({
                        'Day': day_label, 'Country': victim_translated,
                        'Unit': unit_translated, 'Count': int(match.group(1))
                    })

            # --- B. 地図データ ---
            prov_link = p.find('span', attrs={'data-prov-name': True})
            if prov_link:
                location_name = prov_link['data-prov-name']
                attacker_country = "Unknown"
                attacker_unit = "Unknown Unit"
                event_type = None
                popup_desc = text

                key_destroyed = ["destroyed by", "により撃破されました", "壊滅しました"]
                key_occupied = ["occupied", "を占領しました"]

                if any(k in text for k in key_destroyed):
                    event_type = 'combat'
                    clean_text = text
                    for k in key_destroyed:
                        if k in text:
                            parts = text.split(k)
                            if len(parts) > 1:
                                remainder = parts[1].strip()
                                if remainder.lower().startswith("the "): remainder = remainder[4:]
                                clean_text = remainder
                            break
                    clean_text = translate(clean_text)
                    popup_desc = f"<b>{location_name}</b>: {clean_text}"

                    regex_combat = r'(?:destroyed by|により撃破されました) (?:the )?(.+?) \(([^)]+)\)'
                    match = re.search(regex_combat, text)
                    if match:
                        attacker_unit = match.group(1).strip()
                        attacker_country = match.group(2).strip()
                    else:
                        c_links = p.find_all(class_='func_country_link')
                        if len(c_links) >= 2:
                            attacker_country = c_links[-1].get_text().strip()
                            attacker_unit = "Enemy Forces"
                        elif len(c_links) == 1:
                             if text.find(c_links[0].get_text().strip()) > 10:
                                attacker_country = c_links[0].get_text().strip()
                                attacker_unit = "Enemy Forces"

                elif any(k in text for k in key_occupied):
                    event_type = 'occupy'
                    popup_desc = f"<b>{location_name}</b>: 占領 (Occupied)"
                    regex_occupy = r'(?:^|\s)(.+?) \(([^)]+)\) (?:has occupied|を占領しました)'
                    match = re.search(regex_occupy, text)
                    if match:
                        attacker_unit = match.group(1).strip()
                        attacker_country = match.group(2).strip()
                    else:
                        c_links = p.find_all(class_='func_country_link')
                        if c_links:
                            attacker_country = c_links[0].get_text().strip()
                            attacker_unit = "Occupying Force"

                attacker_country_jp = translate(attacker_country)
                
                if attacker_country in EXCLUDED_COUNTRIES or attacker_country_jp in EXCLUDED_COUNTRIES:
                    continue

                if event_type:
                    all_map_events.append({
                        'sort_key': sort_key,
                        'date_display': date_str,
                        'location': location_name,
                        'popup_text': popup_desc,
                        'country': attacker_country_jp, 
                        'unit_name': translate(attacker_unit),
                        'type': event_type
                    })

all_map_events.sort(key=lambda x: x['sort_key'])

# ---------------------------------------------------------
# 2. 集計レポート
# ---------------------------------------------------------
print("\n" + "="*30)
print("【死亡数集計レポート】")
print("="*30)

if all_casualties:
    df_cas = pd.DataFrame(all_casualties)
    unique_days = sorted(df_cas['Day'].unique())
    for day in unique_days:
        print(f"\n>>> 日付: {day}")
        df_day = df_cas[df_cas['Day'] == day]
        summary_day = df_day.groupby(['Country', 'Unit'])['Count'].sum().reset_index()
        summary_day = summary_day.sort_values(by=['Country', 'Count'], ascending=[True, False])
        print_aligned_table(summary_day, ['Country', 'Unit', 'Count'])

    print("\n" + "-"*30)
    print("【総合計】")
    grand_summary = df_cas.groupby(['Country', 'Unit'])['Count'].sum().reset_index()
    grand_summary = grand_summary.sort_values(by=['Country', 'Count'], ascending=[True, False])
    print_aligned_table(grand_summary, ['Country', 'Unit', 'Count'])
else:
    print("損失データなし")

# ---------------------------------------------------------
# 3. 地図生成 (レイヤー機能追加版)
# ---------------------------------------------------------
print("\n" + "="*60)
print("【地図生成】")
print(f"イベント数: {len(all_map_events)}")
print("座標取得中...")

geolocator = Nominatim(user_agent="war_map_interactive_v1")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1.1)
location_cache = {}

def get_lat_lon(loc_name):
    if loc_name in location_cache: return location_cache[loc_name]
    try:
        loc = geocode(loc_name)
        if loc:
            location_cache[loc_name] = (loc.latitude, loc.longitude)
            print(f"OK: {loc_name}")
            return (loc.latitude, loc.longitude)
        else:
            print(f"NG: {loc_name}")
            return None
    except:
        return None

# ユニークな場所検索
unique_locations = set(e['location'] for e in all_map_events)
for loc in unique_locations:
    get_lat_lon(loc)

m = folium.Map(location=[35.0, 20.0], zoom_start=3)

# 国ごとのレイヤーグループを作成
country_layers = {}  # { 'CountryName': FeatureGroup }

unit_paths = {}

for event in all_map_events:
    coords = get_lat_lon(event['location'])
    if not coords: continue
    
    country_name = event['country']
    current_color = get_dynamic_color(country_name)

    # レイヤーグループがなければ作成して地図に追加
    if country_name not in country_layers:
        fg = folium.FeatureGroup(name=country_name)
        country_layers[country_name] = fg
        fg.add_to(m)
    
    # ユニット経路データ蓄積
    unit_id = f"{event['unit_name']} ({country_name})"
    if unit_id not in unit_paths:
        unit_paths[unit_id] = {'coords': [], 'color': current_color, 'country': country_name}
    unit_paths[unit_id]['coords'].append(coords)
    
    # ピンは対応する国のレイヤーに追加
    if event['type'] == 'combat':
        popup_content = f"""
        <div style="width:250px; font-family:sans-serif;">
            <strong style="color:gray; font-size:0.9em;">{event['date_display']}</strong><br>
            <div style="margin-top:5px;">{event['popup_text']}</div>
        </div>
        """
        folium.Marker(
            location=coords,
            popup=folium.Popup(popup_content, max_width=300),
            tooltip=f"{country_name}",
            icon=folium.Icon(color=current_color, icon='crosshairs', prefix='fa')
        ).add_to(country_layers[country_name])

# 線の描画 (対応する国のレイヤーに追加)
for unit_id, data in unit_paths.items():
    points = data['coords']
    c_name = data['country']
    
    if len(points) > 1 and c_name in country_layers:
        folium.PolyLine(
            locations=points,
            color=data['color'],
            weight=3,
            opacity=0.7,
            tooltip=unit_id
        ).add_to(country_layers[c_name])
        
        folium.CircleMarker(points[0], radius=3, color=data['color'], fill=True).add_to(country_layers[c_name])
        folium.CircleMarker(points[-1], radius=3, color=data['color'], fill=True).add_to(country_layers[c_name])

# レイヤーコントロール (右上メニュー) を追加
# これにより、ユーザーは国ごとに表示/非表示を切り替えられます
folium.LayerControl().add_to(m)

# 凡例 (左下の固定表示)
legend_html = '''
     <div style="position: fixed; 
     bottom: 30px; left: 30px; width: 160px; height: auto; 
     border:2px solid grey; z-index:9999; font-size:14px;
     background-color:rgba(255,255,255,0.9); padding: 10px; border-radius: 5px;">
     <b>Active Countries</b><br>
'''
for country, color in sorted(country_color_map.items()):
    legend_html += f'<i class="fa fa-circle" style="color:{color}"></i> {country}<br>'
legend_html += '</div>'
m.get_root().html.add_child(folium.Element(legend_html))

m.save(OUTPUT_MAP)
print(f"\n完了: {OUTPUT_MAP}")
print("ブラウザで地図を開き、右上のアイコンから表示したい国を選択してください。")