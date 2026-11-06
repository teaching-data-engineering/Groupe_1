from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from google.cloud import bigquery

from api.app.data_base import TABLE, run_query
from api.app.pagination import PER_PAGE, build_metadata

router = APIRouter()

COLONNES = (
    "id, artiste, lieu, ville, debut, nb_rsvp, popularite, "
    "type_evenement, url_evenement"
)


@router.get("/events")
def list_events(
    request: Request,
    page: int = Query(1, ge=1),
    ville: Optional[str] = None,
    type_evenement: Optional[str] = None,
):
    filtres = [
        bigquery.ScalarQueryParameter("ville", "STRING", ville),
        bigquery.ScalarQueryParameter("type_evenement", "STRING", type_evenement),
    ]
    where = (
        "WHERE (@ville IS NULL OR ville = @ville) "
        "AND (@type_evenement IS NULL OR type_evenement = @type_evenement)"
    )

    total = run_query(f"SELECT COUNT(*) AS n FROM `{TABLE}` {where}", filtres)[0]["n"]

    params = filtres + [
        bigquery.ScalarQueryParameter("limit", "INT64", PER_PAGE),
        bigquery.ScalarQueryParameter("offset", "INT64", (page - 1) * PER_PAGE),
    ]
    data = run_query(
        f"SELECT {COLONNES} FROM `{TABLE}` {where} "
        f"ORDER BY debut, id LIMIT @limit OFFSET @offset",
        params,
    )
    return {"metadata": build_metadata(request, page, PER_PAGE, total), "data": data}


# Les routes fixes doivent être déclarées AVANT /events/{event_id}
@router.get("/events/by-day-of-week")
def events_by_day_of_week(week: Optional[int] = Query(None, ge=1, le=53)):
    sql = f"""
        SELECT jour_semaine, COUNT(*) AS nb_evenements
        FROM `{TABLE}`
        WHERE (@week IS NULL OR numero_semaine = @week)
        GROUP BY jour_semaine
        ORDER BY nb_evenements DESC
    """
    data = run_query(sql, [bigquery.ScalarQueryParameter("week", "INT64", week)])
    return {"week": week, "data": data}


@router.get("/events/search")
def search_events(
    request: Request,
    page: int = Query(1, ge=1),
    artistName: Optional[str] = None,
    venueName: Optional[str] = None,
    date_start: Optional[date] = None,
    date_end: Optional[date] = None,
):
    filtres = [
        bigquery.ScalarQueryParameter("artist", "STRING", artistName),
        bigquery.ScalarQueryParameter("venue", "STRING", venueName),
        bigquery.ScalarQueryParameter("d_start", "DATE", date_start),
        bigquery.ScalarQueryParameter("d_end", "DATE", date_end),
    ]
    where = """
        WHERE (@artist IS NULL OR LOWER(artiste) LIKE CONCAT('%', LOWER(@artist), '%'))
          AND (@venue IS NULL OR LOWER(lieu) LIKE CONCAT('%', LOWER(@venue), '%'))
          AND (@d_start IS NULL OR DATE(debut) >= @d_start)
          AND (@d_end IS NULL OR DATE(debut) <= @d_end)
    """
    total = run_query(f"SELECT COUNT(*) AS n FROM `{TABLE}` {where}", filtres)[0]["n"]

    params = filtres + [
        bigquery.ScalarQueryParameter("limit", "INT64", PER_PAGE),
        bigquery.ScalarQueryParameter("offset", "INT64", (page - 1) * PER_PAGE),
    ]
    data = run_query(
        f"SELECT {COLONNES} FROM `{TABLE}` {where} "
        f"ORDER BY debut, id LIMIT @limit OFFSET @offset",
        params,
    )
    return {"metadata": build_metadata(request, page, PER_PAGE, total), "data": data}


@router.get("/events/{event_id}")
def get_event(event_id: int):
    rows = run_query(
        f"SELECT * FROM `{TABLE}` WHERE id = @id LIMIT 1",
        [bigquery.ScalarQueryParameter("id", "INT64", event_id)],
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Événement introuvable")
    return rows[0]