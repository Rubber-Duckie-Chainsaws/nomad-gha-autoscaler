from flask import Flask, request
import requests
import pprint

app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<h1>Hello</h1><p>New World!</p>"

@app.route("/github-webhook", methods=["POST"])
def getWebhook():
    data = dict(request.data)
    if data.get("action", "") == "queued":
        print("Dispatching runner")
    else:
        print("Doing nothing")
    return "ok"
