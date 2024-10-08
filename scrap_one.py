import requests


# Question 8
def scrap_one_page(url_api,num_page):
    url = url_api

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    params = {
        "city_id": 2988507,
        "page": num_page,  # Change le numéro de page ici
        "longitude": 2.3488,
        "latitude": 48.85341,
        "date": "2024-10-07T00:00:00,2024-10-09T22:00:00",
        "genre_query": "all-genres"
    }
    reponse = requests.get(url,headers=headers,params=params).json()

    liste_concert = []
    evenement = reponse["events"]
    for events in evenement:
        dico = {}
        dico["Artiste"] = events["artistName"]
        dico["Salle"] = events['venueName']
        dico["Lieu"] = events['locationText']
        dico["Titre"] = events["title"]
        dico["Date"] = events["startsAt"]
        dico["RSVP"] = events["rsvpCount"]
        dico["page"]=num_page
        liste_concert.append(dico)

    return liste_concert

print(scrap_one_page("https://www.bandsintown.com/choose-dates/fetch-next/upcomingEvents",2))