import requests
import pickle

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

data = []
for i in range(1,20):
    params['page']=i
    response = requests.get(url, headers=headers,params=params)
    rep_inter = response.json()
    data.append(rep_inter)

with open('data.pickle', 'wb') as fichier:
    # Sérialiser la liste et l'enregistrer dans le fichier
    pickle.dump(data, fichier)


