import json
import pandas as pd
import os
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
q1 = df["rsvpCount"].quantile(0.25)  # Premier quartile (25%)
q2 = df["rsvpCount"].quantile(0.50)  # Deuxième quartile (50%, médiane)
q3 = df["rsvpCount"].quantile(0.75)
def popularite(val,q1=q1,q2=q2,q3=q3):
    if(val>q3):
        return 'Très populaire'
    elif(val<q1):
        return 'Pas populaire'
    elif(val<q2):
        return 'Peu populaire'
    else:
        return 'Assez populaire'
df["Popularite"]=df["rsvpCount"].apply(popularite)
print(df.columns)
    