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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/jxl,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-language":"fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Referer": "https://www.bandsintown.com/choose-dates/genre/all-genres?calendarTrigger=true",
    "Sec-Ch-Ua": '"Google Chrome";v="155", "Chromium";v="155", "Not(A:Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Upgrade-Insecure-Requests": "1",
}
