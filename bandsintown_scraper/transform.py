import json

import pandas as pd

from bandsintown_scraper.config import RAW_DATA_DIR

FIELDS = {
    "id": "id",
    "artistName": "artiste",
    "venueName": "lieu",
    "startsAt": "debut",
    "endsAt": "fin",
    "eventUrl": "url_evenement",
    "streamingEvent": "streaming",
    "watchLiveText": "watch_live_text",
}


def load_events_dataframe(raw_dir=RAW_DATA_DIR):
    """Agrège tous les JSON bruts en un DataFrame, une ligne par événement."""
    events = []
    for json_path in sorted(raw_dir.glob("*/page_*.json")):
        with open(json_path, encoding="utf-8") as file:
            events.extend(json.load(file))

    df = pd.DataFrame(events, columns=list(FIELDS)).rename(columns=FIELDS)
    df = df.drop_duplicates(subset="id")
    df["debut"] = pd.to_datetime(df["debut"])
    df["fin"] = pd.to_datetime(df["fin"])
    return df.sort_values("debut").reset_index(drop=True)
