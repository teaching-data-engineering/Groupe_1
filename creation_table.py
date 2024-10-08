import pickle
import pandas as pd
with open("dico.pickle","rb") as data:
    contenu=pickle.load(data)
listeglobale=[]
for i in contenu.values():
    listeglobale+=i
df = pd.DataFrame(listeglobale)
print(df)