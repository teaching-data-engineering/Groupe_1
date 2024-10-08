from time import sleep
import datetime
import random
from scrap_one import scrap_one_page
from save_json import save_json

url = "https://www.bandsintown.com/choose-dates/fetch-next/upcomingEvents?"

date_time_debut = datetime.datetime(2024, 10, 8, 0, 0, 0)
date_time_fin = datetime.datetime(2024, 10, 31, 23, 0, 0)

def scrap_multiple_pages(url,start_date,end_date,max_page=30):
    listecontenu=[]
    date_current=start_date
    date_fin=end_date
    date_fin_jour=datetime.datetime(start_date.year,start_date.month,start_date.day,23,0,0)
    prev=[]
    while date_fin_jour<=date_fin:
        sleep(5+random.uniform(-1, 2))
        date_iso_debut = date_current.isoformat()
        date_iso_fin = date_fin_jour.isoformat()
        stop=False
        j=1
        for j in range(max_page):
            sleep(3+random.uniform(-1, 2))
            contenu=scrap_one_page(url,j,f"{date_iso_debut},{date_iso_fin}")
            save_json(contenu,f"Paris{date_iso_debut}"+"page"+str(j))
            if (contenu == prev):
                break
            else:
                prev=contenu
            listecontenu.append(contenu)
        date_current=date_current+datetime.timedelta(days=1)
        date_fin_jour=date_fin_jour+datetime.timedelta(days=1)
    return listecontenu

print(scrap_multiple_pages(url,date_time_debut,date_time_fin))