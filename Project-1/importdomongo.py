import pymongo
import json
from pyproj import Transformer
transformer1992 = Transformer.from_crs("EPSG:2180", "EPSG:4326")
transformer2000 = Transformer.from_crs("EPSG:2176", "EPSG:4326")
connection = pymongo.MongoClient('mongodb+srv://admin:adminadmin@effacility.i7mbxbt.mongodb.net/')
db = connection.mongo
effacility = db.effacility
effacility.create_index([("geometry", pymongo.GEOSPHERE)])

data = []
with open('./data/effacility.geojson','r', encoding='UTF-8') as f:
  geojson = json.loads(f.read())
for feature in geojson['features']:
    geo = feature['geometry']['coordinates']
    uklad = len(str(int(geo[1])))
    if uklad == 6:
        feature['geometry']['coordinates'] = transformer1992.transform(geo[1], geo[0])
    else:
        feature['geometry']['coordinates'] = transformer2000.transform(geo[1], geo[0])
    data.append(feature)

result = effacility.insert_many(data, ordered=False)
# ile = len(result.inserted_ids)
# Szczecin = db.effacility.find_one({'properties.name1':'Szczecin'})
# print(Szczecin.get('geometry').get('coordinates'))
connection.close()
