import pymongo

connection = pymongo.MongoClient('mongodb+srv://pag2:haslomongo@effacility.i7mbxbt.mongodb.net/')
print(connection)
db = connection.mongo
effacility = db.effacility
Szczecin = connection.mongo.effacility.find_one({'properties.name1':'Szczecin'})
print(Szczecin.get('geometry').get('coordinates'))
connection.close()
