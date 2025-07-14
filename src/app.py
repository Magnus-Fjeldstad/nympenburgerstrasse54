from flask import Flask, render_template_string
from mvg import MvgApi, TransportType
import datetime
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


def get_weather(lat, lon, hours=6):
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&hourly=temperature_2m,weathercode&forecast_days=2"
    )
    resp = requests.get(url)
    data = resp.json()
    times = data["hourly"]["time"]
    temps = data["hourly"]["temperature_2m"]
    codes = data["hourly"]["weathercode"]
    now = datetime.datetime.now()
    weather = []
    for t, temp, code in zip(times, temps, codes):
        dt = datetime.datetime.fromisoformat(t)
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
    now = datetime.datetime.now()
    detailed_weather = []
    for t, temp, app_temp, code, pr, ws in zip(
        times, temps, apparent, codes, precip, wind
    ):
        dt = datetime.datetime.fromisoformat(t)
        # Kun neste time
        if 0 <= (dt - now).total_seconds() < 3600:
            detailed_weather.append(
                {
                    "tid": dt.strftime("%H:%M"),
                    "temp": temp,
                    "følt_temp": app_temp,
                    "nedbør": pr,
                    "vind": ws,
                    "code": code,
                    "emoji": weathercode_to_emoji(code),
                }
            )
    return detailed_weather


@app.route("/")
def index():
    station = MvgApi.station(DEFAULT_STATION)
    if not station:
        return "Stasjon ikke funnet"
    mvgapi = MvgApi(station["id"])
    departures = mvgapi.departures(limit=15, transport_types=[TransportType.UBAHN])
    print("Departures:", departures)  # Sjekk Render log

    if not departures:
        return "Ingen avganger funnet"
    dep_list = []
    for dep in departures:
        dep_list.append(
            {
                "line": dep["line"],
                "destination": dep["destination"],
                "tid": datetime.datetime.fromtimestamp(dep["time"]).strftime("%H:%M"),
            }
        )
    weather = get_weather(station["latitude"], station["longitude"], hours=6)
    detailed_weather = get_weather_next_hour(station["latitude"], station["longitude"])
    html = """
    <html>
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <style>
        body {
          font-family: Arial, sans-serif;
          margin: 0;
          padding: 0;
          background: #f7f7f7;
        }
        .container {
          max-width: 1200px;
          margin: 0 auto;
          padding: 20px;
        }
        h1, h2 {
          text-align: center;
          margin-top: 20px;
        }
        table {
          width: 100%;
          border-collapse: collapse;
          margin: 20px 0;
          background: #fff;
          box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        th, td {
          padding: 8px 4px;
          text-align: center;
          border-bottom: 1px solid #eee;
        }
        th {
          background: #e3e3e3;
        }
        tr:last-child td {
          border-bottom: none;
        }
        @media (max-width: 700px) {
          .container {
            padding: 5px;
          }
          table, th, td {
            font-size: 14px;
            padding: 4px 2px;
          }
        }
      </style>
    </head>
    <body>
    <div class="container">
    <h1>Piplup er verdens søteste❤️❤️❤️</h1>
    <h1>Neste 5 U-Bahn fra {{station}}</h1>
    <table>
      <tr>
        <th>Linje</th>
        <th>Destinasjon</th>
        <th>Avgangstid</th>
      </tr>
      {% for dep in departures %}
      <tr>
        <td>{{ dep.line }}</td>
        <td>{{ dep.destination }}</td>
        <td>{{ dep.tid }}</td>
      </tr>
      {% endfor %}
    </table>
    <h2>Vær neste 6 timer</h2>
    <table>
      <tr>
        <th>Tid</th>
        <th>Temperatur (°C)</th>
        <th>Emoji</th>
      </tr>
      {% for w in weather %}
      <tr>
        <td>{{ w.tid }}</td>
        <td>{{ w.temp }}</td>
        <td>{{ w.emoji }}</td>
      </tr>
      {% endfor %}
    </table>
    <h2>Veldig detaljert vær neste time</h2>
    <table>
      <tr>
        <th>Tid</th>
        <th>Temperatur (°C)</th>
        <th>Følt temp (°C)</th>
        <th>Nedbør (mm)</th>
        <th>Vind (m/s)</th>
        <th>Emoji</th>
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
