import pickle

with open('data.pickle','rb') as fichier:
    data = pickle.load(fichier)

print(data[21])