from typing import Optional

from fastapi import APIRouter, Query, Request
from google.cloud import bigquery

from api.app.data_base import TABLE, run_query
from api.app.pagination import PER_PAGE, build_metadata

router = APIRouter()


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
    where = "WHERE (@ville IS NULL OR ville = @ville) AND (@type_evenement IS NULL OR type_evenement = @type_evenement)"

    total = run_query(f"SELECT COUNT(*) AS n FROM `{TABLE}` {where}", filtres)[0]["n"]

    params = filtres + [
        bigquery.ScalarQueryParameter("limit", "INT64", PER_PAGE),
        bigquery.ScalarQueryParameter("offset", "INT64", (page - 1) * PER_PAGE),
    ]
    data = run_query(
        f"SELECT id, artiste, lieu, ville, debut, nb_rsvp, popularite, type_evenement, url_evenement "
        f"FROM `{TABLE}` {where} ORDER BY debut, id LIMIT @limit OFFSET @offset",
        params,
    )
    return {"metadata": build_metadata(request, page, PER_PAGE, total), "data": data}