import requests

url = "https://www.bandsintown.com/all-dates/fetch-next/upcomingEvents?page=4&longitude=2.3488&latitude=48.85341"
header={"User-Agent":"Mozilla/5.0"}

reponse = requests.get(url,headers=header)
print(reponse.json())