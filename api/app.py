from flask import Flask, request, jsonify
from flask_restful import Api, Resource
import bcrypt
import spacy
from box import Box as Fmt
from pymongo import MongoClient


app = Flask(__name__)
api = Api(app)


client = MongoClient("db", 27017)
db = client.db
users = db.users


def user_exists(username):
    if users.find_one({"username": username}):
        return True
    else:
        return False


def gen_res(code, msg):
    res = {
        "status": code,
        "message": msg
    }
    return jsonify(res)


def get_hashed(password):
    hashed_pw = bcrypt.hashpw(password.encode('utf8'),
                              bcrypt.gensalt())
    return hashed_pw


def valid_user(username, password):
    if user_exists(username):
        user = Fmt(users.find_one({"username": username}))
        if bcrypt.checkpw(password.encode('utf8'), user.password):
            return True
        else:
            return False
    else:
        return False


def get_tokens(username):
    user = Fmt(users.find_one({"username": username}))
    return user.tokens


def set_tokens(username, tokens):
    if user_exists(username):
        users.update_one({"username": username}, {
            "$set": {"tokens": tokens}
        })


class Register(Resource):
    def post(self):
        posted_data = Fmt((request.get_json()))
        if user_exists(posted_data.username):
            return gen_res(301, "Sorry! Username is already taken.")
        else:
            hashed_pw = get_hashed(posted_data.password)
            users.insert_one({
                "username": posted_data.username,
                "password": hashed_pw,
                "tokens": 10
            })
            return gen_res(200, "Successfully Registered!")


class Test(Resource):
    def post(self):
        posted_data = Fmt(request.get_json())
        username = posted_data.username
        password = posted_data.password

        if not user_exists(username):
            return gen_res(302, "Sorry! You are not registered!")

        if valid_user(username, password):
            if get_tokens(username) > 0:
                if posted_data.text1 and posted_data.text2:
                    nlp = spacy.load("en_core_web_sm")
                    text1 = nlp(posted_data.text1)
                    text2 = nlp(posted_data.text2)
                    similarity_ratio = text1.similarity(text2)
                    res = {
                        "status": 200,
                        "message": "Analyzation successull!",
                        "match_ratio": similarity_ratio
                    }
                    set_tokens(get_tokens(username)-1)
                    return jsonify(res)
                else:
                    return gen_res(303, "Please send two pieces of text.")
            else:
                return gen_res(304, "Not enough tokens!")
        else:
            return gen_res(305, "Inavlild username/password")


class Refill(Resource):
    def post(self):
        posted_data = Fmt((request.get_json()))
        username = posted_data.username
        admin_pw = posted_data.admin_pw
        refill_amount = posted_data.refill_amount
        if valid_user("Admin", admin_pw):
            if user_exists(username):
                set_tokens(username, refill_amount)
                return gen_res(200, "Successfully added token!")
            else:
                return gen_res(301, "User Does not exist.")


api.add_resource(Register, '/register')
api.add_resource(Test, '/test')
api.add_resource(Refill, '/refill')


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
