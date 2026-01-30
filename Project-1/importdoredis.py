import csv
import json
import os
import redis

pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
db = redis.Redis(connection_pool=pool)

path = r"./Meteo_2024-09"

db.flushall()

limit_paczki = 10000
licznik = 0
pipe = db.pipeline()

if not os.path.exists(path):
    print(f"Błąd: Ścieżka {path} nie istnieje.")
else:
    for file in os.listdir(path):
        if not file.endswith(".csv"):
            continue

        full_path = os.path.join(path, file)
        with open(full_path, mode='r', encoding='utf-8') as f:
            czytnik = csv.reader(f, delimiter=';')

            try:
                next(czytnik)
            except StopIteration:
                continue

            for wiersz in czytnik:
                if not wiersz or len(wiersz) < 3:
                    continue

                stacja_id = wiersz[0]
                parametr = wiersz[1]
                pelna_data = wiersz[2]
                wartosc = wiersz[3]

                tylko_data = pelna_data.split(' ')[0] if ' ' in pelna_data else pelna_data
                klucz_redis = f"meteo:{stacja_id}:{tylko_data}"

                rekord = {
                    "ParametrSH": parametr,
                    "Data": pelna_data,
                    "Wartosc": wartosc
                }

                pipe.rpush(klucz_redis, json.dumps(rekord))
                licznik += 1

                if licznik % limit_paczki == 0:
                    pipe.execute()
                    print(f"Załadowano: {licznik} rekordów...")

    pipe.execute()
    print(f"Zakończono! Łącznie przetworzono: {licznik} rekordów.")
