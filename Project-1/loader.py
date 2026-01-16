from config import MONTH, YEAR
import os
import pandas as pd
from importer import import_meteo

METEO_DIR = f"./Meteo_{YEAR}-{str(MONTH).zfill(2)}"
import_meteo()

directory = os.fsencode(METEO_DIR)

RESULTS = {
    0: [],
    1: [],
    2: [],
    3: [],
    4: [],
    5: [],
    6: [],
    7: [],  
    8: [],
    9: []
}

for i, file in enumerate(os.listdir(directory)):
    filename = os.fsdecode(file)
    if filename.endswith(".csv"): 
        df = pd.read_csv(f"{METEO_DIR}/{filename}", delimiter=";", header=None)
        RESULTS[i] = df
    else:
        continue

print(RESULTS[0])