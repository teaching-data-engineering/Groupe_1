import requests

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