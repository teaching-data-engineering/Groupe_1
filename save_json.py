import json
debut_fichier_json = 'data'


# Question 9
def save_json(response, idx_page):
    contenu = response
    if os.path.exists(debut_fichier_json+str(idx_page)+".json"):
        os.remove(debut_fichier_json+str(idx_page)+".json")
    with open(debut_fichier_json+str(idx_page)+".json", 'w') as fichier:
        json.dump(response, fichier)
