import json
import random
import time
from datetime import date, timedelta

from curl_cffi import requests

from bandsintown_scraper.config import (
    API_URL,
    DEFAULT_RETRY_AFTER_SECONDS,
    GENRE_QUERY,
    HEADERS,
    IMPERSONATE_BROWSER,
    MAX_DELAY_SECONDS,
    MAX_PAGE,
    MIN_DELAY_SECONDS,
    PARIS_LATITUDE,
    PARIS_LONGITUDE,
    RAW_DATA_DIR,
)


def scrap_one_page(page_idx, start_date, end_date):
    """Renvoie la liste brute des événements d'une page, ou None si la requête échoue."""
    params = {
        "date": f"{start_date:%Y-%m-%d}T00:00:00,{end_date:%Y-%m-%d}T23:00:00",
        "page": page_idx,
        "longitude": PARIS_LONGITUDE,
        "latitude": PARIS_LATITUDE,
        "genre_query": GENRE_QUERY,
    }

    while True:
        response = requests.get(
            API_URL, headers=HEADERS, params=params, impersonate=IMPERSONATE_BROWSER
        )
        if response.status_code != 429:
            break
        retry_after = int(response.headers.get("Retry-After", DEFAULT_RETRY_AFTER_SECONDS))
        print(f"page {page_idx} : 429 (trop de requêtes), pause de {retry_after} s")
        time.sleep(retry_after)

    if response.status_code != 200:
        print(f"page {page_idx} : échec ({response.status_code}) : {response.text[:200]}")
        return None

    data = response.json()
    return data if isinstance(data, list) else data.get("events", [])


def save_json(events, start_date, end_date, page_idx):
    period_dir = RAW_DATA_DIR / f"{start_date:%Y-%m-%d}_{end_date:%Y-%m-%d}"
    period_dir.mkdir(parents=True, exist_ok=True)
    with open(period_dir / f"page_{page_idx:03d}.json", "w", encoding="utf-8") as file:
        json.dump(events, file, ensure_ascii=False, indent=2)


def scrap_multiple_pages(start_date, end_date, max_page, seen_ids):
    """Collecte les pages d'une période jusqu'à la fin des résultats ou la limite de l'API.

    Renvoie (new_events, page_limit_reached, nb_pages).
    page_limit_reached vaut True quand la période a été coupée : il reste des événements après.
    """
    new_events = []

    for page_idx in range(1, max_page + 1):
        events = scrap_one_page(page_idx, start_date, end_date)

        if events is None:
            return new_events, False, page_idx
        if not events:
            print(f"page {page_idx} : vide, fin des résultats.")
            return new_events, False, page_idx

        # Une fois sa limite atteinte, l'API renvoie en boucle une page déjà vue
        page_new_events = [event for event in events if event.get("id") not in seen_ids]
        if not page_new_events:
            print(f"page {page_idx} : page répétée, limite de l'API atteinte.")
            return new_events, True, page_idx

        save_json(events, start_date, end_date, page_idx)
        seen_ids.update(event.get("id") for event in page_new_events)
        new_events.extend(page_new_events)
        print(f"page {page_idx} : {len(page_new_events)} nouveaux événements.")

        time.sleep(random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS))

    return new_events, True, max_page


def scrap_all_events(end_date, start_date=None):
    """Collecte tous les événements jusqu'à end_date en découpant automatiquement en périodes.

    L'API renvoie les événements triés par date et limite le nombre de pages par période.
    Quand une période est coupée, la suivante repart du jour du dernier événement reçu :
    le nombre de périodes dépend donc du volume de données, pas d'un choix arbitraire.
    """
    cursor = start_date or date.today()
    seen_ids = set()
    nb_periods = 0
    nb_pages_total = 0

    while cursor <= end_date:
        nb_periods += 1
        print(f"=== Période {nb_periods} : du {cursor:%d/%m/%Y} au {end_date:%d/%m/%Y} ===")

        new_events, page_limit_reached, nb_pages = scrap_multiple_pages(
            cursor, end_date, MAX_PAGE, seen_ids
        )
        nb_pages_total += nb_pages
        print(f"période {nb_periods} : {nb_pages} pages, {len(new_events)} nouveaux événements.\n")

        if not page_limit_reached:
            break

        # Le dernier jour a pu être coupé au milieu : on le redemande, seen_ids filtre les doublons
        last_day = (
            date.fromisoformat(max(event["startsAt"] for event in new_events)[:10])
            if new_events
            else cursor
        )
        if last_day > cursor:
            cursor = last_day
        else:
            print(f"attention : le {cursor:%d/%m/%Y} dépasse à lui seul la limite de pages, "
                  "des événements peuvent manquer.")
            cursor += timedelta(days=1)

    print(f"{len(seen_ids)} événements collectés en {nb_periods} période(s) "
          f"et {nb_pages_total} pages au total.")
