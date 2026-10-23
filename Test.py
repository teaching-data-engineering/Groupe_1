import json
import pandas as pd
import requests
from pprint import pprint
from datetime import date
# Liste qui accumule les événements de toutes les pages

# 1. URL de l'API interne
url = "https://www.bandsintown.com/choose-dates/fetch-next/upcomingEvents"

events_list = []

# Période de recherche : d'aujourd'hui au 30/11/2026
date_debut = date.today()
date_fin = date(2026, 11, 30)
periode = f"{date_debut:%Y-%m-%d}T00:00:00,{date_fin:%Y-%m-%d}T23:00:00"

# Paramètres de la requête GET (dates et géolocalisation)
nb_page = 1
ids_vus = set()  # id des événements déjà récupérés, pour détecter les pages en double
while True:
    params = {
        "date": periode,
        "page": nb_page,
        "longitude": "2.3488",
        "latitude": "48.85341",
        "genre_query": "all-genres",
    }

    # 2. En-têtes nettoyés (sans cookies, sans pseudo-headers ':', sans compression br/zstd)
    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36",
    "Accept" : "text/html,application/xhtml+xml,application/xml;q=0.9,image/jxl,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-language" : "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding" : "gzip, deflate, br, zstd",
    "Referer" : "https://www.bandsintown.com/choose-dates/genre/all-genres?calendarTrigger=true",
    "Sec-Ch-Ua": '"Google Chrome";v="155", "Chromium";v="155", "Not(A:Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Upgrade-Insecure-Requests" : "1"
}

    # 3. Envoi de la requête HTTP GET
    response = requests.get(url, headers=headers, params=params)

    # 4. Traitement des données JSON obtenues
    if response.status_code == 200:
        data = response.json()
        events = data if isinstance(data, list) else data.get("events", [])

        print(f"page {nb_page} : succès ({response.status_code}) : {len(events)} événements récupérés.\n")

        # Page vide ou déjà vue (l'API répète la dernière page à l'infini) : on s'arrête
        nouveaux = [event for event in events if event.get("id") not in ids_vus]
        if not nouveaux:
            print(f"page {nb_page} : aucun nouvel événement (page en double), arrêt.\n")
            break
        ids_vus.update(event.get("id") for event in nouveaux)

        # Ajout des nouveaux événements de cette page à la liste globale
        for event in nouveaux:
            events_list.append({
                "id": event.get("id"),
                "artiste": event.get("artistName"),
                "lieu": event.get("venueName"),
                "debut": event.get("startsAt"),
                "fin" :event.get("endsAt") ,
                "url_evenement": event.get("eventUrl"),
                "streaming" : event.get("streamingEvent") ,
                "watchLiveText" :event.get("watchLiveText")
            })
    else:
        print(f"échec page {nb_page} ({response.status_code})")
        break

    nb_page += 1

# 5. Mise en forme dans un DataFrame Pandas (après la boucle, toutes pages confondues)
df = pd.DataFrame(events_list)
print(df)
print(nb_page)

# Exportation CSV
df.to_csv("events_bandsintown_test.csv", index=False, encoding="utf-8-sig")
