import requests
<<<<<<< HEAD
import re
from time import sleep
from datetime import datetime
import random
url = "https://www.bandsintown.com/choose-dates/fetch-next/upcomingEvents?"
header={"User-Agent":"Mozilla/5.0"}
listecontenu=[]
for i in range(7,32):
    sleep(5+random.uniform(-1, 2))
    date_time_debut = datetime(2024, 10, i, 0, 0, 0)
    date_time_fin = datetime(2024, 10, i, 23, 0, 0)
    date_iso_debut = date_time_debut.isoformat()
    date_iso_fin = date_time_fin.isoformat()
    stop=False
    j=1
    while stop==False:
        sleep(3+random.uniform(-1, 2))
        contenu=scrap_one_page()
        if(contenu["urlForNextPageOfEvents"]==None & contenu in listecontenu):
            stop=True
        else:
            j+=1
        listecontenu.append(contenu)
print(listecontenu)

def scrap_multiple_pages(url):
    header={"User-Agent":"Mozilla/5.0"}
    listecontenu=[]
    for i in range(7,32):
        sleep(5+random.uniform(-1, 2))
        date_time_debut = datetime(2024, 10, i, 0, 0, 0)
        date_time_fin = datetime(2024, 10, i, 23, 0, 0)
        date_iso_debut = date_time_debut.isoformat()
        date_iso_fin = date_time_fin.isoformat()
        stop=False
        j=1
        while stop==False:
            sleep(3+random.uniform(-1, 2))
            contenu=scrap_one_page()
            if(contenu["urlForNextPageOfEvents"]==None & contenu in listecontenu):
                stop=True
            else:
                j+=1
            listecontenu.append(contenu)
    print(listecontenu)
=======

# URL de l'API
url = "https://www.bandsintown.com/this-month/fetch-next/upcomingEvents"

headers = {
    "User-Agent": "Mozilla/5.0"
}

params = {
    "city_id": 2988507,
    "page": 2,  # Change le numéro de page ici
    "longitude": 2.3488,
    "latitude": 48.85341,
    "genre_query": "all-genres"
}
reponse = requests.get(url,headers=headers,params=params)
print(reponse.json())
>>>>>>> 4ae1bf83ff1a20c68ca6fc14b10175264bcfb83b
