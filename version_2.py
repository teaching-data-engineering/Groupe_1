import random
import time
import pandas as pd
import requests
from datetime import date, timedelta

# 1. URL de l'API interne
url = "https://www.bandsintown.com/choose-dates/fetch-next/upcomingEvents"

# Date de fin de la collecte : il suffit de la changer (ex : date(2030, 12, 31)), le découpage est automatique
date_fin = date(2026, 11, 30)

# 2. En-têtes nettoyés (sans cookies, sans pseudo-headers ':')
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


def scraper_periode(date_debut, date_fin, ids_vus):
    """Parcourt toutes les pages de la période [date_debut, date_fin].

    Renvoie (nouveaux_events, limite_atteinte, nb_page) :
    - nb_page                 : nombre de pages demandées pour cette période
    - limite_atteinte = True  : l'API répète la même page (limite d'environ 30 pages),
                                la période est coupée et il reste des événements après
    - limite_atteinte = False : page vide, l'API a tout renvoyé jusqu'à date_fin
    """
    periode = f"{date_debut:%Y-%m-%d}T00:00:00,{date_fin:%Y-%m-%d}T23:00:00"
    nouveaux_events = []
    nb_page = 1

    while True:
        # Paramètres de la requête GET (dates et géolocalisation)
        params = {
            "date": periode,
            "page": nb_page,
            "longitude": "2.3488",
            "latitude": "48.85341",
            "genre_query": "all-genres",
        }

        # 3. Envoi de la requête HTTP GET
        response = requests.get(url, headers=headers, params=params)

        # Trop de requêtes : on attend le délai demandé (ou 60 s) puis on redemande la même page
        if response.status_code == 429:
            attente = int(response.headers.get("Retry-After", 60))
            print(f"page {nb_page} : 429 (trop de requêtes), pause de {attente} s")
            time.sleep(attente)
            continue

        if response.status_code != 200:
            print(f"échec page {nb_page} ({response.status_code}) : {response.text[:200]}")
            return nouveaux_events, False, nb_page

        # 4. Traitement des données JSON obtenues
        data = response.json()
        events = data if isinstance(data, list) else data.get("events", [])

        # Page vide : plus aucun événement jusqu'à date_fin
        if not events:
            print(f"page {nb_page} : vide, fin des résultats.\n")
            return nouveaux_events, False, nb_page

        # Page sans nouvel événement : l'API répète la dernière page, limite atteinte
        nouveaux = [event for event in events if event.get("id") not in ids_vus]
        if not nouveaux:
            print(f"page {nb_page} : page répétée, limite de pages atteinte.\n")
            return nouveaux_events, True, nb_page

        print(f"page {nb_page} : {len(nouveaux)} nouveaux événements.")

        ids_vus.update(event.get("id") for event in nouveaux)
        for event in nouveaux:
            nouveaux_events.append({
                "id": event.get("id"),
                "artiste": event.get("artistName"),
                "lieu": event.get("venueName"),
                "debut": event.get("startsAt"),
                "fin" :event.get("endsAt") ,
                "url_evenement": event.get("eventUrl"),
                "streaming" : event.get("streamingEvent") ,
                "watchLiveText" :event.get("watchLiveText")
            })

        nb_page += 1

        # Pause aléatoire entre deux requêtes pour éviter le ban
        time.sleep(random.uniform(2, 5))


# Boucle principale : un curseur de date qui avance tant que la limite de pages coupe la période
events_list = []
ids_vus = set()
curseur = date.today()
nb_periode = 0
nb_pages_total = 0

while curseur <= date_fin:
    nb_periode += 1
    print(f"=== Période {nb_periode} : du {curseur:%d/%m/%Y} au {date_fin:%d/%m/%Y} ===")

    nouveaux, limite_atteinte, nb_pages = scraper_periode(curseur, date_fin, ids_vus)
    events_list.extend(nouveaux)
    nb_pages_total += nb_pages
    print(f"période {nb_periode} : {nb_pages} pages, {len(nouveaux)} nouveaux événements.\n")

    # L'API a tout renvoyé jusqu'à date_fin : collecte terminée
    if not limite_atteinte:
        break

    # Période coupée : on repart du jour du dernier événement récupéré
    # (ce jour a pu être coupé au milieu, on le redemande, ids_vus élimine les doublons)
    if nouveaux:
        dernier_jour = date.fromisoformat(max(event["debut"] for event in nouveaux)[:10])
    else:
        dernier_jour = curseur

    if dernier_jour > curseur:
        curseur = dernier_jour
    else:
        # Une seule journée dépasse la limite de pages : on passe au lendemain pour ne pas boucler à l'infini
        print(f"attention : le {curseur:%d/%m/%Y} dépasse la limite de pages, des événements peuvent manquer.")
        curseur += timedelta(days=1)

# 5. Mise en forme dans un DataFrame Pandas (toutes périodes confondues)
df = pd.DataFrame(events_list)
#print(df)
print(f"{len(df)} événements collectés en {nb_periode} période(s) et {nb_pages_total} pages au total.")

# Exportation CSV
df.to_csv("events_bandsintown_v2.csv", index=False, encoding="utf-8-sig")
