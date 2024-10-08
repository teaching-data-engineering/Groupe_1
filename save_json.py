import pickle
fichier_pickle = 'dico.pickle'


# Question 9
def save_json(response, idx_page):
    try:
        with open(fichier_pickle, 'rb') as fichier:
            dico = pickle.load(fichier)
    except FileNotFoundError:
        # Si le fichier n'existe pas, créer un nouveau dictionnaire
        dico = {}

    dico[idx_page] = response

    # 3. Réécrire le fichier pickle avec le dictionnaire mis à jour
    with open(fichier_pickle, 'wb') as fichier:
        pickle.dump(dico, fichier)
    return None
