import flask
from flask import jsonify, request

app = flask.Flask(__name__)
app.config["DEBUG"] = True

HOST = "0.0.0.0"
PORT = 5000


@app.route('/referee/results', methods=['POST'])
def referee_results():
    payload = request.json
    print('Arbitre: ' + payload['epic_id'])
    return jsonify({"success": True})


app.run(host=HOST, port=PORT)