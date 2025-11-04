from pymongo import MongoClient
from pymongo.write_concern import WriteConcern
from gridfs import GridFS
import os

# Connect to MongoDB and return database
db = MongoClient(os.environ.get('MONGODB_URI'), tls=True)['socialbook']
db['users'].create_index('username', unique=True)
db['posts'].create_index('_id')

# Return users collection
def get_db_users(operation):
    return db['users'] if operation == "read" else db['users'].with_options(write_concern=WriteConcern(w=1, j=True))

# Return posts collection
def get_db_posts(operation):
    return db['posts'] if operation == "read" else db['posts'].with_options(write_concern=WriteConcern(w=1, j=True))

def get_db_file(operation):
    return GridFS(db) if operation == "read" else GridFS(db.with_options(write_concern=WriteConcern(w=1, j=True)))