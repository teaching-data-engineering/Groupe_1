import json
import random
import re
import shutil
import tempfile
import time
from datetime import date, timedelta
from pathlib import Path

from curl_cffi import requests

from bandsintown_scraper.config import (
    API_URL,
    DEFAULT_RETRY_AFTER_SECONDS,
    GENRE_QUERY,
    HEADERS,
    IMPERSONATE_BROWSERS,
    MAX_DELAY_SECONDS,
    MAX_PAGE,
    MAX_TOO_MANY_REQUESTS_RETRIES,
    MIN_DELAY_SECONDS,
    PARIS_LATITUDE,
    PARIS_LONGITUDE,
    RAW_DATA_DIR,
)

PAGE_FILE_PATTERN = re.compile(r"page_(\d+)\.json$")


class ScrapingError(Exception):
    """Le site a refusé une requête (403, 416, 429 répétés...) : la collecte est incomplète."""


def scrap_one_page(page_idx, start_date, end_date, session):
    """Renvoie la liste brute des événements d'une page. Lève ScrapingError si le site refuse."""
    params = {
        "date": f"{start_date:%Y-%m-%d}T00:00:00,{end_date:%Y-%m-%d}T23:00:00",
        "page": page_idx,
        "longitude": PARIS_LONGITUDE,
        "latitude": PARIS_LATITUDE,
        "genre_query": GENRE_QUERY,
    }

    for _ in range(MAX_TOO_MANY_REQUESTS_RETRIES + 1):
        response = session.get(API_URL, headers=HEADERS, params=params)
        if response.status_code != 429:
            break
        retry_after = int(response.headers.get("Retry-After", DEFAULT_RETRY_AFTER_SECONDS))
        print(f"page {page_idx} : 429 (trop de requêtes), pause de {retry_after} s")
        time.sleep(retry_after)

    if response.status_code != 200:
        raise ScrapingError(
            f"page {page_idx} du {start_date:%d/%m/%Y} : échec ({response.status_code}) "
            f"{response.text[:200]}"
        )

    data = response.json()
    return data if isinstance(data, list) else data.get("events", [])


def list_page_files(raw_dir=RAW_DATA_DIR):
    """Fichiers page_XXX.json du dossier, triés par numéro (page_1000 vient après page_999)."""
    pages = [path for path in raw_dir.glob("page_*.json") if PAGE_FILE_PATTERN.search(path.name)]
    return sorted(pages, key=lambda path: int(PAGE_FILE_PATTERN.search(path.name).group(1)))


def save_json(events, start_date, end_date, page_idx, file_idx, output_dir):
    """Écrit une page brute, avec les informations de sa collecte."""
    page = {
        "collectedAt": date.today().isoformat(),
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "page": page_idx,
        "events": events,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / f"page_{file_idx:03d}.json", "w", encoding="utf-8") as file:
        json.dump(page, file, ensure_ascii=False, indent=2)


def move_pages_to_raw_dir(staging_dir, raw_dir=RAW_DATA_DIR):
    """Déplace les pages d'une collecte dans raw_dir, en continuant la numérotation existante."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    existing_pages = list_page_files(raw_dir)
    next_idx = int(PAGE_FILE_PATTERN.search(existing_pages[-1].name).group(1)) + 1 if existing_pages else 1
    new_pages = list_page_files(staging_dir)
    for offset, page_path in enumerate(new_pages):
        shutil.move(page_path, raw_dir / f"page_{next_idx + offset:03d}.json")
    return len(new_pages)


def scrap_multiple_pages(start_date, end_date, max_page, seen_ids, output_dir, session):
    """Collecte les pages d'une période jusqu'à la fin des résultats ou la limite de l'API.

    Renvoie (new_events, page_limit_reached, nb_pages).
    page_limit_reached vaut True quand la période a été coupée : il reste des événements après.
    """
    new_events = []

    for page_idx in range(1, max_page + 1):
        events = scrap_one_page(page_idx, start_date, end_date, session)

        if not events:
            print(f"page {page_idx} : vide, fin des résultats.")
            return new_events, False, page_idx

        # Une fois sa limite atteinte, l'API renvoie en boucle une page déjà vue
        page_new_events = [event for event in events if event.get("id") not in seen_ids]
        if not page_new_events:
            print(f"page {page_idx} : page répétée, limite de l'API atteinte.")
            return new_events, True, page_idx

        file_idx = len(list_page_files(output_dir)) + 1
        save_json(events, start_date, end_date, page_idx, file_idx, output_dir)
        seen_ids.update(event.get("id") for event in page_new_events)
        new_events.extend(page_new_events)
        print(f"page {page_idx} : {len(page_new_events)} nouveaux événements.")

        time.sleep(random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS))

    return new_events, True, max_page


def scrap_all_events(end_date, start_date=None):
    """Collecte tous les événements jusqu'à end_date et ajoute les pages dans RAW_DATA_DIR.

    Les pages sont d'abord écrites dans un dossier temporaire et ne sont déplacées dans
    RAW_DATA_DIR que si toute la collecte réussit : en cas de ScrapingError, data/ reste intact.

    Le navigateur imité est tiré au hasard une fois par collecte, puis gardé dans une session
    qui renvoie les cookies de Cloudflare : changer de navigateur à chaque requête depuis
    la même IP, sans cookies, est détecté comme un robot (403).
    """
    browser = random.choice(IMPERSONATE_BROWSERS)
    print(f"Navigateur imité : {browser}")
    with tempfile.TemporaryDirectory() as staging_dir, requests.Session(impersonate=browser) as session:
        _scrap_periods(end_date, start_date or date.today(), Path(staging_dir), session)
        nb_new_pages = move_pages_to_raw_dir(Path(staging_dir))
    print(f"{nb_new_pages} pages ajoutées dans {RAW_DATA_DIR} "
          f"({len(list_page_files())} pages au total).")


def _scrap_periods(end_date, cursor, output_dir, session):
    """Découpe automatiquement la collecte en périodes.

    L'API renvoie les événements triés par date et limite le nombre de pages par période.
    Quand une période est coupée, la suivante repart du jour du dernier événement reçu :
    le nombre de périodes dépend donc du volume de données, pas d'un choix arbitraire.
    """
    seen_ids = set()
    nb_periods = 0
    nb_pages_total = 0

    while cursor <= end_date:
        nb_periods += 1
        print(f"=== Période {nb_periods} : du {cursor:%d/%m/%Y} au {end_date:%d/%m/%Y} ===")

        new_events, page_limit_reached, nb_pages = scrap_multiple_pages(
            cursor, end_date, MAX_PAGE, seen_ids, output_dir, session
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
