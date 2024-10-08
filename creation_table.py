import pickle
with open("dico.pickle","rb") as data:
    contenu=pickle.load(data)
print(contenu)