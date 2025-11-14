from urllib.request import urlretrieve
from zipfile import ZipFile

BASE_URL = "https://danepubliczne.imgw.pl/pl/datastore/getfiledown/Arch/Telemetria/Meteo/"
YEAR = 2024
MONTH = 9

FILENAME = f"Meteo_{YEAR}-{str(MONTH).zfill(2)}.zip"

file = urlretrieve(f"{BASE_URL}{YEAR}/{FILENAME}", f"{FILENAME}")

with ZipFile(f"{file[0]}", 'r') as zip_ref:
    zip_ref.extractall(f"./{file[0][:-4]}")