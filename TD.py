import requests
import re
from time import sleep
from datetime import datetime
import random
from api_mathis import scrap_one_page

url = "https://www.bandsintown.com/choose-dates/fetch-next/upcomingEvents?"

date_time_debut = datetime(2024, 10, 7, 0, 0, 0)
date_time_fin = datetime(2024, 10, 31, 23, 0, 0)

def scrap_multiple_pages(url,start_date,end_date,max_page=30):
    header={"User-Agent":"Mozilla/5.0"}
    listecontenu=[]
    date_current=start_date
    date_fin=end_date
    date_fin_jour=datetime(start_date.year,start_date.month,start_date.day,23,0,0)
    while date_fin_jour<=date_fin:
        sleep(5+random.uniform(-1, 2))
        date_iso_debut = date_current.isoformat()
        date_iso_fin = date_fin_jour.isoformat()
        stop=False
        j=1
        while stop==False:
            sleep(3+random.uniform(-1, 2))
            contenu=scrap_one_page(url,j,f"{date_iso_debut},{date_iso_fin}")
            if(contenu["urlForNextPageOfEvents"]==None | contenu == prev |j>=max_page):
                stop=True
            else:
                j+=1
                prev=contenu
            listecontenu.append(contenu)
        date_current=date_current+datetime.timedelta(days=1)
        date_fin_jour=date_fin_jour+datetime.timedelta(days=1)
    return listecontenu

