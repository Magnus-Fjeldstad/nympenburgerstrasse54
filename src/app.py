from flask import Flask, render_template_string
from mvg import MvgApi, TransportType
import datetime
from zoneinfo import ZoneInfo
import requests

app = Flask(__name__)

DEFAULT_STATION = "Maillingerstrasse, München"


def weathercode_to_emoji(code):
    # Open-Meteo weather codes: https://open-meteo.com/en/docs
    mapping = {
        0: "☀️",  # Clear sky
        1: "🌤️",  # Mainly clear
        2: "⛅",  # Partly cloudy
        3: "☁️",  # Overcast
        45: "🌫️",  # Fog
        48: "🌫️",  # Depositing rime fog
        51: "🌦️",  # Drizzle: light
        53: "🌦️",  # Drizzle: moderate
        55: "🌦️",  # Drizzle: dense
        61: "🌧️",  # Rain: slight
        63: "🌧️",  # Rain: moderate
        65: "🌧️",  # Rain: heavy
        71: "🌨️",  # Snow fall: slight
        73: "🌨️",  # Snow fall: moderate
        75: "🌨️",  # Snow fall: heavy
        80: "🌦️",  # Rain showers: slight
        81: "🌦️",  # Rain showers: moderate
        82: "🌦️",  # Rain showers: violent
        95: "⛈️",  # Thunderstorm: slight or moderate
        96: "⛈️",  # Thunderstorm with hail: slight
        99: "⛈️",  # Thunderstorm with hail: heavy
    }
    return mapping.get(code, "❓")


def get_weather(lat, lon, hours=12):
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&hourly=temperature_2m,weathercode&forecast_days=2"
    )
    resp = requests.get(url)
    data = resp.json()
    times = data["hourly"]["time"]
    temps = data["hourly"]["temperature_2m"]
    codes = data["hourly"]["weathercode"]
    now = datetime.datetime.now(ZoneInfo("Europe/Berlin"))  # Offset-aware
    weather = []

    for t, temp, code in zip(times, temps, codes):
        dt = datetime.datetime.fromisoformat(t)
        # Konverter UTC → lokal tid
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc).astimezone(
                ZoneInfo("Europe/Berlin")
            )
        if dt >= now:
            weather.append(
                {
                    "tid": dt.strftime("%H:%M"),
                    "temp": temp,
                    "code": code,
                    "emoji": weathercode_to_emoji(code),
                }
            )
        if len(weather) >= hours:
            break
    return weather


def get_weather_next_hour(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m,apparent_temperature,weathercode,precipitation,windspeed_10m"
        f"&forecast_days=1"
    )
    resp = requests.get(url)
    data = resp.json()
    times = data["hourly"]["time"]
    temps = data["hourly"]["temperature_2m"]
    apparent = data["hourly"]["apparent_temperature"]
    codes = data["hourly"]["weathercode"]
    precip = data["hourly"]["precipitation"]
    wind = data["hourly"]["windspeed_10m"]
    now = datetime.datetime.now(ZoneInfo("Europe/Berlin"))
    detailed_weather = []

    for t, temp, app_temp, code, pr, ws in zip(
        times, temps, apparent, codes, precip, wind
    ):
        dt = datetime.datetime.fromisoformat(t)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc).astimezone(
                ZoneInfo("Europe/Berlin")
            )

        # Finn neste hele timen etter "nå"
        if dt > now:
            detailed_weather.append(
                {
                    "tid": f"{now.strftime('%H:%M')} → {dt.strftime('%H:%M')}",
                    "temp": temp,
                    "følt_temp": app_temp,
                    "nedbør": pr,
                    "vind": ws,
                    "code": code,
                    "emoji": weathercode_to_emoji(code),
                }
            )
            break  # bare én time er ønsket

    return detailed_weather


@app.route("/")
def index():
    station = MvgApi.station(DEFAULT_STATION)
    if not station:
        return "Stasjon ikke funnet"

    mvgapi = MvgApi(station["id"])
    departures = mvgapi.departures(limit=15, transport_types=[TransportType.UBAHN])
    print("Departures:", departures)  # Bruk gjerne for logging på Render

    if not departures:
        return "Ingen avganger funnet"

    dep_list = []
    for dep in departures:
        # Konverter avgangstiden til Europe/Berlin
        dt = datetime.datetime.fromtimestamp(dep["time"], tz=ZoneInfo("Europe/Berlin"))
        dep_list.append(
            {
                "line": dep["line"],
                "destination": dep["destination"],
                "tid": dt.strftime("%H:%M"),
            }
        )

    # Værdata (krever ikke endringer, du bruker riktig tidssone allerede)
    weather = get_weather(station["latitude"], station["longitude"], hours=12)
    detailed_weather = get_weather_next_hour(station["latitude"], station["longitude"])
    html = """
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      margin: 0;
      padding: 0;
      background: #f4f6f9;
      color: #333;
    }
    .container {
      max-width: 900px;
      margin: auto;
      padding: 20px;
    }
    h1, h2 {
      text-align: center;
      margin: 30px 0 20px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      background: white;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
      margin-bottom: 30px;
    }
    th, td {
      padding: 12px 8px;
      text-align: center;
      border-bottom: 1px solid #eee;
    }
    th {
      background-color: #0078d7;
      color: white;
      font-weight: 600;
    }
    tr:last-child td {
      border-bottom: none;
    }
    @media (max-width: 700px) {
      .container {
        padding: 10px;
      }
      table, th, td {
        font-size: 14px;
        padding: 6px 4px;
      }
    }
  </style>
</head>
<body>
  <div class="container">

    <h2>Next U-Bahns from {{station}}</h2>
    <table>
      <tr>
        <th>Line</th>
        <th>Destination</th>
        <th>Departure</th>
      </tr>
      {% for dep in departures %}
      <tr>
        <td>{{ dep.line }}</td>
        <td>{{ dep.destination }}</td>
        <td>{{ dep.tid }}</td>
      </tr>
      {% endfor %}
    </table>

    <h2>Weather - Next 12 Hours</h2>
    <table>
      <tr>
        <th>Time</th>
        <th>Temperature (°C)</th>
        <th>Condition</th>
      </tr>
      {% for w in weather %}
      <tr>
        <td>{{ w.tid }}</td>
        <td>{{ w.temp }}</td>
        <td>{{ w.emoji }}</td>
      </tr>
      {% endfor %}
    </table>

    <h2>Detailed Forecast - Next Hour</h2>
    <table>
      <tr>
        <th>Time</th>
        <th>Temperature (°C)</th>
        <th>Feels Like (°C)</th>
        <th>Precipitation (mm)</th>
        <th>Wind (m/s)</th>
        <th>Condition</th>
      </tr>
      {% for w in detailed_weather %}
      <tr>
        <td>{{ w.tid }}</td>
        <td>{{ w.temp }}</td>
        <td>{{ w.følt_temp }}</td>
        <td>{{ w.nedbør }}</td>
        <td>{{ w.vind }}</td>
        <td>{{ w.emoji }}</td>
      </tr>
      {% endfor %}
    </table>
  </div>
</body>
</html>
"""

    return render_template_string(
        html,
        station=station["name"],
        departures=dep_list,
        weather=weather,
        detailed_weather=detailed_weather,
    )


if __name__ == "__main__":
    app.run(debug=True)
