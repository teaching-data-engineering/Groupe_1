from geopy.geocoders import Nominatim
import pandas as pd
from datetime import datetime
from creation_table import df
import re

# Coordonnées géographiques

geolocator = Nominatim(user_agent="geopiExercises",timeout=10)

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

q1 = df["rsvpCount"].quantile(0.25)  # Premier quartile (25%)
q2 = df["rsvpCount"].quantile(0.50)  # Deuxième quartile (50%, médiane)
q3 = df["rsvpCount"].quantile(0.75)
def popularite(val,q1=q1,q2=q2,q3=q3):
    if(val>q3):
        return 'Très populaire'
    elif(val<q1):
        return 'Pas populaire'
    elif(val<q2):
        return 'Peu populaire'
    else:
        return 'Assez populaire'
df["Popularite"]=df["rsvpCount"].apply(popularite)
print(df.columns)
def detectfestival(str):
    if re.search(r"festival",str):
        return 'festival'
    else:
        return 'concert'
df["Type"]=df['artistImageSrc'].apply(detectfestival)

print(df.columns)

