import requests
import datetime

# Question 8
def scrap_one_page(url_api,num_page,date):
    url = url_api

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    params = {
        "city_id": 2988507,
        "page": num_page,  # Change le numéro de page ici
        "longitude": 2.3488,
        "latitude": 48.85341,
        "date": date,
        "genre_query": "all-genres"
    }
    reponse = requests.get(url,headers=headers,params=params).json()

    liste_concert = []
    evenement = reponse["events"]
    for events in evenement:
        liste_concert.append(events)

    return liste_concert


date_time_debut = datetime.datetime(2024, 10, 8, 0, 0, 0)
date_time_fin = datetime.datetime(2024, 10, 31, 23, 0, 0)
date_iso_debut = date_time_debut.isoformat()
date_iso_fin = date_time_fin.isoformat()
print(scrap_one_page("https://www.bandsintown.com/choose-dates/fetch-next/upcomingEvents",2,f"{date_iso_debut},{date_iso_fin}"))