from pathlib import Path

API_URL = "https://www.bandsintown.com/choose-dates/fetch-next/upcomingEvents"

PARIS_LATITUDE = "48.85341"
PARIS_LONGITUDE = "2.3488"
GENRE_QUERY = "all-genres"

# Au-delà d'environ 30 pages, l'API renvoie toujours la même page
MAX_PAGE = 30

MIN_DELAY_SECONDS = 2
MAX_DELAY_SECONDS = 5
DEFAULT_RETRY_AFTER_SECONDS = 200
MAX_TOO_MANY_REQUESTS_RETRIES = 3

# Toutes les pages collectées, numérotées à la suite : page_001.json, page_002.json...
RAW_DATA_DIR = Path("data") / "raw"
OUTPUT_CSV = Path("data") / "events_bandsintown.csv"

# Géocodage des salles via Nominatim (1 requête par seconde maximum)
CACHE_DIR = Path("data") / "cache"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
EXTERNAL_API_USER_AGENT = "Groupe1BandsintownScraper/1.0 (https://github.com/teaching-data-engineering/Groupe_1)"
EXTERNAL_API_DELAY_SECONDS = 1.1
EXTERNAL_API_MAX_RETRIES = 3
# Île-de-France (lon min, lat max, lon max, lat min) : sinon "Montreuil" peut être celui du Pas-de-Calais
GEOCODING_VIEWBOX = "1.4,49.25,3.6,48.1"

# Navigateurs imités par curl_cffi, un tiré au hasard à chaque requête. curl_cffi envoie l'empreinte TLS
# ET le User-Agent du navigateur choisi : les deux restent cohérents, sinon Cloudflare détecte le robot.
# Uniquement Chrome : testé le 23/10/2026, l'imitation de Firefox est bloquée par Cloudflare (403)
IMPERSONATE_BROWSERS = [
    "chrome150",
    "chrome146",
    "chrome145",
    "chrome142",
    "chrome136",
    "chrome133a",
    "chrome131",
]

# User-Agent, Accept, Sec-Ch-Ua* et Accept-Encoding sont fournis par curl_cffi selon le navigateur imité
HEADERS = {
    "Accept-language":"fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.bandsintown.com/choose-dates/genre/all-genres?calendarTrigger=true",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Upgrade-Insecure-Requests": "1",
}
