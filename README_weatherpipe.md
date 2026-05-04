# WeatherPipe Setup Guide

This project collects weather data for Sofia, stores it in PostgreSQL, orchestrates ingestion with Apache Airflow, and visualizes the data in Grafana. The stack uses Docker Compose, Airflow’s official local Docker quick-start approach, PostgreSQL initialization rules, and Open-Meteo as the weather source.[cite:193][cite:712][cite:999]

## What was done

The project was cleaned up to avoid the earlier Airflow and database issues. Airflow now starts with the proper two-file Compose command, the weather database can be rebuilt from empty volumes, the old `weather_hourly` table is no longer part of the intended schema, and the pipeline is meant to use current weather data instead of storing forecast-hour timestamps that did not match the actual DAG run time.[cite:193][cite:712][cite:999]

In practice, that means the setup now focuses on one clean ingestion path: Airflow runs the DAG, the DAG calls the weather script, the script inserts rows into the new weather table, and Grafana reads that table for charts. The key fixes were removing stale volume data, checking `init.sql`, using the proper Airflow initialization flow, and avoiding fragile startup dependency installs in the Airflow init container.[cite:193][cite:1129][cite:1138]

## Final architecture

Services in the stack:

- `weather_postgres` for project data
- `weather_grafana` for dashboards
- `airflow-postgres` for Airflow metadata
- `redis` for Airflow CeleryExecutor
- Airflow services: `airflow-init`, `airflow-apiserver`, `airflow-scheduler`, `airflow-worker`, `airflow-triggerer`, `airflow-dag-processor`

Airflow’s Docker quick-start runs multiple containers and requires an initialization step before the rest of the services are started. PostgreSQL can also run initialization SQL scripts from `/docker-entrypoint-initdb.d`, but those scripts run only when the database directory is empty.[cite:193][cite:712][cite:1138]

## Project structure

Keep these files and folders in the project root:

- `docker-compose.yml`
- `docker-compose.airflow.yml`
- `.env`
- `init.sql` (only if you intentionally want database bootstrap SQL)
- `dags/`
- `scripts/`
- `logs/`
- `config/`
- `plugins/`

Docker Compose can merge multiple Compose files into one effective configuration, which is why the Airflow file must be included every time Airflow is managed.[cite:193]

## Prerequisites

Install Docker Desktop and verify Docker Compose is available in the terminal before starting. Airflow’s Docker quick-start depends on Docker being available first.[cite:193]

Check with:

```powershell
docker --version
docker compose version
```

## Create the `.env` file

Create a file named `.env` in the project root. It must contain plain `KEY=value` pairs only.

Use this content:

```env
# Weather DB
POSTGRES_DB=weather
POSTGRES_USER=weather_user
POSTGRES_PASSWORD=weather_pass
PGHOST=localhost
PGPORT=5432
PGDATABASE=weather
PGUSER=weather_user
PGPASSWORD=weather_pass

# Airflow
AIRFLOW_UID=50000
AIRFLOW_PROJ_DIR=.
AIRFLOW_IMAGE_NAME=apache/airflow:3.2.1

_AIRFLOW_WWW_USER_USERNAME=admin
_AIRFLOW_WWW_USER_PASSWORD=admin
_AIRFLOW_WWW_USER_FIRSTNAME=Admin
_AIRFLOW_WWW_USER_LASTNAME=User
_AIRFLOW_WWW_USER_EMAIL=admin@example.com

FERNET_KEY=ZmFrZV9mZXJuZXRfa2V5X2Zvcl9sb2NhbF9kZXZlbG9wbWVudA==
AIRFLOW__API_AUTH__JWT_SECRET=airflow_jwt_secret
AIRFLOW__API_AUTH__JWT_ISSUER=airflow

_PIP_ADDITIONAL_REQUIREMENTS=
```

The Airflow docs warn that runtime package installation at startup is only for testing and is fragile, so `_PIP_ADDITIONAL_REQUIREMENTS` is intentionally left empty here.[cite:193]

## About `init.sql`

If you use `init.sql`, make sure it does **not** recreate `weather_hourly`. PostgreSQL initialization scripts in `/docker-entrypoint-initdb.d` are executed automatically only when the database is initialized from an empty data directory, so an old `init.sql` can bring back an old table even after a rebuild.[cite:712][cite:1138][cite:1129]

If you do not need bootstrap SQL, the safest option is to remove `init.sql` and let the ingestion script create the table it needs.

## Clean rebuild from scratch

To remove all old data, containers, networks, and named volumes:

```powershell
docker compose -f docker-compose.yml -f docker-compose.airflow.yml down --volumes --remove-orphans
```

Docker Compose removes service containers and, with `--volumes`, also removes the named volumes that hold Postgres data, which is the correct way to force a truly clean database rebuild.[cite:193]

Then initialize Airflow:

```powershell
docker compose -f docker-compose.yml -f docker-compose.airflow.yml up airflow-init
```

After `airflow-init` finishes successfully, start everything else:

```powershell
docker compose -f docker-compose.yml -f docker-compose.airflow.yml up -d
```

This follows the intended Airflow Docker startup flow: initialize first, then start the full stack.[cite:193]

## Always use both Compose files

Run this any time you want to verify the combined project services:

```powershell
docker compose -f docker-compose.yml -f docker-compose.airflow.yml config --services
```

That should list both base services and Airflow services. If the Airflow file is omitted, Airflow services will not be part of the effective stack.[cite:193]

## Check that everything is running

Use:

```powershell
docker compose -f docker-compose.yml -f docker-compose.airflow.yml ps
docker ps
```

Airflow should expose port `8080`, and Grafana should expose port `3000`. Airflow also provides a health endpoint that can be checked after the API server is up.[cite:193]

```powershell
curl http://localhost:8080/api/v2/monitor/health
```

## Open the apps

Open in the browser:

- Airflow: `http://localhost:8080`
- Grafana: `http://localhost:3000`

The Airflow admin user is created from the `_AIRFLOW_WWW_USER_*` values in `.env`, so with the sample file above the login is `admin` / `admin`.[cite:193]

## Current weather ingestion

The pipeline should now use current weather instead of hourly forecast storage. Open-Meteo provides current weather data separately, and this matches the requirement to store the weather at the actual DAG run moment rather than the nearest hourly forecast slot.[cite:999]

Example API shape:

```text
https://api.open-meteo.com/v1/forecast?latitude=42.6977&longitude=23.3219&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,surface_pressure,cloud_cover,wind_speed_10m&timezone=auto
```

## Query the new table

Use this to inspect the latest rows:

```sql
SELECT *
FROM current_weather
ORDER BY ingestion_time DESC
LIMIT 20;
```

Use this from PowerShell:

```powershell
docker exec -it weather_postgres psql -U weather_user -d weather -c "SELECT * FROM current_weather ORDER BY ingestion_time DESC LIMIT 20;"
```

## Grafana SQL example

For a Grafana PostgreSQL time-series panel:

```sql
SELECT
  $__timeGroup(ingestion_time, $__interval) AS time,
  AVG(temperature_2m) AS temperature_2m,
  AVG(relative_humidity_2m) AS relative_humidity_2m,
  AVG(wind_speed_10m) AS wind_speed_10m
FROM current_weather
WHERE $__timeFilter(ingestion_time)
GROUP BY 1
ORDER BY 1;
```

## Restart commands

Restart only the Airflow execution services after code changes:

```powershell
docker compose -f docker-compose.yml -f docker-compose.airflow.yml restart airflow-apiserver airflow-scheduler airflow-dag-processor airflow-worker
```

Restart the whole stack:

```powershell
docker compose -f docker-compose.yml -f docker-compose.airflow.yml restart
```

If you need a full clean restart:

```powershell
docker compose -f docker-compose.yml -f docker-compose.airflow.yml down --volumes --remove-orphans
docker compose -f docker-compose.yml -f docker-compose.airflow.yml up airflow-init
docker compose -f docker-compose.yml -f docker-compose.airflow.yml up -d
```

## Troubleshooting

### `weather_hourly` still appears

That usually means one of these is true:

- old data volume was not removed
- `init.sql` recreated the old table
- an old Python script or DAG still contains `CREATE TABLE IF NOT EXISTS weather_hourly`

Initialization SQL and old application code are the two most common reasons a dropped table returns after a rebuild.[cite:712][cite:1138]

Search the project:

```powershell
findstr /spin "weather_hourly" *.py dags\* scripts\* *.sql
```

### Airflow services do not appear

Check the merged service list:

```powershell
docker compose -f docker-compose.yml -f docker-compose.airflow.yml config --services
```

If Airflow services are listed there, Docker is loading the file correctly and the problem is startup or initialization, not Compose file discovery.[cite:193]

### `airflow-init` hangs

Keep `_PIP_ADDITIONAL_REQUIREMENTS=` empty and rerun the init flow. Airflow documents startup package injection as fragile and better suited only for quick testing.[cite:193]

### DAG is green but no rows appear

Check the worker logs and confirm the script is inserting into `current_weather` rather than an old table name.

```powershell
docker compose -f docker-compose.yml -f docker-compose.airflow.yml logs --tail=50 airflow-worker
docker exec -it weather_postgres psql -U weather_user -d weather -c "SELECT * FROM current_weather ORDER BY ingestion_time DESC LIMIT 20;"
```

## Recommended workflow

1. Keep `.env` clean.
2. Keep `init.sql` either minimal or removed.
3. Use both Compose files every time.
4. Run `airflow-init` before `up -d` on a fresh environment.
5. Use only the new weather table.
6. Query `current_weather` in Grafana and psql.

This setup avoids the earlier problems caused by partial Compose startup, old persisted volumes, old SQL init definitions, and hourly forecast timestamps that did not match the actual ingestion moment.[cite:193][cite:712][cite:999]
