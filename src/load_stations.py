import csv
from mvg import MvgApi


def save_stations_to_csv(filename="stations.csv"):
    stations = MvgApi.stations()
    # Anta at stations er en liste av dicts med minst en 'name'-nøkkel
    station_names = sorted(
        {station["name"] for station in stations if "name" in station}
    )

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["station_name"])
        for name in station_names:
            writer.writerow([name])

    print(f"Saved {len(station_names)} stations to {filename}")


if __name__ == "__main__":
    save_stations_to_csv()
