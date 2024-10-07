import requests
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