from google.cloud import bigquery

from bandsintown_scraper.loader import get_bigquery_client

client = get_bigquery_client()
TABLE = f"{client.project}.dataset_group_1.events_bandsintown"


def run_query(sql, params=None):
    """Exécute une requête SQL sur BigQuery et renvoie les lignes sous forme de dictionnaires."""
    job_config = bigquery.QueryJobConfig(query_parameters=params or [])
    return [dict(row) for row in client.query(sql, job_config=job_config).result()]