from curl_cffi import requests
import json
import time
import pandas as pd

url = "https://www.bandsintown.com/choose-dates/fetch-next/upcomingEvents"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.bandsintown.com/",
    "X-Requested-With": "XMLHttpRequest"
}

tous_les_evenements = []

# Génère automatiquement toutes les dates du 23 oct. au 30 nov. 2026 inclus
dates = pd.date_range(start="2026-10-23", end="2026-11-30", freq="D")

# 1. Boucle sur chaque jour
for jour in dates:
    date_str = jour.strftime("%Y-%m-%d")
    plage_date = f"{date_str}T00:00:00,{date_str}T23:59:59"
    print(f"\n--- Récupération du {date_str} ---")

    # 2. Boucle sur les pages de ce jour-là
    for i in range(1, 152):
        params = {
            "city_id": "2988507",
            "date": plage_date,
            "page": i,
            "longitude": "2.3522",
            "latitude": "48.8566",
            "genre_query": "all-genres"
        }

        try:
            response = requests.get(
                url, 
                headers=headers, 
                params=params, 
                impersonate="chrome", 
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            events = data.get("events", [])
            
            # Si la page est vide, on a fini ce jour : on sort de la boucle 'i' pour passer au jour suivant
            if not events:
                print(f"Fin du {date_str} à la page {i-1}.")
                break
                
            tous_les_evenements.extend(events)
            print(f"  Page {i} : +{len(events)} événements (Total cumulé : {len(tous_les_evenements)})")
            
            time.sleep(1)  # Pause anti-ban Cloudflare

        except Exception as e:
            print(f"  Erreur le {date_str} (page {i}) : {e}")
            break  # Passe au jour suivant en cas de souci sur une page

# --- SAUVEGARDE FINALE ---
if tous_les_evenements:
    # 1. Fichier JSON complet
    with open("evenements_23oct_30nov.json", "w", encoding="utf-8") as f:
        json.dump({"events": tous_les_evenements}, f, ensure_ascii=False, indent=4)

    # 2. DataFrame Pandas + Fichier CSV dédoublonné
    colonnes = ["id", "startsAt", "timezone", "artistName", "locationText"]
    df = pd.DataFrame(tous_les_evenements).reindex(columns=colonnes)
    df = df.drop_duplicates(subset=["id"])
    
    df.to_csv("evenements_23oct_30nov.csv", index=False, encoding="utf-8-sig")
    print(f"\nTerminé ! {len(df)} événements uniques sauvegardés dans 'evenements_23oct_30nov.csv'.")