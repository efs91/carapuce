import random
from math import floor

import flask
from flask import jsonify, request, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

from sqlalchemy import Table, Column, Integer, String, Boolean, DateTime, ForeignKey, null, func, asc, desc, text
from sqlalchemy.orm import relationship, declarative_base

# Config
HOST = "0.0.0.0"
PORT = 5000

DB_HOST = "efs91.fr"
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
    edition = relationship("Edition", back_populates="arbitres")

    groupes = relationship('Groupe', back_populates="arbitre")


class ClassementGroupe(Base):
    __tablename__ = "classement_groupe"
    groupe_id = Column(Integer, ForeignKey('groupe.id'), primary_key=True)
    groupe = relationship("Groupe", back_populates="classements")
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
    config = Column(String)
    tours = relationship("Tour", back_populates="edition")

    inscriptions = relationship('Inscription', back_populates="edition")
    arbitres = relationship('Arbitre', back_populates="edition")


class Elimination(Base):
    __tablename__ = "elimination"
    id = Column(Integer, primary_key=True)
    groupe_id = Column(Integer, ForeignKey('groupe.id'))
    groupe = relationship("Groupe", back_populates="eliminations")
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
    tour = relationship("Tour", back_populates="groupes")
    code = Column(String)
    arbitre_id = Column(Integer, ForeignKey('arbitre.id'))
    arbitre = relationship('Arbitre', back_populates="groupes")
    debut_le = Column(DateTime)
    fin_le = Column(DateTime)
    has_resultats = Column(Boolean)
    is_validated = Column(Boolean)

    joueurs = relationship(
        "Joueur",
        secondary=groupe_joueur_table,
        back_populates="groupes")

    parties = relationship("Partie", back_populates="groupe")
    classements = relationship("ClassementGroupe", back_populates="groupe")
    eliminations = relationship("Elimination", back_populates="groupe")


class Inscription(Base):
    __tablename__ = "inscription"
    id = Column(Integer, primary_key=True)
    edition_id = Column(Integer, ForeignKey('edition.id'))
    edition = relationship('Edition', back_populates="inscriptions")
    joueur_id = Column(Integer, ForeignKey('joueur.id'))
    joueur = relationship("Joueur", back_populates="inscriptions")
    inscrit_le = Column(DateTime)
    is_elimine = Column(Boolean)
    is_participe = Column(Boolean)
    participe_le = Column(DateTime)


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

    inscriptions = relationship("Inscription", back_populates="joueur")


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
    edition = relationship("Edition", back_populates="tours")
    debut_le = Column(DateTime)
    fin_le = Column(DateTime)
    config = Column(String)

    groupes = relationship("Groupe", back_populates="tour")


# Routing


@app.route("/admin", methods=['GET'])
def http_get_admin():
    edition = get_current_edition()
    return redirect(f"/admin/edition/{edition.id}")


@app.route("/admin/edition/<edition_id>", methods=['GET'])
def http_get_admin_edition(edition_id):
    edition = get_edition_by_id(edition_id)
    classements = get_classements(edition=edition)
    return render_template("edition.html", edition=edition, current_tour_code=None, classements=classements)


@app.route("/admin/edition/<edition_id>/init", methods=['POST'])
def http_get_admin_edition_init(edition_id):
    edition = get_edition_by_id(edition_id)
    init_edition(edition)
    return redirect(f"/admin/edition/{edition.id}")


@app.route("/admin/edition/<edition_id>/resultats", methods=['get'])
def http_get_admin_edition_resultats(edition_id):
    edition = get_edition_by_id(edition_id)
    classements = get_classements(edition=edition, show_rangs=True)
    return render_template("edition_resultats.html", edition=edition, classements=classements)

@app.route("/admin/edition/<edition_id>/liste_attente", methods=['get'])
def http_get_admin_edition_resultats(edition_id):
    edition = get_edition_by_id(edition_id)
    classements = get_classements_and_is_participe(edition=edition, show_rangs=True)
    return render_template("edition_liste_attente.html", edition=edition, classements=classements)


@app.route("/admin/groupe/<groupe_id>/joueur/<joueur_id>/elimine", methods=['POST'])
def http_get_admin_joueur_elimine(groupe_id, joueur_id):
    groupe = get_groupe_by_id(groupe_id)
    joueur = get_joueur_by_id(joueur_id)
    elimine_joueur(groupe, joueur)
    return redirect(f"/admin/groupe/{groupe.id}")


@app.route("/admin/edition/<edition_id>/delete_tours", methods=['POST'])
def http_get_admin_edition_delete_tour(edition_id):
    edition = get_edition_by_id(edition_id)
    db.session.query(Tour).filter(Tour.edition == edition).delete()
    db.session.commit()
    return redirect(f"/admin/edition/{edition.id}")


@app.route("/admin/tour/<tour_id>/init", methods=['POST'])
def http_get_admin_tour_init(tour_id):
    tour = get_tour_by_id(tour_id)
    init_tour(tour)
    return redirect(f"/admin/edition/{tour.edition.id}")


@app.route("/admin/groupe/<groupe_id>", methods=['GET'])
def http_get_admin_groupe(groupe_id):
    edition = get_current_edition()
    tour = get_current_tour_by_edition(edition)
    groupe = get_groupe_by_id(groupe_id)
    return render_template("groupe.html", edition=edition, tour=tour, groupe=groupe)


@app.route("/admin/groupe/<groupe_id>/delete", methods=['POST'])
def http_get_admin_groupe_delete(groupe_id):
    groupe = get_groupe_by_id(groupe_id)
    edition_id = groupe.tour.edition.id
    groupe.joueurs.clear()
    db.session.delete(groupe)
    db.session.commit()
    return redirect(f"/admin/edition/{edition_id}")


@app.route("/admin/groupe/<groupe_id>/delete_classements", methods=['POST'])
def http_get_admin_groupe_delete_classements(groupe_id):
    groupe = get_groupe_by_id(groupe_id)
    edition_id = groupe.tour.edition.id

    db.session.query(Elimination).filter(Elimination.partie_id == Partie.id, Partie.groupe_id == groupe.id).delete(
        synchronize_session=False)
    db.session.query(ClassementPartie).filter(ClassementPartie.partie_id == Partie.id,
                                              Partie.groupe_id == groupe.id).delete(synchronize_session=False)
    db.session.query(Partie).filter(Partie.groupe_id == groupe.id).delete(synchronize_session=False)
    groupe.has_resultats = False;
    db.session.commit()
    return redirect(f"/admin/edition/{edition_id}")


@app.route("/admin/groupe/<groupe_id>/push_resultats", methods=['POST'])
def http_get_admin_groupe_push_resultats(groupe_id):
    eliminations = json.loads(request.form.get("eliminations_json"))
    groupe = get_groupe_by_id(groupe_id)
    parse_group_result(eliminations, groupe)
    return redirect(f"/admin/edition/{groupe.tour.edition.id}")


@app.route('/group/results', methods=['POST'])
def referee_results():
    payload = request.json
    parse_group_result(payload)
    return jsonify({"success": True})


@app.route('/admin/participation', methods=['POST'])
def http_post_admin_participation():
    try:
        payload = request.json
        print(payload)
        joueur = get_joueur_by_discord_id(payload['discord_id'])
        if not joueur:
            raise Exception(f"discord_id inconnue : {payload['discord_id']}")
        message = set_etat_participation(joueur, payload['etat'])
        print(message)
        return jsonify({"success": True, "message": message})
    except BaseException as err:
        return jsonify({"success": False, "message": str(err)})




@app.route("/admin/groupe/<groupe_id>/validate", methods=['POST'])
def http_post_admin_groupe_validate(groupe_id):
    edition = get_current_edition()
    groupe = get_groupe_by_id(groupe_id)
    groupe.is_validated = True
    db.session.commit()
    return redirect('/admin')


@app.route("/admin/groupe/<groupe_id>/unvalidate", methods=['POST'])
def http_post_admin_groupe_unvalidate(groupe_id):
    edition = get_current_edition()
    tour = get_current_tour_by_edition(edition)
    groupe = get_groupe_by_id(groupe_id)
    groupe.is_validated = False
    db.session.commit()
    return redirect('/admin')


@app.route("/admin/partie/<partie_id>", methods=['GET'])
def http_get_admin_partie(partie_id):
    partie = get_partie_by_id(partie_id)
    return render_template("partie.html", partie=partie)


# Fonctions
def init_edition(edition):
    config = get_edition_config(edition)

    if len(edition.tours) > 0:
        raise Exception('Edition contient deja des tours')

    for idx, config_tour in enumerate(config['tours'], start=1):
        tour = Tour()
        tour.ordre = idx
        tour.edition = edition
        tour.label = config_tour['label']
        tour.code = edition.code + 'T' + str(config_tour['ordre'])
        tour.is_termine = False
        tour.config = json.dumps(config_tour)
        db.session.add(tour)
        db.session.flush()

    db.session.commit()


def init_tour(tour):
    config_tour = json.loads(tour.config)
    joueurs = []
    if config_tour['composition'] == 'ALL':
        for i in tour.edition.inscriptions:
            if not i.is_elimine:
                joueurs.append(i.joueur)
        random.shuffle(joueurs)
    elif config_tour['composition'] == 'TOP-ABS-GENERAL':
        for c in get_classements(edition=tour.edition):
            joueurs.append(c.Joueur)
        joueurs = joueurs[:config_tour['max_joueurs_par_groupe']]
    else:
        raise Exception(f"composition {config_tour['composition']} invalide.")

    listes_joueurs = get_composition_tour(joueurs, config_tour['max_joueurs_par_groupe'],
                                          config_tour['algo'] == 'ESCARGOT')

    arbitres_restants = tour.edition.arbitres.copy()

    i = 1
    for liste in listes_joueurs:
        groupe = Groupe()
        groupe.tour = tour
        groupe.code = tour.code + 'G' + str(i)
        groupe.is_validated = False
        groupe.has_resultats = False

        if len(arbitres_restants) == 0 and config_tour['nb_arbitres_par_groupe'] > 0:
            raise Exception("Plus d'arbitre disponible.")

        if config_tour['nb_arbitres_par_groupe'] > 0:
            groupe.arbitre = arbitres_restants.pop()

        for joueur in liste:
            groupe.joueurs.append(joueur)

        db.session.add(groupe)
        db.session.flush()

        i += 1

    db.session.commit()

    return tour


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
    return db.session.query(Edition).filter(Edition.debut_le <= datetime.now(), Edition.fin_le == null()).first()


def get_edition_by_id(edition_id):
    return db.session.query(Edition).filter(Edition.id == edition_id).first()


def get_tour_by_id(tour_id):
    return db.session.query(Tour).filter(Tour.id == tour_id).first()


def get_current_tour_by_edition(edition):
    return db.session.query(Tour).filter(Tour.edition_id == edition.id, Tour.is_termine == 0).order_by(
        Tour.ordre).first()


def get_arbitre_by_joueur_and_edition(joueur, edition):
    return db.session.query(Arbitre).filter(Arbitre.edition_id == edition.id, Arbitre.joueur_id == joueur.id).first()


def get_groupe_by_id(groupe_id):
    return db.session.query(Groupe).filter(Groupe.id == groupe_id).first()


def get_partie_by_id(partie_id):
    return db.session.query(Partie).filter(Partie.id == partie_id).first()


def get_group_by_arbitre_and_tour(arbitre, tour):
    return db.session.query(Groupe).filter(Groupe.arbitre_id == arbitre.id, Groupe.tour_id == tour.id).first()


def get_joueur_by_epic_id(epic_id):
    return db.session.query(Joueur).filter(Joueur.epic_id == epic_id.upper()).first()


def get_joueur_by_discord_id(discord_id):
    return db.session.query(Joueur).filter(Joueur.discord_id == discord_id).first()


def get_joueur_by_id(joueur_id):
    return db.session.query(Joueur).filter(Joueur.id == joueur_id).first()


def get_inscription_by_edition_and_joueur(edition, joueur):
    return db.session.query(Inscription).filter(Inscription.edition == edition, Inscription.joueur == joueur).first()


def calcul_points(rang, nb_kills, comptage):
    points = min(nb_kills, comptage['max_kills']) * comptage['points_par_kill']
    for top in comptage['points_par_tops']:
        if rang <= int(top):
            points += comptage['points_par_tops'][top]
            break
    return points


def elimine_joueur(groupe, joueur):
    inscription = get_inscription_by_edition_and_joueur(groupe.tour.edition, joueur)
    inscription.is_elimine = True
    db.session.commit()


def set_etat_participation(joueur, etat):

    edition = get_current_edition()
    inscription = get_inscription_by_edition_and_joueur(edition, joueur)
    message = ""

    if not inscription:
        raise Exception(f"Inscription introuvable")

    if etat == 'CONFIRME':
        if inscription.is_participe is None:
            message += "Ta participation a bien été confirmée, merci."
            inscription.participe_le = datetime.now()
            inscription.is_participe = True
        elif inscription.is_participe:
            message += f"Tu as déja confirmé ta participation le {inscription.participe_le}"
        else:
            message += f"Tu avais indiqué le {inscription.participe_le} ton refus de participer. Ta confirmation de " \
                        f"participer a bien été enregistrée."
            inscription.participe_le = datetime.now()
            inscription.is_participe = True
    elif etat == 'REFUSE':
        if inscription.is_participe is None:
            message += "Ton refus de participer a bien été pris en compte, merci."
            inscription.participe_le = datetime.now()
            inscription.is_participe = False
        elif inscription.is_participe:
            message += f"Tu avais confirmé ta participation le {inscription.participe_le}. Ton refus de participer a " \
                       f"bien été enregistré."
            inscription.participe_le = datetime.now()
            inscription.is_participe = False
        else:
            message += f"Tu as déja indiqué le {inscription.participe_le} ton refus de participer."

    else:
        raise Exception(f"Etat inconnu : {etat}")

    db.session.commit()

    return message


def get_classements(edition=None, tour=None, groupe=None, partie=None, joueur=None, show_rangs=False):
    query = db.session.query(
        Joueur,
        func.sum(ClassementPartie.nb_points).label('nb_points'),
        func.sum(ClassementPartie.nb_morts).label('nb_morts'),
        func.sum(ClassementPartie.nb_kills).label('nb_kills')
    ).filter(
        Tour.edition_id == edition.id,
        Groupe.tour_id == Tour.id,
        Partie.groupe_id == Groupe.id,
        ClassementPartie.partie_id == Partie.id,
        Groupe.is_validated == True,
        groupe_joueur_table.c.groupe_id == Groupe.id,
        Joueur.id == groupe_joueur_table.c.joueur_id,
        ClassementPartie.joueur_id == Joueur.id,
    ).group_by(Joueur.id).order_by(desc("nb_points"), asc("nb_morts"), desc("nb_kills"))
    if edition: query.filter(Edition.id == edition.id)
    if tour: query.filter(Tour.id == tour.id)
    if groupe: query.filter(Groupe.id == groupe.id)
    if partie: query.filter(Partie.id == partie.id)
    if joueur: query.filter(Joueur.id == joueur.id)

    # from sqlalchemy.dialects import mysql
    # sql = query.compile(dialect=mysql.dialect());
    # sql = str(query);

    res = query.all()

    if show_rangs:
        rangs = []
        rang = 1
        for classement in res:
            rangs.append( dict({
                "rang" : rang,
                "classement": classement
            }))
            rang += 1
        res = rangs

    return res



def get_classements_and_is_participe(edition=None, tour=None, groupe=None, partie=None, joueur=None, show_rangs=False):
    query = db.session.query(
        Joueur,
        func.sum(ClassementPartie.nb_points).label('nb_points'),
        func.sum(ClassementPartie.nb_morts).label('nb_morts'),
        func.sum(ClassementPartie.nb_kills).label('nb_kills')
    ).filter(
        Inscription.is_participe == True,
        Tour.edition_id == edition.id,
        Groupe.tour_id == Tour.id,
        Partie.groupe_id == Groupe.id,
        ClassementPartie.partie_id == Partie.id,
        Groupe.is_validated == True,
        groupe_joueur_table.c.groupe_id == Groupe.id,
        Joueur.id == groupe_joueur_table.c.joueur_id,
        ClassementPartie.joueur_id == Joueur.id,
    ).group_by(Joueur.id).order_by(desc("nb_points"), asc("nb_morts"), desc("nb_kills"))
    if edition: query.filter(Edition.id == edition.id)
    if tour: query.filter(Tour.id == tour.id)
    if groupe: query.filter(Groupe.id == groupe.id)
    if partie: query.filter(Partie.id == partie.id)
    if joueur: query.filter(Joueur.id == joueur.id)

    # from sqlalchemy.dialects import mysql
    # sql = query.compile(dialect=mysql.dialect());
    # sql = str(query);

    res = query.all()

    if show_rangs:
        rangs = []
        rang = 1
        for classement in res:
            rangs.append( dict({
                "rang" : rang,
                "classement": classement
            }))
            rang += 1
        res = rangs

    return res




def get_edition_config(edition):
    print(edition.config)
    return json.loads(edition.config)


def parse_group_result(payload, groupe=False):
    if not groupe:
        edition = get_current_edition()
    else:
        edition = groupe.tour.edition
    tour = get_current_tour_by_edition(edition)
    print(f"Edition: {edition.code}, Tour: {tour.code}")
    payload['referee_epic_id'] = payload['referee_epic_id'].upper()
    print(f"Arbitre epic_id: {payload['referee_epic_id']}")

    has_arbitre = False
    if not len(payload['referee_epic_id']) == 0:
        joueur_arbitre = get_joueur_by_epic_id(payload['referee_epic_id'])
        arbitre = get_arbitre_by_joueur_and_edition(joueur_arbitre, edition)
        print(f"Arbitre : {joueur_arbitre.pseudo}")
        has_arbitre = True

    if not has_arbitre and not groupe:
        raise Exception("Impossible de determiner le groupe (pas d'arbitre, pas de groupe).")

    if not groupe:
        groupe = get_group_by_arbitre_and_tour(arbitre, tour)
    print(f"Groupe: {groupe.id} {groupe.code}")
    if groupe.is_validated:
        print("Groupe déja validé")
        return

    lookup = {}
    nb_joueurs = 0
    for joueur in groupe.joueurs:
        inscription = get_inscription_by_edition_and_joueur(edition, joueur)
        if not inscription.is_elimine:
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

        print(f"{elim['timecode']} : {elim['eliminator']} -> {elim['eliminated']}------------------------------")
        if has_arbitre and elim['eliminated'] == payload['referee_epic_id']:  # Arbitre
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

        if elim['eliminator'] == elim['eliminated']:  # auto-éliminé
            print(f"Joueur {lu_ed.pseudo} auto-éliminé.")
            current_partie["stat_joueurs"][elim['eliminated']]['nb_morts'] += 1
            classement = {
                "joueur": lu_ed,
                "rang": len(current_partie['joueurs_restant']),
                "nb_kills": current_partie["stat_joueurs"][elim['eliminated']]['nb_kills'],
                "nb_morts": 1
            }
            print(classement)
            current_partie["classements_jeu"].append(classement)
            current_partie['joueurs_restant'].remove(elim['eliminated'])

        else:  # Elimination
            print(f"Joueur {lu_or.pseudo} à éliminé joueur {lu_ed.pseudo}.")
            current_partie["stat_joueurs"][elim['eliminated']]['nb_morts'] += 1
            current_partie["stat_joueurs"][elim['eliminator']]['nb_kills'] += 1

            classement = {
                "joueur": lookup[elim['eliminated']],
                "rang": len(current_partie['joueurs_restant']),
                "nb_kills": current_partie["stat_joueurs"][elim['eliminated']]['nb_kills'],
                "nb_morts": 1
            }
            print(classement)
            current_partie["classements_jeu"].append(classement)
            if not elim['eliminated'] in current_partie['joueurs_restant']:
                print(f" {elim['eliminated']} n'est pas dans les ids restantes")
            current_partie['joueurs_restant'].remove(elim['eliminated'])

        real_restants = []
        for epic_id in current_partie['joueurs_restant']:
            joueur = get_joueur_by_epic_id(epic_id)
            inscription = get_inscription_by_edition_and_joueur(edition, joueur)
            if not inscription.is_elimine:
                real_restants.append(joueur)

        if len(real_restants) == 1:  # we have a winner !
            gagnant = real_restants.pop()

            print(f"Joueur {gagnant.pseudo} a gagné la partie !")
            classement = {
                "joueur": gagnant,
                "rang": 1,
                "nb_kills": current_partie["stat_joueurs"][gagnant.epic_id]['nb_kills'],
                "nb_morts": 0
            }
            print(classement)
            current_partie["classements_jeu"].append(classement)

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

    config = get_edition_config(tour.edition)
    print(parties)
    ordre = 0
    for p in parties:
        ordre += 1
        partie = Partie()
        partie.groupe = groupe
        partie.ordre = ordre
        partie.debut_le = datetime.now()
        partie.fin_le = datetime.now()

        for e in p['eliminations']:
            elimination = Elimination()
            elimination.groupe = groupe
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
            classement.nb_points = calcul_points(c['rang'], c['nb_kills'], config['comptage'])
            partie.classements.append(classement)
        db.session.add(partie)

    groupe.has_resultats = True
    db.session.commit()


# Main
app.run(host=HOST, port=PORT)
