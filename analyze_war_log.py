import bs4
from bs4 import BeautifulSoup
import re
import pandas as pd
import folium
from folium import plugins
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import os

# ---------------------------------------------------------
# 設定
# ---------------------------------------------------------
# 【重要】ここに解析したいファイル名をすべて列挙してください
INPUT_FILES = ['test.html', 'test2.html'] 

OUTPUT_MAP = 'war_map_combined.html' # 出力する地図ファイル名

# 色定義
COUNTRY_COLORS = {
    'Iraq': 'darkred',
    'Belarus': 'green',
    'Sudan': 'orange',
    'Egypt': 'purple',
    'Argentina': 'blue',
    'Balkan Union': 'cadetblue',
    'Romania': 'pink',
    'Finland': 'lightblue',
    'Iceland': 'lightgreen',
    'Brazil': 'darkgreen',
    'Kazakhstan': 'beige',
    'Unknown': 'gray'
}

def get_color(country_name):
    return COUNTRY_COLORS.get(country_name, 'black')

# ---------------------------------------------------------
# 1. 複数HTMLファイルの読み込みと解析
# ---------------------------------------------------------
all_casualties = [] # 全ファイルの損失データ
all_map_events = [] # 全ファイルの地図イベント

print(f"対象ファイル: {INPUT_FILES}")

for file_path in INPUT_FILES:
    if not os.path.exists(file_path):
        print(f"警告: ファイルが見つかりません -> {file_path}")
        continue

    print(f"\nProcessing: {file_path} ...")
    with open(file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, 'html.parser')
    articles = soup.find_all('div', class_='newspaper_article')
    
    print(f"  -> {len(articles)} 件の記事を解析")

    for article in articles:
        body = article.find('div', class_='newspaper_body')
        if not body: continue
        
        paragraphs = body.find_all('p')
        for p in paragraphs:
            text = p.get_text().strip()
            
            # --- 日時取得 ---
            date_span = p.find('span', class_='event_time')
            date_str = date_span.get_text().strip() if date_span else "Unknown"
            
            # 日付ごとの集計用に「日 29」のようなパートを抽出
            # 例: "日 29 04:49:01" -> "日 29"
            day_label = "Unknown Day"
            if len(date_str.split()) >= 2:
                day_label = f"{date_str.split()[0]} {date_str.split()[1]}"

            # ソート用キー (マップの時系列描画用)
            sort_key = 0
            time_match = re.search(r'(\d+)\s+(\d{2}):(\d{2}):(\d{2})', date_str)
            if time_match:
                d, h, m, s = map(int, time_match.groups())
                sort_key = d * 86400 + h * 3600 + m * 60 + s
            
            # =========================================================
            # A. 損失データ (Casualties)
            # =========================================================
            if "lost:" in text:
                country_links = p.find_all(class_='func_country_link')
                victim = country_links[0].get_text().strip() if country_links else "Unknown"
                
                match = re.search(r'lost:\s*(\d+)\s*(.+)', text)
                if match:
                    all_casualties.append({
                        'Day': day_label, # 日付集計用
                        'FullDate': date_str,
                        'Country': victim,
                        'Unit': match.group(2).strip(),
                        'Count': int(match.group(1))
                    })

            # =========================================================
            # B. 地図データ (Combat / Occupy)
            # =========================================================
            prov_link = p.find('span', attrs={'data-prov-name': True})
            if prov_link:
                location_name = prov_link['data-prov-name']
                attacker_unit = "Unknown Unit"
                attacker_country = "Unknown"
                event_type = None
                popup_desc = text

                # --- B-1: 撃破 (ピン表示対象) ---
                if "destroyed by" in text:
                    event_type = 'combat'
                    
                    # 【変更点】 ポップアップ文言の整形
                    # "destroyed by" を除去し、[地名]: [残りの文] にする
                    parts = text.split("destroyed by")
                    if len(parts) > 1:
                        # " the 4th Infantry Division..." のような残りの部分
                        remainder = parts[1].strip()
                        # 末尾のピリオド除去（見た目のため）
                        if remainder.endswith('.'): remainder = remainder[:-1]
                        # "the" で始まっていたら除去（任意）
                        if remainder.lower().startswith("the "): remainder = remainder[4:]
                        
                        popup_desc = f"<b>{location_name}</b>: {remainder}"
                    else:
                        popup_desc = f"<b>{location_name}</b>: {text}"

                    # 加害者情報の抽出 (正規表現 + フォールバック)
                    regex_combat = r'destroyed by (?:the )?(.+?) \(([^)]+)\)'
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
                            if text.find(c_links[0].get_text().strip()) > text.find("destroyed by"):
                                attacker_country = c_links[0].get_text().strip()
                                attacker_unit = "Enemy Forces"

                # --- B-2: 占領 (軌跡用) ---
                elif "occupied" in text:
                    event_type = 'occupy'
                    # 占領も同様にポップアップを短くするならここを調整
                    popup_desc = f"<b>{location_name}</b>: Occupied"
                    
                    regex_occupy = r'(?:^|\s)(.+?) \(([^)]+)\) has occupied'
                    match = re.search(regex_occupy, text)
                    if match:
                        attacker_unit = match.group(1).strip()
                        attacker_country = match.group(2).strip()
                    else:
                        c_links = p.find_all(class_='func_country_link')
                        if c_links:
                            attacker_country = c_links[0].get_text().strip()
                            attacker_unit = "Occupying Force"

                if event_type:
                    all_map_events.append({
                        'sort_key': sort_key,
                        'date_display': date_str,
                        'location': location_name,
                        'popup_text': popup_desc,
                        'country': attacker_country,
                        'unit_name': attacker_unit,
                        'type': event_type
                    })

# 全データを時系列順にソート（地図の線を描くため）
all_map_events.sort(key=lambda x: x['sort_key'])

# ---------------------------------------------------------
# 2. 集計レポート出力 (日付ごと + 合計)
# ---------------------------------------------------------
print("\n" + "="*60)
print("【集計レポート】")
print("="*60)

if all_casualties:
    df_cas = pd.DataFrame(all_casualties)

    # 日付(Day)の一覧を取得してソート
    unique_days = sorted(df_cas['Day'].unique())

    # --- A. 日付ごとの集計 ---
    for day in unique_days:
        print(f"\n>>> 日付: {day} の集計")
        df_day = df_cas[df_cas['Day'] == day]
        
        # 国別・兵種別
        summary_day = df_day.groupby(['Country', 'Unit'])['Count'].sum().reset_index()
        summary_day = summary_day.sort_values(by=['Country', 'Count'], ascending=[True, False])
        print(summary_day.to_string(index=False))
        
        # 国別合計のみ（簡易表示）
        # print("-" * 20)
        # print(df_day.groupby('Country')['Count'].sum().sort_values(ascending=False))

    # --- B. 総合計 (Grand Total) ---
    print("\n" + "="*60)
    print("【総合計 (Grand Total)】全期間")
    print("="*60)
    
    grand_summary = df_cas.groupby(['Country', 'Unit'])['Count'].sum().reset_index()
    grand_summary = grand_summary.sort_values(by=['Country', 'Count'], ascending=[True, False])
    print(grand_summary.to_string(index=False))

    print("\n[国別 損失総数]")
    print(df_cas.groupby('Country')['Count'].sum().sort_values(ascending=False))

else:
    print("損失データが見つかりませんでした。")

# ---------------------------------------------------------
# 3. 地図生成 (一枚のマップに統合)
# ---------------------------------------------------------
print("\n" + "="*60)
print("【地図生成】")
print(f"全イベント数: {len(all_map_events)}")
print("座標を取得中...")
print("="*60)

geolocator = Nominatim(user_agent="war_map_multi_v1")
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

# ユニークな場所を先に検索
unique_locations = set(e['location'] for e in all_map_events)
for loc in unique_locations:
    get_lat_lon(loc)

m = folium.Map(location=[35.0, 20.0], zoom_start=3)
unit_paths = {}

for event in all_map_events:
    coords = get_lat_lon(event['location'])
    if not coords: continue
    
    # 経路データ蓄積
    unit_id = f"{event['unit_name']} ({event['country']})"
    if unit_id not in unit_paths:
        unit_paths[unit_id] = {'coords': [], 'color': get_color(event['country'])}
    unit_paths[unit_id]['coords'].append(coords)
    
    # ピン表示 (Combatのみ)
    if event['type'] == 'combat':
        # ポップアップ: 日時 + 整形済みテキスト
        popup_content = f"""
        <div style="width:250px; font-family:sans-serif;">
            <strong style="color:gray; font-size:0.9em;">{event['date_display']}</strong><br>
            <div style="margin-top:5px; font-size:1em;">{event['popup_text']}</div>
        </div>
        """
        icon_color = get_color(event['country'])
        
        folium.Marker(
            location=coords,
            popup=folium.Popup(popup_content, max_width=300),
            tooltip=f"{event['country']}",
            icon=folium.Icon(color=icon_color, icon='crosshairs', prefix='fa')
        ).add_to(m)

# 線の描画
print("\n経路を描画中...")
for unit_id, data in unit_paths.items():
    points = data['coords']
    if len(points) > 1:
        folium.PolyLine(
            locations=points,
            color=data['color'],
            weight=3,
            opacity=0.7,
            tooltip=unit_id
        ).add_to(m)
        folium.CircleMarker(points[0], radius=3, color=data['color'], fill=True).add_to(m)
        folium.CircleMarker(points[-1], radius=3, color=data['color'], fill=True).add_to(m)

# 凡例
legend_html = '''
     <div style="position: fixed; 
     bottom: 30px; left: 30px; width: 160px; height: auto; 
     border:2px solid grey; z-index:9999; font-size:14px;
     background-color:rgba(255,255,255,0.9); padding: 10px; border-radius: 5px;">
     <b>Attacker Country</b><br>
'''
sorted_colors = sorted(COUNTRY_COLORS.items(), key=lambda x: x[0])
for country, color in sorted_colors:
    if country == 'Unknown': continue
    legend_html += f'<i class="fa fa-circle" style="color:{color}"></i> {country}<br>'
legend_html += '</div>'
m.get_root().html.add_child(folium.Element(legend_html))

m.save(OUTPUT_MAP)
print(f"\n完了しました: {OUTPUT_MAP}")