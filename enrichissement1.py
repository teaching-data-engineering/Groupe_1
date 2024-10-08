from geopy.geocoders import Nominatim
import pandas as pd
from datetime import datetime

# dataframe test
data = {'startat': ['2024-10-08T08:00:00', '2024-10-12T09:30:00'], "Lieu":["Ivry-sur-Seine, France", "Paris, France"], "Salle":["adidas arena", "Zenith Paris - La Villette"]}
table = pd.DataFrame(data)


# Coordonnées géographiques

geolocator = Nominatim(user_agent="geopiExercises")

table["Lieu"] = table["Lieu"].str.lower()
table["Salle"] = table["Salle"].str.lower()

table["adresse_complete"] = table["Salle"] + ', ' + table["Lieu"]
liste_lieux = list(set(table["adresse_complete"]))

adresse_paris = "Paris, France"
location_paris = geolocator.geocode(adresse_paris)

dico_coordonnees = {}

for lieu in liste_lieux:
    location= geolocator.geocode(lieu)
    if location :
        latitude = location.latitude
        longitude = location.longitude
        dico_coordonnees[lieu] = {"latitude" : latitude, "longitude":longitude}
    else : 
        dico_coordonnees[lieu] = {"latitude" : location_paris.latitude, "longitude":location_paris.longitude}

liste_lat = []
liste_long = []
for adresse in list(table["adresse_complete"]):
    liste_lat.append(dico_coordonnees[adresse]['latitude'])
    liste_long.append(dico_coordonnees[adresse]['longitude'])

table["latitude"] = liste_lat
table["longitude"] = liste_long


# Enrichissement date

table[['date', 'heure']] = table['startat'].str.split('T', expand=True)

table["Weekend"] = 0

# ### weekend
table["date"] = pd.to_datetime(table["date"])
liste_date = []

for date in list(table["date"]):
    if date.weekday() >= 5:
        liste_date.append(True)
    else : 
        liste_date.append(False)

table["Weekend"]=liste_date

# Nb jour avant l'évènement

date_current = datetime.now()

table["Nb_jours_avant"] = ((table["date"] - date_current).dt.days)+1

print(table)