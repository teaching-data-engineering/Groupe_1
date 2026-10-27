"""Chargement des événements enrichis dans une table BigQuery."""
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

from bandsintown_scraper.config import BIGQUERY_DATASET, BIGQUERY_TABLE, GCP_CREDENTIALS_PATH

# Schéma explicite : la détection automatique de BigQuery se trompe sur les colonnes souvent vides
BIGQUERY_SCHEMA = [
    bigquery.SchemaField("id", "INTEGER", mode="REQUIRED", description="identifiant Bandsintown de l'événement"),
    bigquery.SchemaField("artiste", "STRING", description="nom de l'artiste"),
    bigquery.SchemaField("titre", "STRING", description="titre de l'événement (souvent vide)"),
    bigquery.SchemaField("lieu", "STRING", description="salle"),
    bigquery.SchemaField("localisation", "STRING", description="texte brut de l'API, ex. « Paris, France »"),
    bigquery.SchemaField("debut", "DATETIME", description="date et heure de début (heure de Paris)"),
    bigquery.SchemaField("fin", "DATETIME", description="date et heure de fin (souvent vide)"),
    bigquery.SchemaField("nb_rsvp", "INTEGER", description="nombre de personnes ayant signalé leur intérêt"),
    bigquery.SchemaField("url_evenement", "STRING", description="lien vers la page de l'événement"),
    bigquery.SchemaField("streaming", "BOOLEAN", description="événement diffusé en ligne"),
    bigquery.SchemaField("watch_live_text", "STRING", description="texte affiché pour le direct"),
    bigquery.SchemaField("date_collecte", "DATE", description="date de collecte de la page"),
    bigquery.SchemaField("ville", "STRING", description="ville de la salle"),
    bigquery.SchemaField("jour_semaine", "STRING", description="jour de la semaine de l'événement"),
    bigquery.SchemaField("est_weekend", "BOOLEAN", description="samedi ou dimanche"),
    bigquery.SchemaField("numero_semaine", "INTEGER", description="numéro de semaine ISO"),
    bigquery.SchemaField("mois", "INTEGER", description="mois de l'événement"),
    bigquery.SchemaField("heure", "INTEGER", description="heure de début"),
    bigquery.SchemaField("jours_avant_evenement", "INTEGER", description="jours entre la collecte et l'événement"),
    bigquery.SchemaField("duree_heures", "FLOAT", description="durée en heures (vide sans heure de fin)"),
    bigquery.SchemaField("type_evenement", "STRING", description="festival, soirée ou concert"),
    bigquery.SchemaField("popularite", "STRING", description="aucune, faible, moyenne ou forte"),
    bigquery.SchemaField("longitude", "FLOAT", description="longitude de la salle (Nominatim)"),
    bigquery.SchemaField("latitude", "FLOAT", description="latitude de la salle (Nominatim)"),
    bigquery.SchemaField("source_geocodage", "STRING", description="salle ou ville"),
]
INTEGER_COLUMNS = [field.name for field in BIGQUERY_SCHEMA if field.field_type == "INTEGER"]
FLOAT_COLUMNS = [field.name for field in BIGQUERY_SCHEMA if field.field_type == "FLOAT"]
BOOLEAN_COLUMNS = [field.name for field in BIGQUERY_SCHEMA if field.field_type == "BOOLEAN"]
STRING_COLUMNS = [field.name for field in BIGQUERY_SCHEMA if field.field_type == "STRING"]


def get_bigquery_client(credentials_path=GCP_CREDENTIALS_PATH):
    """Client BigQuery authentifié avec la clé du compte de service. Le projet est lu dans la clé."""
    if not credentials_path.exists():
        raise FileNotFoundError(
            f"Clé GCP introuvable : {credentials_path}. "
            "Placez la clé JSON du compte de service dans credentials/gcp_key.json."
        )
    credentials = service_account.Credentials.from_service_account_file(credentials_path)
    return bigquery.Client(credentials=credentials, project=credentials.project_id)


def prepare_for_bigquery(events_df):
    """Met les colonnes dans l'ordre du schéma, avec des types que BigQuery accepte sans conversion."""
    df = events_df[[field.name for field in BIGQUERY_SCHEMA]].copy()
    df[INTEGER_COLUMNS] = df[INTEGER_COLUMNS].astype("Int64")
    df[FLOAT_COLUMNS] = df[FLOAT_COLUMNS].apply(pd.to_numeric, errors="coerce").astype("float64")
    df[BOOLEAN_COLUMNS] = df[BOOLEAN_COLUMNS].astype("boolean")
    df[STRING_COLUMNS] = df[STRING_COLUMNS].astype("string")
    df["date_collecte"] = pd.to_datetime(df["date_collecte"]).dt.date
    return df


def load_events_to_bigquery(events_df, client=None, dataset=BIGQUERY_DATASET, table=BIGQUERY_TABLE):
    """Charge les événements dans BigQuery et renvoie (identifiant_de_la_table, nombre_de_lignes).

    La table est remplacée à chaque chargement (WRITE_TRUNCATE) : elle reflète toujours le dernier CSV,
    sans doublons, même si on relance plusieurs fois.
    """
    client = client or get_bigquery_client()
    table_id = f"{client.project}.{dataset}.{table}"
    job_config = bigquery.LoadJobConfig(
        schema=BIGQUERY_SCHEMA,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    client.load_table_from_dataframe(prepare_for_bigquery(events_df), table_id, job_config=job_config).result()
    return table_id, client.get_table(table_id).num_rows
