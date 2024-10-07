import requests

url = "https://www.bandsintown.com/all-dates/fetch-next/upcomingEvents?"
header={"User-Agent":"Mozilla/5.0"}

reponse = requests.get(url,headers=header,params={"page":4,"longitude":"2.3488","latitude":"48.85341"})
print(reponse.json())