import flask

app = flask.Flask(__name__)
app.config["DEBUG"] = True

HOST = "51.75.204.37"
PORT = 5000


@app.route('/referee', methods=['GET'])
def home():
    return """{"sucess": true}"""


app.run(host=HOST, port=PORT)