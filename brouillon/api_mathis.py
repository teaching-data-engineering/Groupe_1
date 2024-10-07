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
reponse = requests.get(url,headers=headers,params=params).json()
print(reponse)

liste_concert = []
evenement = reponse["events"]
for events in evenement:
    dico = {}
    dico["Artiste"] = events["artistName"]
    dico["Lieu"] = f"{events['venueName']},{events['locationText']}"
    dico["Date"] = events["startsAt"]
    liste_concert.append(dico)

print(liste_concert)

