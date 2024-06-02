import hashlib
import hmac
import os

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

def verify_signature(payload_body, signature_header):
    """Verify that the payload was sent from GitHub by validating SHA256.

    Raise and return 403 if not authorized.

    Args:
        payload_body: original request body to verify (request.body())
        signature_header: header received from GitHub (x-hub-signature-256)


    Lifted from github examples: https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries#python-example
    """
    if not signature_header:
        raise HTTPException(status_code=403, detail="x-hub-signature-256 header is missing!")
    secret_token = os.environ['GITHUB_SECRET']
    hash_object = hmac.new(secret_token.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)
    del secret_token
    expected_signature = "sha256=" + hash_object.hexdigest()
    if not hmac.compare_digest(expected_signature, signature_header):
        raise HTTPException(status_code=403, detail="Request signature didn't match!")

@app.route("/github-webhook", methods=["POST"])
def getWebhook():
    app.logger.info("Getting data as dictionary")
    payload = request.data
    header_signature = request.headers['X-Hub-Signature-256']
    verify_signature(payload, header_signature)
    data = dict(request.json)
    app.logger.info(data.get("action", ""))
    if data.get("action", "") == "queued":
        app.logger.info("Dispatching runner")
        # We don't restart the container when nomad updates the env variable
        # that corresponds to our token (for renewals). So grab it every
        # time we want to use it. Technically there is a race condition
        # a retry x3 loop or some such should probably resolve
        acl_token = os.environ["NOMAD_TOKEN"]
        # The job doesn't take parameters but the api gets mad at an empty body
        # hence the Meta field with nothing in it
        r = requests.post('http://nomad.service.consul:4646/v1/job/github-runner/dispatch', json={'Meta': {}}, headers={"X-Nomad-Token": acl_token})
        app.logger.info(r.text)
    else:
        app.logger.info("Doing nothing")
        app.logger.info(data.get("action", ""))
    return "ok"
