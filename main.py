import requests
from flask import Flask, request
from logging.config import dictConfig

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<h1>Hello</h1><p>New World!</p>"

#TODO: Secrets next
@app.route("/github-webhook", methods=["POST"])
def getWebhook():
    app.logger.info("Getting data as dictionary")
    data = dict(request.json)
    app.logger.info(data.get("action", ""))
    if data.get("action", "") == "queued":
        app.logger.info("Dispatching runner")
        r = requests.post('http://10.0.1.81:4646/v1/job/github_runner/dispatch', data={'empty': 'body'})
        app.logger.info(r.text)
    else:
        app.logger.info("Doing nothing")
        app.logger.info(data.get("action", ""))
    return "ok"
