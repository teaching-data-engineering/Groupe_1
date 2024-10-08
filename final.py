from scrap_one import scrap_one_page
from save_json import save_json
from datetime import datetime


# Question 10
def scrap_multiple_pages(start_date, end_date, max_page):
    url = pass

    for i in range(max_page):
        reponse = scrap_one_page(url,i)
        save_json(reponse)

# Question 11
def f11():
    scrap_multiple_pages(datetime(2024,10,7),datetime(2024,11,1),5)