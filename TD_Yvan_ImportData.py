import requests
import pickle
from time import sleep
import random
from datetime import datetime, timedelta


headers = {
    "User-Agent": "Mozilla/5.0"
}

# URL de base
url = "https://www.bandsintown.com/choose-dates/fetch-next/upcomingEvents"

# Dictionnaire de paramètres
params = {
    "date": "2024-10-07T00:00:00,2024-10-09T22:00:00",
    "page": 2,
    "longitude": 2.3488,
    "latitude": 48.85341,
    "genre_query": "all-genres"
}

# Date de début
date_debut = datetime(2024, 10, 7)

# Liste pour stocker les intervalles de dates
date_mois = []

# Générer 30 intervalles de dates
for i in range(30):
    # Calculer les dates de début et de fin pour chaque intervalle
    debut_intervalle = date_debut + timedelta(days=i)
    fin_intervalle = debut_intervalle + timedelta(days=1)  # Intervalle de 1 jours

    # Formater les dates en chaîne de caractères
    intervalle_formate = f"{debut_intervalle.isoformat()},{fin_intervalle.isoformat()}"
    if (fin_intervalle == datetime(2024, 11, 1)):
        break
    # Ajouter à la liste
    date_mois.append(intervalle_formate)

data = []
for j in date_mois:
    k = random.uniform(1,3)
    sleep(k)
    params["date"]=j
    for i in range(1,5):
        params['page']=i
        rep_inter = requests.get(url, headers=headers,params=params).json()
        data.append(rep_inter)




with open('data.pickle', 'wb') as fichier:
    # Sérialiser la liste et l'enregistrer dans le fichier
    pickle.dump(data, fichier)


