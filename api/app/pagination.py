import math

from fastapi import Request

PER_PAGE = 20


def build_metadata(request: Request, page: int, per_page: int, total: int) -> dict:
    """Construit la section metadata demandée par l'énoncé."""
    total_pages = max(1, math.ceil(total / per_page))
    next_url = None
    if page < total_pages:
        next_url = str(request.url.include_query_params(page=page + 1))
    return {
        "page": page,
        "total_pages": total_pages,
        "results_per_page": per_page,
        "total_results": total,
        "next_page_url": next_url,
    }