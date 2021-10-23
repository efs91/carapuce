import flask
from flask import jsonify, request
from flask_sqlalchemy import SQLAlchemy


# Config
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship, declarative_base

HOST = "0.0.0.0"
PORT = 5000

DB_HOST = "efs91.fr"
DB_USER = "carapuce"
DB_PASS = "sbirneb91"
DB_DATABASE = "carapuce"

# Main
app = flask.Flask(__name__)
app.config["DEBUG"] = True
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_DATABASE_URI"] = 'mysql://'+DB_USER+':'+DB_PASS+'@'+DB_HOST+'/'+DB_DATABASE
db = SQLAlchemy(app)


# Orm
Base = declarative_base()


class Edition(Base):
    __tablename__ = "edition"
    id = Column(Integer, primary_key=True)


class Joueur(Base):
    __tablename__ = "joueur"
    id = Column(Integer, primary_key=True)
    epic_id = Column(Integer)
    discord_id = Column(String)
    pseudo = Column(String)
    is_valid = Column(Boolean)
    email = Column(Boolean)

    arbitre = relationship("Arbitre",  back_populates="joueur")


class Arbitre(Base):
    __tablename__ = "arbitre"
    id = Column(Integer, primary_key=True)
    joueur_id = Column(Integer, ForeignKey('joueur.id'))
    edition_id = Column(Integer, ForeignKey('edition.id'))

    joueur = relationship("Joueur", back_populates="arbitre")


# Routing
@app.route('/referee/results', methods=['POST'])
def referee_results():
    payload = request.json
    print('Arbitre: ' + payload['referee_epic_id'])

    toto = Joueur()
    toto.epic_id = 'sqfssqfds'

    db.session.add(toto);
    db.session.commit()

    for elim in payload.elimination:
        pass

    return jsonify({"success": True})


app.run(host=HOST, port=PORT)


