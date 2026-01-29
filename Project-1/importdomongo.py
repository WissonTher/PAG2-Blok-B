import pymongo
import json
connection = pymongo.MongoClient('mongodb+srv://admin:adminadmin@effacility.i7mbxbt.mongodb.net/')
print(connection)
db = connection.mongo
effacility = db.effacility
# bibliografia: https://github.com/rtbigdata/geojson-mongo-import.py/blob/master/geojson-mongo-import.py
# effacility.create_index([("geometry", pymongo.GEOSPHERE)])

data = []
with open('./Project-1/data/effacility.geojson','r', encoding='UTF-8') as f:
  geojson = json.loads(f.read())
for feature in geojson['features']:
    data.append(feature)

result = effacility.insert_many(data, ordered=False)
ile = len(result.inserted_ids)
Szczecin = db.effacility.find_one({'properties.name1':'Szczecin'})
print(Szczecin.get('geometry').get('coordinates'))
connection.close()
# print(ile)