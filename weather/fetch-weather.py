#!/usr/bin/env python3
"""
Camino del Norte – Weather Tracker
Fetches historical climate averages from Open-Meteo archive API
for each stage town on the planned walking date (calendar date averaged
across 2019-2023), plus live forecasts for any stages within 16 days.
Outputs docs/weather.html for GitHub Pages.

Usage: python3 fetch-weather.py
"""

import json
import time
import sys
import os
from datetime import date, timedelta, datetime, timezone
from urllib.request import urlopen
from urllib.error import URLError

# ── Config ──────────────────────────────────────────────────────
START_DATE    = date(2027, 6, 1)
CLIMATE_YEARS = [2019, 2020, 2021, 2022, 2023]
TODAY         = date.today()
FORECAST_DAYS = 16  # Open-Meteo free tier

STAGES = [
    ("Irún",                   43.3381, -1.7889,  0),
    ("San Sebastián",          43.3182, -1.9817,  1),
    ("Zarautz",                43.2848, -2.1711,  2),
    ("Deba",                   43.2963, -2.3524,  3),
    ("Markina-Xemein",         43.2673, -2.4963,  4),
    ("Gernika",                43.3114, -2.6808,  5),
    ("Bilbao",                 43.2634, -2.9348,  6),
    ("Pobeña",                 43.3445, -3.1250,  7),
    ("Castro Urdiales",        43.3688, -3.2156,  8),
    ("Laredo",                 43.4089, -3.4317,  9),
    ("Güemes",                 43.4560, -3.6349, 10),
    ("Santa Cruz de Bezana",   43.4426, -3.9024, 11),
    ("Santillana del Mar",     43.3873, -4.1066, 12),
    ("Comillas",               43.3856, -4.2923, 13),
    ("Colombres",              43.3748, -4.5402, 14),
    ("Llanes",                 43.4211, -4.7562, 15),
    ("San Esteban de Leces",   43.4645, -5.1103, 16),
    ("Villaviciosa",           43.4817, -5.4356, 17),
    ("Gijón",                  43.5322, -5.6610, 18),
    ("San Martín de Laspra",   43.5672, -5.9743, 19),
    ("Soto de Luiña",          43.5619, -6.2309, 20),
    ("Cadavedo",               43.5447, -6.3882, 21),
    ("Piñera",                 43.5451, -6.6683, 22),
    ("Tapia de Casariego",     43.5702, -6.9439, 23),
    ("Vilela",                 43.5115, -7.1026, 24),
    ("Mondoñedo",              43.4286, -7.3638, 25),
    ("Castromaior",            43.3448, -7.5431, 26),
    ("Baamonde",               43.1763, -7.7566, 27),
    ("Sobrado dos Monxes",     43.0705, -7.9811, 28),
    ("Arzúa",                  42.9297, -8.1608, 29),
    ("O Pedrouzo",             42.9046, -8.3625, 30),
    ("Santiago de Compostela", 42.8769, -8.5442, 31),
]

# WMO weather code descriptions
WMO_CODES = {
    0: ("Clear sky", "☀️"),
    1: ("Mainly clear", "🌤️"),
    2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Foggy", "🌫️"),
    48: ("Icy fog", "🌫️"),
    51: ("Light drizzle", "🌦️"),
    53: ("Drizzle", "🌦️"),
    55: ("Heavy drizzle", "🌧️"),
    61: ("Slight rain", "🌧️"),
    63: ("Rain", "🌧️"),
    65: ("Heavy rain", "🌧️"),
    71: ("Slight snow", "🌨️"),
    73: ("Snow", "🌨️"),
    75: ("Heavy snow", "❄️"),
    80: ("Rain showers", "🌦️"),
    81: ("Rain showers", "🌧️"),
    82: ("Violent showers", "⛈️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm + hail", "⛈️"),
    99: ("Thunderstorm + hail", "⛈️"),
}

def get_wmo(code):
    if code is None:
        return ("—", "")
    c = int(code)
    return WMO_CODES.get(c, (f"Code {c}", "🌡️"))

def fetch_json(url, retries=3):
    for attempt in range(retries):
        try:
            with urlopen(url, timeout=30) as r:
                return json.loads(r.read())
        except Exception as e:
            if attempt < retries - 1:
                print(f"  ⚠️  Attempt {attempt+1} failed ({e}), retrying...", file=sys.stderr)
                time.sleep(2 ** attempt)  # 1s, 2s backoff
            else:
                print(f"  ⚠️  All retries failed: {e}", file=sys.stderr)
                return None

def fetch_historical(lat, lon, month, day):
    """Fetch the same calendar date across CLIMATE_YEARS and return averages."""
    all_tmax, all_tmin, all_rain, all_wind = [], [], [], []

    for year in CLIMATE_YEARS:
        try:
            d = date(year, month, day)
        except ValueError:
            continue  # skip Feb 29 in non-leap years
        url = (
            f"https://archive-api.open-meteo.com/v1/archive"
            f"?latitude={lat}&longitude={lon}"
            f"&start_date={d}&end_date={d}"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max"
            f"&timezone=Europe/Madrid"
        )
        data = fetch_json(url)
        if data and "daily" in data:
            daily = data["daily"]
            def first(key):
                vals = daily.get(key, [None])
                return vals[0] if vals else None
            tmax = first("temperature_2m_max")
            tmin = first("temperature_2m_min")
            rain = first("precipitation_sum")
            wind = first("windspeed_10m_max")
            if tmax is not None: all_tmax.append(tmax)
            if tmin is not None: all_tmin.append(tmin)
            if rain is not None: all_rain.append(rain)
            if wind is not None: all_wind.append(wind)
        time.sleep(0.4)

    def avg(lst):
        return round(sum(lst) / len(lst), 1) if lst else None

    rain_prob = round(100 * sum(1 for r in all_rain if r and r > 1.0) / len(CLIMATE_YEARS)) if all_rain else None

    return {
        "tmax": avg(all_tmax),
        "tmin": avg(all_tmin),
        "rain_mm": avg(all_rain),
        "rain_prob": rain_prob,
        "wind_kmh": avg(all_wind),
        "source": "historical",
        "years": f"{CLIMATE_YEARS[0]}–{CLIMATE_YEARS[-1]}",
    }

def fetch_forecast(lat, lon, target_date):
    """Fetch live forecast for a specific date (only works within 16 days)."""
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&start_date={target_date}&end_date={target_date}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,windspeed_10m_max,weathercode"
        f"&timezone=Europe/Madrid"
    )
    data = fetch_json(url)
    if not data or "daily" not in data:
        return None
    daily = data["daily"]
    def first(key):
        vals = daily.get(key, [None])
        return vals[0] if vals else None
    return {
        "tmax":      first("temperature_2m_max"),
        "tmin":      first("temperature_2m_min"),
        "rain_mm":   first("precipitation_sum"),
        "rain_prob": first("precipitation_probability_max"),
        "wind_kmh":  first("windspeed_10m_max"),
        "wmo_code":  first("weathercode"),
        "source":    "forecast",
    }

def rain_color(prob):
    if prob is None: return "#888"
    if prob >= 70:   return "#e74c3c"
    if prob >= 40:   return "#e67e22"
    if prob >= 20:   return "#f1c40f"
    return "#27ae60"

def rain_label(prob):
    if prob is None: return "—"
    if prob >= 70:   return "High"
    if prob >= 40:   return "Moderate"
    if prob >= 20:   return "Low"
    return "Unlikely"

def temp_bar(tmin, tmax):
    """Mini SVG temperature bar."""
    if tmin is None or tmax is None:
        return "—"
    low = max(0, min(tmin, 40))
    high = max(0, min(tmax, 40))
    scale = 100 / 40
    x1 = low * scale
    w  = (high - low) * scale
    return (
        f'<svg width="100" height="12" style="vertical-align:middle">'
        f'<rect x="0" y="3" width="100" height="6" rx="3" fill="#2a2a2a"/>'
        f'<rect x="{x1:.0f}" y="3" width="{max(w,4):.0f}" height="6" rx="3" fill="#e67e22"/>'
        f'</svg> {tmin:.0f}°–{tmax:.0f}°C'
    )

# ── Main: fetch all stages ───────────────────────────────────────
print("Fetching weather data for 32 stages...", file=sys.stderr)

results = []
for name, lat, lon, day_index in STAGES:
    walking_date = START_DATE + timedelta(days=day_index)
    days_away    = (walking_date - TODAY).days
    is_forecast  = 0 <= days_away <= FORECAST_DAYS

    print(f"  Day {day_index:02d} {name} ({walking_date}) — {'FORECAST' if is_forecast else 'HISTORICAL'}",
          file=sys.stderr)

    if is_forecast:
        wx = fetch_forecast(lat, lon, walking_date)
        if wx is None:
            wx = fetch_historical(lat, lon, walking_date.month, walking_date.day)
    else:
        wx = fetch_historical(lat, lon, walking_date.month, walking_date.day)

    results.append({
        "day":          day_index,
        "name":         name,
        "date":         str(walking_date),
        "days_away":    days_away,
        "lat":          lat,
        "lon":          lon,
        "wx":           wx,
    })
    time.sleep(0.2)

# ── Build HTML ───────────────────────────────────────────────────
now_str = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")

# Summary stats
total_rainy = sum(1 for r in results if r["wx"] and (r["wx"].get("rain_prob") or 0) >= 40)
max_rain_day = max(results, key=lambda r: r["wx"].get("rain_prob") or 0) if results else None
avg_rain_prob = round(sum((r["wx"].get("rain_prob") or 0) for r in results) / len(results))

rows_html = ""
for r in results:
    wx       = r["wx"] or {}
    tmax     = wx.get("tmax")
    tmin     = wx.get("tmin")
    rain_mm  = wx.get("rain_mm")
    rain_p   = wx.get("rain_prob")
    wind     = wx.get("wind_kmh")
    source   = wx.get("source", "historical")
    wmo_code = wx.get("wmo_code")
    wmo_desc, wmo_emoji = get_wmo(wmo_code) if wmo_code is not None else ("", "")

    days_away = r["days_away"]
    if days_away < 0:
        row_class = "past"
    elif days_away == 0:
        row_class = "today"
    elif source == "forecast":
        row_class = "live"
    else:
        row_class = "historical"

    source_badge = (
        '<span class="badge-live">📡 Live</span>'
        if source == "forecast"
        else f'<span class="badge-hist">📊 Avg {wx.get("years","")}</span>'
    )

    rain_col = rain_color(rain_p)
    rain_lbl = rain_label(rain_p)
    rain_disp = f'<span style="color:{rain_col};font-weight:600">{rain_lbl}</span>'
    if rain_p is not None:
        rain_disp += f' <small style="color:#888">({rain_p}%)</small>'

    rain_mm_disp = f"{rain_mm:.1f}mm" if rain_mm is not None else "—"
    wind_disp    = f"{wind:.0f} km/h" if wind is not None else "—"
    temp_disp    = temp_bar(tmin, tmax)
    cond_disp    = f"{wmo_emoji} {wmo_desc}" if wmo_emoji else "—"

    rows_html += f"""
        <tr class="{row_class}">
          <td class="day-num">Day {r['day']}</td>
          <td class="town-name">{r['name']}</td>
          <td class="date-col">{r['date']}</td>
          <td>{temp_disp}</td>
          <td>{rain_disp}</td>
          <td>{rain_mm_disp}</td>
          <td>{wind_disp}</td>
          <td>{cond_disp if cond_disp != '— ' else '—'}</td>
          <td>{source_badge}</td>
        </tr>"""

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Camino del Norte – Weather Tracker</title>
  <style>
    :root {{
      --bg:      #0f1117;
      --surface: #1a1d27;
      --border:  #2a2d3a;
      --text:    #e8eaf0;
      --muted:   #8892a4;
      --accent:  #4f9cf9;
      --green:   #27ae60;
      --orange:  #e67e22;
      --red:     #e74c3c;
      --yellow:  #f1c40f;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 14px;
      line-height: 1.5;
    }}
    header {{
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      padding: 24px 32px;
    }}
    header h1 {{ font-size: 22px; font-weight: 700; margin-bottom: 4px; }}
    header p  {{ color: var(--muted); font-size: 13px; }}
    .summary {{
      display: flex;
      gap: 16px;
      padding: 20px 32px;
      flex-wrap: wrap;
    }}
    .stat {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px 20px;
      min-width: 160px;
    }}
    .stat-val  {{ font-size: 28px; font-weight: 700; }}
    .stat-label{{ font-size: 12px; color: var(--muted); margin-top: 2px; }}
    .table-wrap {{
      overflow-x: auto;
      padding: 0 32px 40px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 820px;
    }}
    th {{
      text-align: left;
      padding: 10px 12px;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: .06em;
      color: var(--muted);
      border-bottom: 1px solid var(--border);
      white-space: nowrap;
    }}
    td {{
      padding: 10px 12px;
      border-bottom: 1px solid var(--border);
      vertical-align: middle;
      white-space: nowrap;
    }}
    tr:hover td {{ background: rgba(255,255,255,.03); }}
    tr.past td  {{ opacity: .45; }}
    tr.today td {{ background: rgba(79,156,249,.08); }}
    tr.today .day-num {{ color: var(--accent); font-weight: 700; }}
    .day-num    {{ color: var(--muted); font-size: 12px; width: 52px; }}
    .town-name  {{ font-weight: 600; }}
    .date-col   {{ color: var(--muted); font-size: 12px; }}
    .badge-live {{
      background: rgba(39,174,96,.2);
      color: #2ecc71;
      font-size: 11px;
      padding: 2px 7px;
      border-radius: 4px;
      border: 1px solid rgba(39,174,96,.4);
    }}
    .badge-hist {{
      background: rgba(79,156,249,.12);
      color: var(--accent);
      font-size: 11px;
      padding: 2px 7px;
      border-radius: 4px;
      border: 1px solid rgba(79,156,249,.3);
    }}
    .legend {{
      padding: 0 32px 32px;
      color: var(--muted);
      font-size: 12px;
      line-height: 2;
    }}
    .legend span {{ margin-right: 24px; }}
    @media (max-width: 600px) {{
      header, .summary, .table-wrap, .legend {{ padding-left: 16px; padding-right: 16px; }}
      .stat {{ min-width: 130px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>🥾 Camino del Norte – Weather Tracker</h1>
    <p>Irún → Santiago de Compostela &nbsp;·&nbsp; Start date: {START_DATE.strftime('%B %d, %Y')} &nbsp;·&nbsp; Last updated: {now_str}</p>
  </header>

  <div class="summary">
    <div class="stat">
      <div class="stat-val" style="color:var(--accent)">{(START_DATE - TODAY).days}</div>
      <div class="stat-label">Days until start</div>
    </div>
    <div class="stat">
      <div class="stat-val" style="color:var(--orange)">{total_rainy}</div>
      <div class="stat-label">Stages with ≥40% rain chance</div>
    </div>
    <div class="stat">
      <div class="stat-val" style="color:{rain_color(avg_rain_prob)}">{avg_rain_prob}%</div>
      <div class="stat-label">Avg rain probability</div>
    </div>
    <div class="stat">
      <div class="stat-val" style="color:var(--yellow)">
        {max_rain_day['name'].split()[0] if max_rain_day else '—'}
      </div>
      <div class="stat-label">Wettest stage ({(max_rain_day['wx'].get('rain_prob') or 0)}% rain)</div>
    </div>
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th></th>
          <th>Town</th>
          <th>Date</th>
          <th>Temp (min–max)</th>
          <th>Rain chance</th>
          <th>Rainfall</th>
          <th>Wind</th>
          <th>Conditions</th>
          <th>Source</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
  </div>

  <div class="legend">
    <span>🟢 <strong>Unlikely</strong> &lt;20%</span>
    <span>🟡 <strong>Low</strong> 20–39%</span>
    <span>🟠 <strong>Moderate</strong> 40–69%</span>
    <span>🔴 <strong>High</strong> ≥70%</span>
    &nbsp;&nbsp;|&nbsp;&nbsp;
    <span>📡 <strong>Live forecast</strong> — real-time data from Open-Meteo</span>
    <span>📊 <strong>Historical avg</strong> — {CLIMATE_YEARS[0]}–{CLIMATE_YEARS[-1]} averages for this calendar date</span>
  </div>

</body>
</html>
"""

# Write output
os.makedirs("docs", exist_ok=True)
with open("docs/weather.html", "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ Written to docs/weather.html ({len(html):,} bytes)", file=sys.stderr)