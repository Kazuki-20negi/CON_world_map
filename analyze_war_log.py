import bs4
from bs4 import BeautifulSoup
import re
import pandas as pd
import folium
from folium import plugins
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

# ---------------------------------------------------------
# 設定
# ---------------------------------------------------------
INPUT_FILE = 'test.html'           # 解析するHTMLファイル
OUTPUT_MAP = 'war_map_complete.html' # 出力する地図ファイル

# 国ごとのピンの色定義
# Foliumの色: red, blue, green, purple, orange, darkred, lightred, beige, darkblue, darkgreen, cadetblue, darkpurple, white, pink, lightblue, lightgreen, gray, black, lightgray
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
    'Unknown': 'gray'
}

def get_color(country_name):
    """国名から色を取得。定義になければ黒を返す"""
    return COUNTRY_COLORS.get(country_name, 'black')

# ---------------------------------------------------------
# 1. HTML解析とデータ抽出
# ---------------------------------------------------------
print("HTMLファイルを読み込んでいます...")
with open(INPUT_FILE, 'r', encoding='utf-8') as f:
    html_content = f.read()

soup = BeautifulSoup(html_content, 'html.parser')
articles = soup.find_all('div', class_='newspaper_article')

# データ格納用リスト
casualties_data = [] # 集計レポート用（誰が何を失ったか）
map_events = []      # 地図用（移動・戦闘イベント）

print(f"{len(articles)} 件の記事を解析中...")

for article in articles:
    body = article.find('div', class_='newspaper_body')
    if not body:
        continue
    
    paragraphs = body.find_all('p')
    
    for p in paragraphs:
        text = p.get_text().strip()
        
        # --- 共通情報の取得: 日時 ---
        date_span = p.find('span', class_='event_time')
        date_str = date_span.get_text().strip() if date_span else "Unknown"
        
        # ソート用タイムスタンプ（簡易数値化: 日*86400 + 時*3600...）
        sort_key = 0
        time_match = re.search(r'(\d+)\s+(\d{2}):(\d{2}):(\d{2})', date_str)
        if time_match:
            day, hh, mm, ss = map(int, time_match.groups())
            sort_key = day * 86400 + hh * 3600 + mm * 60 + ss
        
        # =========================================================
        # 機能A: 集計レポート用データ抽出 ("lost: [数量] [兵種]")
        # =========================================================
        if "lost:" in text:
            # 損失した国の特定（行内の func_country_link）
            country_links = p.find_all(class_='func_country_link')
            victim_country = country_links[0].get_text().strip() if country_links else "Unknown"
            
            # 正規表現で数量と兵種を抽出
            match = re.search(r'lost:\s*(\d+)\s*(.+)', text)
            if match:
                count = int(match.group(1))
                unit_type = match.group(2).strip()
                
                casualties_data.append({
                    'Date': date_str,
                    'Country': victim_country,
                    'Unit': unit_type,
                    'Count': count
                })

        # =========================================================
        # 機能B: 地図用データ抽出 ("destroyed by" / "occupied")
        # =========================================================
        # 場所の特定 (<span data-prov-name="XXX">)
        prov_link = p.find('span', attrs={'data-prov-name': True})
        
        if prov_link:
            location_name = prov_link['data-prov-name']
            
            # --- パターンB-1: 撃破 (ピンを表示) ---
            if "destroyed by" in text:
                # ポップアップ用に "destroyed by" 以降を切り出し
                split_text = text.split("destroyed by")
                popup_desc = "destroyed by" + split_text[1] if len(split_text) > 1 else text
                
                # 加害ユニットと国名の抽出
                attacker_match = re.search(r'destroyed by the (.+?) \((.+?)\)', text)
                attacker_unit = "Unknown Unit"
                attacker_country = "Unknown"
                
                if attacker_match:
                    attacker_unit = attacker_match.group(1).strip()
                    attacker_country = attacker_match.group(2).strip()
                
                map_events.append({
                    'sort_key': sort_key,
                    'date_display': date_str,
                    'location': location_name,
                    'popup_text': popup_desc,
                    'country': attacker_country,
                    'unit_name': attacker_unit,
                    'type': 'combat'
                })
                
            # --- パターンB-2: 占領 (線を引くための経由地情報) ---
            elif "occupied" in text:
                occ_match = re.search(r'^(.+?) \((.+?)\) has occupied', text)
                if occ_match:
                    attacker_unit = occ_match.group(1).strip()
                    attacker_country = occ_match.group(2).strip()
                    
                    map_events.append({
                        'sort_key': sort_key,
                        'date_display': date_str,
                        'location': location_name,
                        'popup_text': f"Occupied by {attacker_unit}",
                        'country': attacker_country,
                        'unit_name': attacker_unit,
                        'type': 'occupy'
                    })

# 地図イベントを時系列順にソート
map_events.sort(key=lambda x: x['sort_key'])

# ---------------------------------------------------------
# 2. 集計レポートの出力 (コンソール)
# ---------------------------------------------------------
print("\n" + "="*50)
print("【集計レポート】")
print("="*50)

if casualties_data:
    df_cas = pd.DataFrame(casualties_data)
    
    # 1. 国別・兵種別の損失合計
    summary = df_cas.groupby(['Country', 'Unit'])['Count'].sum().reset_index()
    summary = summary.sort_values(by=['Country', 'Count'], ascending=[True, False])
    
    print("\n[国別・兵種別 損失リスト]")
    print(summary.to_string(index=False))
    
    # 2. 国別の損失総数
    total_summary = df_cas.groupby('Country')['Count'].sum().sort_values(ascending=False)
    print("\n[国別 損失ユニット総数]")
    print(total_summary)
else:
    print("損失データ(lost:...)が見つかりませんでした。")

# ---------------------------------------------------------
# 3. 座標取得と地図生成 (Folium)
# ---------------------------------------------------------
print("\n" + "="*50)
print("【地図生成】")
print(f"地図用イベント数: {len(map_events)}")
print("座標を取得中... (数秒～数十秒かかります)")
print("="*50)

geolocator = Nominatim(user_agent="war_map_complete_v3")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1.1)

location_cache = {}

def get_lat_lon(loc_name):
    if loc_name in location_cache:
        return location_cache[loc_name]
    try:
        loc = geocode(loc_name)
        if loc:
            coords = (loc.latitude, loc.longitude)
            location_cache[loc_name] = coords
            print(f"OK: {loc_name}")
            return coords
        else:
            print(f"NG: {loc_name} (Not Found)")
            return None
    except Exception as e:
        print(f"Error: {loc_name} -> {e}")
        return None

# ユニークな場所のみ先に検索
unique_locations = set(e['location'] for e in map_events)
for loc in unique_locations:
    get_lat_lon(loc)

# ベース地図
m = folium.Map(location=[35.0, 20.0], zoom_start=3)

# ユニット経路データ
unit_paths = {}

for event in map_events:
    coords = get_lat_lon(event['location'])
    if not coords:
        continue
    
    # --- 経路データの蓄積 ---
    unit_id = f"{event['unit_name']} ({event['country']})"
    if unit_id not in unit_paths:
        unit_paths[unit_id] = {'coords': [], 'color': get_color(event['country'])}
    unit_paths[unit_id]['coords'].append(coords)
    
    # --- ピンの表示 (Combatのみ) ---
    if event['type'] == 'combat':
        # ポップアップ内容: 日時 + destroyed by ...
        popup_content = f"""
        <div style="width:220px; font-family:sans-serif;">
            <strong style="color:gray;">{event['date_display']}</strong><br>
            <p style="margin-top:5px;">{event['popup_text']}</p>
        </div>
        """
        
        icon_color = get_color(event['country'])
        
        folium.Marker(
            location=coords,
            popup=folium.Popup(popup_content, max_width=250),
            tooltip=f"Battle: {event['unit_name']}",
            icon=folium.Icon(color=icon_color, icon='crosshairs', prefix='fa')
        ).add_to(m)

# --- 線の描画 (ユニット軌跡) ---
print("\nユニットの移動経路を描画中...")
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
        # 始点・終点のマーカー
        folium.CircleMarker(points[0], radius=3, color=data['color'], fill=True).add_to(m)
        folium.CircleMarker(points[-1], radius=3, color=data['color'], fill=True).add_to(m)

# --- 凡例 (Legend) ---
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

# 保存
m.save(OUTPUT_MAP)
print(f"\n完了しました。地図ファイル: {OUTPUT_MAP}")
print("コンソール上の集計レポートも確認してください。")