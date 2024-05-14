from flask import Flask, request
import pprint

app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<h1>Hello</h1><p>New Worlds!</p>"
#    return "<h1>Hello</h1><p>World!</p>"

@app.route("/github-webhook", methods=["POST"])
def getWebhook():
    data = request.data
    pprint.pp(data)
    return "ok"

