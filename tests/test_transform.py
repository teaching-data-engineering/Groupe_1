import json

import pandas as pd

from bandsintown_scraper.transform import add_location_columns, classify_event_type, load_events_dataframe


def test_classify_event_type():
    assert classify_event_type("Winter Rising Fest") == "festival"
    assert classify_event_type("KALUPTO // Release Party") == "soirée"
    assert classify_event_type("Johanns Steiner – World Tour") == "concert"
    assert classify_event_type(None) == "concert"


def test_add_location_columns_groups_paris_variants():
    df = pd.DataFrame({"localisation": ["PARIS, France", "Paris 19 Buttes-Chaumont, France", "Montreuil, France"]})
    df = add_location_columns(df)
    assert df["ville"].tolist() == ["Paris", "Paris", "Montreuil"]
    assert df["pays"].tolist() == ["France", "France", "France"]


def test_load_events_dataframe_keeps_most_recent_version(tmp_path):
    def write_page(name, collected_at, rsvp):
        event = {
            "id": 1,
            "artistName": "Korn",
            "venueName": "Accor Arena",
            "locationText": "Paris, France",
            "startsAt": "2026-11-20T20:00:00",
            "rsvpCountInt": rsvp,
            "streamingEvent": False,
        }
        page = {"collectedAt": collected_at, "startDate": "2026-10-23", "endDate": "2026-11-30", "page": 1,
                "events": [event]}
        (tmp_path / name).write_text(json.dumps(page), encoding="utf-8")

    write_page("page_001.json", "2026-10-23", rsvp=10)
    write_page("page_002.json", "2026-10-25", rsvp=42)

    df = load_events_dataframe(tmp_path)

    assert len(df) == 1
    assert df.loc[0, "nb_rsvp"] == 42
    assert df.loc[0, "jours_avant_evenement"] == 26
