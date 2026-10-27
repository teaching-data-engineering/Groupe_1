from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest
from google.cloud import bigquery

from bandsintown_scraper.loader import (
    BIGQUERY_SCHEMA,
    get_bigquery_client,
    load_events_to_bigquery,
    prepare_for_bigquery,
)


@pytest.fixture
def events_df():
    """Deux événements au format produit par load_events_dataframe, dans le désordre des colonnes."""
    df = pd.DataFrame(
        {
            "id": [1, 2],
            "artiste": ["Korn", "Angèle"],
            "titre": [None, "Winter Fest"],
            "lieu": ["Accor Arena", "La Cigale"],
            "localisation": ["Paris, France", "Paris, France"],
            "debut": pd.to_datetime(["2026-11-20 20:00", "2026-11-21 19:30"]),
            "fin": pd.to_datetime([None, "2026-11-21 23:00"]),
            "nb_rsvp": [120, 3],
            "url_evenement": ["https://a", "https://b"],
            "streaming": [False, False],
            "watch_live_text": ["Watch Live", "Watch Live"],
            "date_collecte": pd.to_datetime(["2026-10-23", "2026-10-23"]),
            "ville": ["Paris", "Paris"],
            "jour_semaine": ["Friday", "Saturday"],
            "est_weekend": [False, True],
            "numero_semaine": [47, 47],
            "mois": [11, 11],
            "heure": [20, 19],
            "jours_avant_evenement": [28, 29],
            "duree_heures": [None, 3.5],
            "type_evenement": ["concert", "festival"],
            "popularite": pd.Categorical(["forte", "faible"]),
            "longitude": [2.378, None],
            "latitude": [48.838, None],
            "source_geocodage": ["salle", None],
        }
    )
    return df[list(reversed(df.columns))]


def test_prepare_for_bigquery_follows_schema_order(events_df):
    df = prepare_for_bigquery(events_df)
    assert list(df.columns) == [field.name for field in BIGQUERY_SCHEMA]


def test_prepare_for_bigquery_converts_types(events_df):
    df = prepare_for_bigquery(events_df)
    assert df["date_collecte"].iloc[0] == date(2026, 10, 23)
    assert df["popularite"].tolist() == ["forte", "faible"]
    assert df["longitude"].dtype == "float64" and pd.isna(df["longitude"].iloc[1])
    assert df["nb_rsvp"].dtype == "Int64"


def test_load_events_to_bigquery_replaces_table(events_df):
    client = MagicMock(project="mon-projet")
    client.get_table.return_value.num_rows = 2

    table_id, nb_rows = load_events_to_bigquery(events_df, client=client, dataset="mon_dataset", table="evenements")

    assert (table_id, nb_rows) == ("mon-projet.mon_dataset.evenements", 2)
    loaded_df, loaded_table_id = client.load_table_from_dataframe.call_args.args
    job_config = client.load_table_from_dataframe.call_args.kwargs["job_config"]
    assert loaded_table_id == "mon-projet.mon_dataset.evenements"
    assert len(loaded_df) == 2
    assert job_config.write_disposition == bigquery.WriteDisposition.WRITE_TRUNCATE
    assert job_config.schema == BIGQUERY_SCHEMA
    client.load_table_from_dataframe.return_value.result.assert_called_once()


def test_get_bigquery_client_explains_missing_key(tmp_path):
    with pytest.raises(FileNotFoundError, match="credentials/gcp_key.json"):
        get_bigquery_client(credentials_path=Path(tmp_path / "absente.json"))
