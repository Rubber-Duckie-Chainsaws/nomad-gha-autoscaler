from flask import Flask, request
import requests
import pprint

app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<h1>Hello</h1><p>New World!</p>"

@app.route("/github-webhook", methods=["POST"])
def getWebhook():
    data = dict(request.json)
    if data.get("action", "") == "queued":
        print("Dispatching runner")
        r = requests.post('http://10.0.1.81:4646/v1/job/github_runner/dispatch', data={})
        print(r.text)
    else:
        print("Doing nothing")
        print(data.get("action", ""))
    return "ok"
