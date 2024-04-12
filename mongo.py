import pymongo

# Connect to MongoDB Atlas
client = pymongo.MongoClient("your_connection_string")
db = client["job_database"]
collection = db["job_collection"]

# Insert scraped job data into MongoDB
for job in job_listings:
    collection.insert_one(job)

print("Job data saved to MongoDB Atlas.")
