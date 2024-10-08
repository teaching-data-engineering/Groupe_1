from geopy.geocoders import Nominatim
import pandas as pd
from datetime import datetime
from creation_table import df

# Coordonnées géographiques

geolocator = Nominatim(user_agent="geopiExercises",timeout=2)

df["locationText"] = df["locationText"].str.lower()
df["venueName"] = df["venueName"].str.lower()

df["adresse_complete"] = df["venueName"] + ', ' + df["locationText"]
liste_lieux = list(set(df["adresse_complete"]))

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
for adresse in list(df["adresse_complete"]):
    liste_lat.append(dico_coordonnees[adresse]['latitude'])
    liste_long.append(dico_coordonnees[adresse]['longitude'])

df["latitude"] = liste_lat
df["longitude"] = liste_long


# Enrichissement date

df[['date', 'heure']] = df['startsAt'].str.split('T', expand=True)

df["Weekend"] = 0

# ### weekend
df["date"] = pd.to_datetime(df["date"])
liste_date = []

for date in list(df["date"]):
    if date.weekday() >= 5:
        liste_date.append(True)
    else : 
        liste_date.append(False)

df["Weekend"]=liste_date

# Nb jour avant l'évènement

date_current = datetime.now()

df["Nb_jours_avant"] = ((df["date"] - date_current).dt.days)+1

# Durée de l'event
if df["endsAt"] is not None:
    df['heure_fin'] = df['endsAt'].str.split('T', expand=True)[1]
else:
    df['heure_fin'] = None

df["heure"] = pd.to_datetime(df["heure"])
df["heure_fin"] = pd.to_datetime(df["heure_fin"])

if df["heure_fin"] is not None:
    df["duree"] = df["heure_fin"]-df["heure"]
else :
    df["duree"] = None

print(df)
