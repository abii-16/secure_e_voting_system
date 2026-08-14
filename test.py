import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

connection_string = os.environ.get("MONGO_URI")
if not connection_string:
    raise RuntimeError("MONGO_URI is not set. Add it to your .env file.")

client = MongoClient(connection_string)
db = client["test_database"]
collection = db["students"]

sample_data = {
    "name": "Test User",
    "age": 21,
    "course": "Cyber Security"
}

collection.insert_one(sample_data)
print("Data inserted successfully!")

for doc in collection.find():
    print(doc)
