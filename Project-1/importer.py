from urllib.request import urlretrieve
from zipfile import ZipFile
from config import BASE_URL, MONTH, YEAR

def import_meteo(output_directory):
    zip_file = f"{output_directory}.zip"

    file = urlretrieve(f"{BASE_URL}{YEAR}/{zip_file}", f"{zip_file}")

    with ZipFile(f"{file[0]}", 'r') as zip_ref:
        zip_ref.extractall(f"./{zip_file[:-4]}")