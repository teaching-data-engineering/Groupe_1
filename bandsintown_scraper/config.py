from pathlib import Path

API_URL = "https://www.bandsintown.com/choose-dates/fetch-next/upcomingEvents"

PARIS_LATITUDE = "48.85341"
PARIS_LONGITUDE = "2.3488"
GENRE_QUERY = "all-genres"

# Au-delà d'environ 30 pages, l'API renvoie toujours la même page
MAX_PAGE = 30

MIN_DELAY_SECONDS = 2
MAX_DELAY_SECONDS = 5
DEFAULT_RETRY_AFTER_SECONDS = 60

RAW_DATA_DIR = Path("data") / "raw"
OUTPUT_CSV = Path("data") / "events_bandsintown.csv"

# Enrichissement via des API externes (1 requête par seconde maximum pour les deux)
CACHE_DIR = Path("data") / "cache"
MUSICBRAINZ_URL = "https://musicbrainz.org/ws/2/artist/"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
EXTERNAL_API_USER_AGENT = "Groupe1BandsintownScraper/1.0 (https://github.com/teaching-data-engineering/Groupe_1)"
EXTERNAL_API_DELAY_SECONDS = 1.1
EXTERNAL_API_MAX_RETRIES = 3
MUSICBRAINZ_MIN_SCORE = 90
# Île-de-France (lon min, lat max, lon max, lat min) : sinon "Montreuil" peut être celui du Pas-de-Calais
GEOCODING_VIEWBOX = "1.4,49.25,3.6,48.1"
LOCAL_COUNTRY_CODE = "FR"

# curl_cffi imite l'empreinte TLS de Chrome : Cloudflare bloque celle de la librairie requests
IMPERSONATE_BROWSER = "chrome"

# User-Agent, Sec-Ch-Ua* et Accept-Encoding sont fournis par curl_cffi, cohérents avec IMPERSONATE_BROWSER
HEADERS = {
    "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/jxl,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-language":"fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.bandsintown.com/choose-dates/genre/all-genres?calendarTrigger=true",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Upgrade-Insecure-Requests": "1",
}
