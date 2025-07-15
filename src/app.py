from flask import Flask, render_template_string, request
from mvg import MvgApi, TransportType
import datetime
from zoneinfo import ZoneInfo
import requests
import csv
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)

DEFAULT_STATION = "Maillingerstrasse, München"


def load_station_names(filename=None):
    if filename is None:
        filename = os.path.join(BASE_DIR, "static", "resources", "stations.csv")
    with open(filename, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        return [row["station_name"] for row in reader]


def weathercode_to_emoji(code):
    mapping = {
        0: "☀️",
        1: "🌤️",
        2: "⛅",
        3: "☁️",
        45: "🌫️",
        48: "🌫️",
        51: "🌦️",
        53: "🌦️",
        55: "🌦️",
        61: "🌧️",
        63: "🌧️",
        65: "🌧️",
        71: "🌨️",
        73: "🌨️",
        75: "🌨️",
        80: "🌦️",
        81: "🌦️",
        82: "🌦️",
        95: "⛈️",
        96: "⛈️",
        99: "⛈️",
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
    now = datetime.datetime.now(ZoneInfo("Europe/Berlin"))
    weather = []

    for t, temp, code in zip(times, temps, codes):
        dt = datetime.datetime.fromisoformat(t)
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
            break
    return detailed_weather


@app.route("/")
def index():
    station_names = load_station_names()
    selected_station = request.args.get("station") or DEFAULT_STATION

    station = MvgApi.station(selected_station)
    if not station:
        return f"Station not found: {selected_station}"

    mvgapi = MvgApi(station["id"])
    departures = mvgapi.departures(limit=15, transport_types=[TransportType.UBAHN])
    if not departures:
        return "No departures found"

    dep_list = []
    color_map = {}
    color_palette = [
        "#ffd1dc",  # Rosa
        "#c1f0f6",  # Lys cyan
        "#ffedcc",  # Aprikos
        "#d2f4c4",  # Lys grønn
        "#f6c6ea",  # Lilla-rosa
        "#c2cfff",  # Lys blå
        "#ffe0b2",  # Lys oransje
        "#e0f7fa",  # Blågrønn
        "#e6ee9c",  # Gulgrønn
        "#f0c9f0",  # Lavendel
        "#b2dfdb",  # Turkisgrønn
        "#f8bbd0",  # Rosa-beige
        "#dcedc8",  # Matt lime
        "#f3e5f5",  # Lys lilla
        "#ffccbc",  # Rosa-oransje
        "#b3e5fc",  # Isblå
        "#c8e6c9",  # Mintgrønn
        "#f0f4c3",  # Gulhvit
        "#d1c4e9",  # Lilla-grå
        "#ffecb3",  # Lys gul
    ]

    color_index = 0

    now = datetime.datetime.now(ZoneInfo("Europe/Berlin"))

    for dep in departures:
        dt = datetime.datetime.fromtimestamp(dep["time"], tz=ZoneInfo("Europe/Berlin"))
        minutes_left = int((dt - now).total_seconds() / 60)
        dest = dep["destination"]
        if dest not in color_map:
            color_map[dest] = color_palette[color_index % len(color_palette)]
            color_index += 1

        dep_list.append(
            {
                "line": f'<img src="/static/resources/{dep["line"].lower()}.png" alt="{dep["line"]}" height="24">',
                "destination": dest,
                "tid": dt.strftime("%H:%M"),
                "minutes_left": minutes_left,
                "bgcolor": color_map[dest],
            }
        )

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
    .emoji {
      font-size: 30px;
    }
    .container {
      max-width: 900px;
      margin: auto;
      padding: 20px;
      position: relative;
    }
    h1, h2 {
      text-align: center;
      margin: 30px 0 20px;
    }
    form {
      text-align: center;
      margin-bottom: 30px;
      position: relative;
    }
    input, button {
      font-size: 16px;
      padding: 8px;
      width: 250px;
      max-width: 80vw;
      box-sizing: border-box;
    }
    button {
      margin-left: 8px;
      cursor: pointer;
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

    /* Autocomplete list styles */
    #autocomplete-list {
      position: absolute;
      top: 38px; /* litt under inputfeltet */
      left: 50%;
      transform: translateX(-50%);
      width: 250px;
      max-width: 80vw;
      border: 1px solid #ddd;
      border-top: none;
      background: white;
      max-height: 180px;
      overflow-y: auto;
      z-index: 1000;
      box-shadow: 0 2px 6px rgba(0,0,0,0.2);
      border-radius: 0 0 8px 8px;
    }
    #autocomplete-list li {
      padding: 8px 12px;
      cursor: pointer;
    }
    #autocomplete-list li:hover {
      background-color: #0078d7;
      color: white;
    }

    @media (max-width: 700px) {
      .container {
        padding: 10px;
      }
      table, th, td {
        font-size: 14px;
        padding: 6px 4px;
      }
      input, button {
        width: 100%;
        margin: 4px 0;
      }
      form {
        display: flex;
        flex-direction: column;
        align-items: center;
      }
      #autocomplete-list {
        left: 10%;
        transform: none;
        width: 80vw;
        top: 42px;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>U-Bahn & Weather for Munich</h1>

    <form method="get" autocomplete="off" id="station-form">
      <input
        type="text"
        id="stationInput"
        name="station"
        placeholder="Enter station..."
        value="{{ station }}"
        spellcheck="false"
        autocomplete="off"
      />
      <button type="submit">Search</button>
      <ul id="autocomplete-list"></ul>
    </form>

    <h2>Next U-Bahns from {{station}}</h2>
    <table>
      <tr>
        <th>Line</th>
        <th>Destination</th>
        <th>Departure</th>
        <th>In (min)</th>
      </tr>
      {% for dep in departures %}
      <tr style="background-color: {{ dep.bgcolor }}">
        <td>{{ dep.line|safe }}</td>
        <td>{{ dep.destination }}</td>
        <td>{{ dep.tid }}</td>
        <td>{{ dep.minutes_left }}</td>
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
        <td class="emoji">{{ w.emoji }}</td>
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
        <td class="emoji">{{ w.emoji }}</td>
      </tr>
      {% endfor %}
    </table>
  </div>

<script>
  const stations = {{ station_names|tojson }};
  const input = document.getElementById("stationInput");
  const list = document.getElementById("autocomplete-list");

  input.addEventListener("input", function () {
    const val = this.value.trim().toLowerCase();
    list.innerHTML = "";
    if (!val) return;

    let count = 0;
    for (const station of stations) {
      if (station.toLowerCase().startsWith(val)) {
        const item = document.createElement("li");
        item.textContent = station;
        item.addEventListener("click", () => {
          input.value = station;
          list.innerHTML = "";
        });
        list.appendChild(item);
        count++;
        if (count >= 10) break; // maks 10 forslag
      }
    }
  });

  // Klikk utenfor autocomplete-listen skjuler den
  document.addEventListener("click", e => {
    if (e.target !== input) {
      list.innerHTML = "";
    }
  });

  // Piltaster og Enter navigasjon
  let currentFocus = -1;
  input.addEventListener("keydown", function(e) {
    const items = list.getElementsByTagName("li");
    if (items.length === 0) return;

    if (e.key === "ArrowDown") {
      currentFocus++;
      if (currentFocus >= items.length) currentFocus = 0;
      addActive(items);
      e.preventDefault();
    } else if (e.key === "ArrowUp") {
      currentFocus--;
      if (currentFocus < 0) currentFocus = items.length - 1;
      addActive(items);
      e.preventDefault();
    } else if (e.key === "Enter") {
      if (currentFocus > -1) {
        e.preventDefault();
        items[currentFocus].click();
        currentFocus = -1;
      }
    }
  });

  function addActive(items) {
    removeActive(items);
    if (currentFocus >= items.length) currentFocus = 0;
    if (currentFocus < 0) currentFocus = items.length -1;
    items[currentFocus].classList.add("autocomplete-active");
  }
  function removeActive(items) {
    for (const item of items) {
      item.classList.remove("autocomplete-active");
    }
  }
</script>

</body>
</html>
"""

    return render_template_string(
        html,
        station=selected_station,
        departures=dep_list,
        weather=weather,
        detailed_weather=detailed_weather,
        station_names=station_names,
    )


if __name__ == "__main__":
    app.run(debug=True)
