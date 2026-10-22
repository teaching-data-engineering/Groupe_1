import requests
import pandas as pd

url = "https://www.bandsintown.com/choose-dates/fetch-next/upcomingEvents"

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

try:
    # 3. Envoyer la requête GET
    response = requests.get(url, headers=headers)

    # 4. Vérifier si la requête a réussi (code 200 = OK)
    if response.status_code == 200:
        print("Succès !")
        
        # Si le site renvoie du JSON, on le convertit en dictionnaire Python
        data_json = response.json()
        #print(data_json)
        events = data_json.get("events", [])
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
        print(len(df))


    else:
        print(f"Erreur : Le serveur a répondu avec le code {response.status_code}")

except requests.exceptions.RequestException as e:
    print(f"Erreur lors de la requête : {e}")

