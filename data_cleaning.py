import pandas as pd
df = pd.read_csv("events_bandsintown_v2.csv" , sep=",")
print(len(df))
df.drop_duplicates(inplace=True)
print(len(df))