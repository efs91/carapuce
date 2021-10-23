import flask

app = flask.Flask(__name__)
app.config["DEBUG"] = True


@app.route('/referee', methods=['GET'])
def home():
    return """{"sucess": true}"""


app.run()
