from datetime import datetime

from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator

with DAG(
    dag_id="weather_pipeline",
    start_date=datetime(2026, 5, 4),
    schedule="*/5 * * * *",
    catchup=False,
    is_paused_upon_creation=False,
    tags=["weather"],
) as dag:

    ingest_weather = BashOperator(
        task_id="ingest_weather",
        bash_command="python /opt/airflow/scripts/weather_ingest.py",
    )