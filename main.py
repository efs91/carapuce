from math import floor

import flask
from flask import jsonify, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

from sqlalchemy import Table, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship, declarative_base

# Config
HOST = "0.0.0.0"
PORT = 5000

DB_HOST = "localhost"
DB_USER = "carapuce"
DB_PASS = "sbirneb91"
DB_DATABASE = "carapuce"

# Init
app = flask.Flask(__name__)
app.config["DEBUG"] = True
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_DATABASE_URI"] = 'mysql://' + DB_USER + ':' + DB_PASS + '@' + DB_HOST + '/' + DB_DATABASE
db = SQLAlchemy(app)

# Orm
Base = declarative_base()


class Arbitre(Base):
    __tablename__ = "arbitre"
    id = Column(Integer, primary_key=True)
    joueur_id = Column(Integer, ForeignKey('joueur.id'))
    edition_id = Column(Integer, ForeignKey('edition.id'))


class ClassementGroupe(Base):
    __tablename__ = "classement_groupe"
    groupe_id = Column(Integer, ForeignKey('groupe.id'), primary_key=True)
    rang = Column(Integer, primary_key=True)
    joueur_id = Column(Integer, ForeignKey('joueur.id'))
    nb_kills = Column(Integer)
    nb_morts = Column(Integer)
    nb_points = Column(Integer)


class ClassementPartie(Base):
    __tablename__ = "classement_partie"
    partie_id = Column(Integer, ForeignKey('partie.id'), primary_key=True)
    partie = relationship("Partie", back_populates="classements")
    joueur_id = Column(Integer, ForeignKey('joueur.id'))
    joueur = relationship("Joueur", back_populates="classements_parties")
    rang_jeu = Column(Integer, primary_key=True)
    nb_kills = Column(Integer)
    nb_morts = Column(Integer)
    nb_points = Column(Integer)


class Edition(Base):
    __tablename__ = "edition"
    id = Column(Integer, primary_key=True)
    code = Column(String)
    label = Column(String)
    debut_le = Column(DateTime)
    fin_le = Column(DateTime)


class Elimination(Base):
    __tablename__ = "elimination"
    id = Column(Integer, primary_key=True)
    partie_id = Column(Integer, ForeignKey('partie.id'))
    partie = relationship("Partie", back_populates="eliminations")
    eliminated_id = Column(Integer, ForeignKey('joueur.id'))
    eliminated = relationship("Joueur", back_populates="eliminateds", foreign_keys='Elimination.eliminated_id')
    eliminator_id = Column(Integer, ForeignKey('joueur.id'))
    eliminator = relationship("Joueur", back_populates="eliminators", foreign_keys='Elimination.eliminator_id')
    gun_type = Column(String)
    timecode = Column(String)


groupe_joueur_table = Table('groupe_joueur', Base.metadata,
                            Column('groupe_id', ForeignKey('groupe.id'), primary_key=True),
                            Column('joueur_id', ForeignKey('joueur.id'), primary_key=True)
                            )


class Groupe(Base):
    __tablename__ = "groupe"
    id = Column(Integer, primary_key=True)
    tour_id = Column(Integer, ForeignKey('tour.id'))
    code = Column(String)
    arbitre_id = Column(Integer, ForeignKey('arbitre.id'))
    debut_le = Column(DateTime)
    fin_le = Column(DateTime)
    is_validated = Column(Boolean)

    joueurs = relationship(
        "Joueur",
        secondary=groupe_joueur_table,
        back_populates="groupes")

    parties = relationship("Partie", back_populates="groupe")


class Inscription(Base):
    __tablename__ = "inscription"
    id = Column(Integer, primary_key=True)
    edition_id = Column(Integer, ForeignKey('edition.id'))
    joueur_id = Column(Integer, ForeignKey('joueur.id'))
    inscrit_le = Column(DateTime)


class Joueur(Base):
    __tablename__ = "joueur"
    id = Column(Integer, primary_key=True)
    epic_id = Column(String)
    discord_id = Column(String)
    pseudo = Column(String)
    is_valide = Column(Boolean)
    email = Column(String)

    groupes = relationship(
        "Groupe",
        secondary=groupe_joueur_table,
        back_populates="joueurs")
    classements_parties = relationship("ClassementPartie", back_populates="joueur")
    eliminators = relationship("Elimination", back_populates="eliminator", foreign_keys='Elimination.eliminator_id')
    eliminateds = relationship("Elimination", back_populates="eliminated", foreign_keys='Elimination.eliminated_id')


class Partie(Base):
    __tablename__ = "partie"
    id = Column(Integer, primary_key=True)
    groupe_id = Column(Integer, ForeignKey('groupe.id'))
    groupe = relationship("Groupe", back_populates="parties")
    ordre = Column(Integer)
    debut_le = Column(DateTime)
    fin_le = Column(DateTime)

    classements = relationship("ClassementPartie", back_populates="partie")
    eliminations = relationship("Elimination", back_populates="partie")


class Tour(Base):
    __tablename__ = "tour"
    id = Column(Integer, primary_key=True)
    ordre = Column(Integer)
    code = Column(String)
    label = Column(String)
    is_termine = Column(Boolean)
    edition_id = Column(Integer, ForeignKey('edition.id'))
    debut_le = Column(DateTime)
    fin_le = Column(DateTime)
    max_joueurs_par_groupe = Column(Integer)
    comptage = Column(String)


# Routing
@app.route('/group/results', methods=['POST'])
def referee_results():
    payload = request.json
    parse_group_result(payload)
    return jsonify({"success": True})


# Fonctions
def get_composition_tour(liste_joueurs, max_joueurs_par_groupe, is_escargot):
    nb_joueurs = len(liste_joueurs)
    nb_groupes_pleins = floor(nb_joueurs / max_joueurs_par_groupe)
    taille_dernier_groupe = nb_joueurs - (nb_groupes_pleins * max_joueurs_par_groupe)
    nb_groupes = nb_groupes_pleins + (1 if taille_dernier_groupe > 0 else 0)

    groupes = [[] for _ in range(nb_groupes)]
    while len(liste_joueurs) > 0:  # round-robin
        for groupe in groupes:
            groupe.append(liste_joueurs.pop(0))
            if len(liste_joueurs) == 0:
                break
        if is_escargot: groupes.reverse()
    return groupes


def get_current_edition():
    return db.session.query(Edition).filter(Edition.debut_le <= datetime.now(), Edition.fin_le == None).first()


def get_current_tour_by_edition(edition):
    return db.session.query(Tour).filter(Tour.edition_id == edition.id, Tour.is_termine == 0).order_by(
        Tour.ordre).first()


def get_arbitre_by_joueur_and_edition(joueur, edition):
    return db.session.query(Arbitre).filter(Arbitre.edition_id == edition.id, Arbitre.joueur_id == joueur.id).first()


def get_group_by_arbitre_and_tour(arbitre, tour):
    return db.session.query(Groupe).filter(Groupe.arbitre_id == arbitre.id, Groupe.tour_id == tour.id).first()


def get_joueur_by_epic_id(epic_id):
    return db.session.query(Joueur).filter(Joueur.epic_id == epic_id.upper()).first()


def calcul_points(rang, nb_kills, comptage):
    points = min(nb_kills, comptage['max_kills']) * comptage['points_par_kill']
    for top in comptage['points_par_tops']:
        if rang <= int(top):
            points += comptage['points_par_tops'][top]
            break
    return points


def parse_group_result(payload):
    edition = get_current_edition()
    tour = get_current_tour_by_edition(edition)
    print(f"Edition: {edition.code}, Tour: {tour.code}")
    print(f"Arbitre epic_id: {payload['referee_epic_id']}")
    joueur_arbitre = get_joueur_by_epic_id(payload['referee_epic_id'])
    arbitre = get_arbitre_by_joueur_and_edition(joueur_arbitre, edition)
    print(f"Arbitre : {joueur_arbitre.pseudo}")
    groupe = get_group_by_arbitre_and_tour(arbitre, tour)
    print(f"Groupe: {groupe.id} {groupe.code}")
    if groupe.is_validated:
        print("Groupe déja validé")
        return

    lookup = {}
    nb_joueurs = 0
    for joueur in groupe.joueurs:
        lookup[joueur.epic_id] = joueur
        nb_joueurs += 1

    parties = []
    current_partie = {
        "joueurs_restant": [epic_id for epic_id in lookup.keys()],
        "eliminations": [],
        "classements_jeu": [],
        "stat_joueurs": {key: {"nb_kills": 0, "nb_morts": 0} for (key, value) in lookup.items()}
    }

    for elim in payload['eliminations']:

        if elim['eliminated'] == payload['referee_epic_id']:  # Arbitre
            if elim['eliminator'] != payload['referee_epic_id']:
                print(f"{lookup[elim['eliminator']].pseudo} à tué l'arbitre !")
                continue

            print(f"Arbitre auto-éliminé.")
            continue

        lu_or = lookup[elim['eliminator']]
        lu_ed = lookup[elim['eliminated']]

        current_partie["eliminations"].append({
            "eliminator": lu_or,
            "eliminated": lu_ed,
            "timecode": elim['timecode'],
            "gun_type": elim['gunType']
        })

        if elim['eliminator'] == elim['eliminated']:  #  auto-éliminé
            print(f"Joueur {lu_ed.pseudo} auto-éliminé.")
            current_partie["stat_joueurs"][elim['eliminated']]['nb_morts'] += 1
            current_partie["classements_jeu"].append({
                "joueur": lu_ed,
                "rang": len(current_partie['joueurs_restant']),
                "nb_kills": current_partie["stat_joueurs"][elim['eliminated']]['nb_kills'],
                "nb_morts": 1
            })
            current_partie['joueurs_restant'].remove(elim['eliminated'])

        else:  # Elimination
            print(f"Joueur {lu_or.pseudo} à éliminé joueur {lu_ed.pseudo}.")
            current_partie["stat_joueurs"][elim['eliminated']]['nb_morts'] += 1
            current_partie["stat_joueurs"][elim['eliminator']]['nb_kills'] += 1
            current_partie["classements_jeu"].append({
                "joueur": lookup[elim['eliminated']],
                "rang": len(current_partie['joueurs_restant']),
                "nb_kills": current_partie["stat_joueurs"][elim['eliminated']]['nb_kills'],
                "nb_morts": 1
            })
            current_partie['joueurs_restant'].remove(elim['eliminated'])

        if len(current_partie['joueurs_restant']) == 1:  # we have a winner !

            gagnant = lookup[current_partie['joueurs_restant'].pop()]

            print(f"Joueur {gagnant.pseudo} a gagné la partie !")
            current_partie["classements_jeu"].append({
                "joueur": gagnant,
                "rang": 1,
                "nb_kills": current_partie["stat_joueurs"][gagnant.epic_id]['nb_kills'],
                "nb_morts": 0
            })

            parties.append(current_partie)

            current_partie = {
                "joueurs_restant": [epic_id for epic_id in lookup.keys()],
                "eliminations": [],
                "classements_jeu": [],
                "stat_joueurs": {key: {"nb_kills": 0, "nb_morts": 0} for (key, value) in lookup.items()},
            }

    # delete existing eliminations/classements/parties for this groupe
    db.session.query(Elimination).filter(Elimination.partie_id == Partie.id, Partie.groupe_id == groupe.id).delete(
        synchronize_session=False)
    db.session.query(ClassementPartie).filter(ClassementPartie.partie_id == Partie.id,
                                              Partie.groupe_id == groupe.id).delete(synchronize_session=False)
    db.session.query(Partie).filter(Partie.groupe_id == groupe.id).delete(synchronize_session=False)
    db.session.commit()

    comptage = json.loads(tour.comptage)
    print(parties)
    ordre = 1
    for p in parties:
        partie = Partie()
        partie.groupe = groupe
        partie.ordre = ordre
        partie.debut_le = datetime.now()
        partie.fin_le = datetime.now()

        for e in p['eliminations']:
            elimination = Elimination()
            elimination.partie = partie
            elimination.eliminator = e['eliminator']
            elimination.eliminated = e['eliminated']
            elimination.gun_type = e['gun_type']
            elimination.timecode = e['timecode']
            partie.eliminations.append(elimination)

        for c in p['classements_jeu']:
            classement = ClassementPartie()
            classement.partie = partie
            classement.joueur = c['joueur']
            classement.rang_jeu = c['rang']
            classement.nb_kills = c['nb_kills']
            classement.nb_morts = c['nb_morts']
            classement.nb_points = calcul_points(c['rang'], c['nb_kills'], comptage)
            partie.classements.append(classement)
        db.session.add(partie)
        db.session.commit()


#  Main
app.run(host=HOST, port=PORT)
