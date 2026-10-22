import json
import pandas as pd
import requests
from pprint import pprint
# 1. URL de l'API interne
url = "https://www.bandsintown.com/choose-dates/fetch-next/upcomingEvents"

# Paramètres de la requête GET (dates et géolocalisation)
params = {
    "use_current_location": "1",
    "calendarTrigger": "false",
    "date": "2026-10-22T00:00:00,2026-10-31T23:00:00",
}

# 2. En-têtes nettoyés (sans cookies, sans pseudo-headers ':', sans compression br/zstd)
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate",  # On évite br et zstd
    "Referer": "https://www.bandsintown.com/",
    "sec-ch-ua": (
        '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"'
    ),
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
}

# 3. Envoi de la requête HTTP GET
response = requests.get(url, headers=headers, params=params)

# 4. Traitement des données JSON obtenues
if response.status_code == 200:
    data = response.json()
    events = data if isinstance(data, list) else data.get("events", [])

    print(f"✅ succès ({response.status_code}) : {len(events)} événements récupérés.\n")

    # Mise en forme dans un DataFrame Pandas
    events_list = [
        {
            "id": event.get("id"),
            "artiste": event.get("artistName"),
            "lieu": event.get("venueName"),
            "date": event.get("startsAt"),
            "url_evenement": event.get("eventUrl"),
        }
        for event in events
    ]

    df = pd.DataFrame(events_list)

    print(df)

    # Exportation CSV
    #df.to_csv("events_bandsintown_test.scsv", index=False, encoding="utf-8-sig")
