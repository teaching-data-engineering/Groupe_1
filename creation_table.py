import json
import pandas as pd
import os
import re
liste=[]
dossier_script = os.path.dirname(os.path.abspath(__file__))
for fichier in os.listdir(dossier_script):
    if fichier.endswith(".json"):
        with open(fichier,"r") as data:
            contenu=json.load(data)
        liste+=contenu
df = pd.DataFrame(liste)
print(df)
df["rsvpCount"]=df["rsvpCount"].apply(lambda x:int(x))
