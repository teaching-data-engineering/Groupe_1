import pickle

with open('data.pickle','rb') as fichier:
    data = pickle.load(fichier)

dico = {}
for i in data:
    l = i['events']
    for dic in l:
        k = dic["venueName"]
        v = dic["startsAt"]
        lieu = dic['venueName']
        artiste = dic['artistName']
        dico[k] = (v,lieu,artiste)
print(dico)
