import requests
import psycopg2
from datetime import datetime

# Sofia coordinates
LAT = 42.6977
LON = 23.3219

# Get CURRENT weather only (not forecast)
url = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={LAT}&longitude={LON}"
    "&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
    "precipitation,surface_pressure,cloud_cover,wind_speed_10m"
    "&timezone=auto"
)

response = requests.get(url, timeout=30)
response.raise_for_status()
data = response.json()

# Connect to database
conn = psycopg2.connect(
    host="postgres",
    port=5432,
    dbname="weather",
    user="weather_user",
    password="weather_pass",
)
cur = conn.cursor()

# Create table
cur.execute(
    """
    CREATE TABLE IF NOT EXISTS current_weather (
        ingestion_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP PRIMARY KEY,
        temperature_2m DOUBLE PRECISION,
        relative_humidity_2m DOUBLE PRECISION,
        apparent_temperature DOUBLE PRECISION,
        precipitation DOUBLE PRECISION,
        surface_pressure DOUBLE PRECISION,
        cloud_cover DOUBLE PRECISION,
        wind_speed_10m DOUBLE PRECISION
    );
    """
)

current = data["current"]
now = datetime.now()

# Insert current weather snapshot
cur.execute(
    """
    INSERT INTO current_weather (
        temperature_2m,
        relative_humidity_2m,
        apparent_temperature,
        precipitation,
        surface_pressure,
        cloud_cover,
        wind_speed_10m
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s);
    """,
    (
        current["temperature_2m"],
        current["relative_humidity_2m"],
        current["apparent_temperature"],
        current["precipitation"],
        current["surface_pressure"],
        current["cloud_cover"],
        current["wind_speed_10m"],
    ),
)

conn.commit()
cur.close()
conn.close()