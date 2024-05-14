from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<h1>Hello</h1><p>New World!</p>"
#    return "<h1>Hello</h1><p>World!</p>"
