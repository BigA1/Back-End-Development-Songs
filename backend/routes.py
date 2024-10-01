from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get("MONGODB_SERVICE")
mongodb_username = os.environ.get("MONGODB_USERNAME")
mongodb_password = os.environ.get("MONGODB_PASSWORD")
mongodb_port = os.environ.get("MONGODB_PORT")

print(f"The value of MONGODB_SERVICE is: {mongodb_service}")

if mongodb_service == None:
    app.logger.error("Missing MongoDB server in the MONGODB_SERVICE variable")
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)


def parse_json(data):
    return json.loads(json_util.dumps(data))


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "OK"})


@app.route("/count", methods=["GET"])
def count():
    return jsonify({"count": db.songs.count_documents({})})


@app.route("/songs", methods=["GET"])
def songs():
    songs = db.songs.find()
    return jsonify({"songs": parse_json(songs)})


@app.route("/song/<int:id>", methods=["GET"])
def get_song_by_id(id):
    song = db.songs.find_one({"id": id})
    if song is None:
        return make_response(jsonify({"message": f"song with id {id} not found"}), 404)
    return jsonify(parse_json(song))


@app.route("/song", methods=["POST"])
def create_song():
    song = request.json
    id = song["id"]
    is_duplicate = db.songs.find_one({"id": id})
    if is_duplicate:
        return make_response(
            jsonify({"message": f"song with id {id} already exists"}), 302
        )
    inserted_id = db.songs.insert_one(song).inserted_id
    return jsonify({"inserted_id": str(inserted_id)})


@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id):
    song = request.json
    does_song_exist = db.songs.find_one({"id": id})
    if does_song_exist is None:
        return make_response(jsonify({"message": "song not found"}), 404)
    update_song_count = db.songs.update_one({"id": id}, {"$set": song})
    if update_song_count.modified_count == 0:
        return make_response(
            jsonify({"message": "song found, but nothing updated"}), 200
        )
    updated_song = db.songs.find_one({"id": id})
    return jsonify(parse_json(updated_song))


@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    song = db.songs.find_one({"id": id})
    if song is None:
        return make_response(jsonify({"message": "song not found"}), 404)
    db.songs.delete_one({"id": id})
    return make_response({}, 204)
