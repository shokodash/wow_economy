# Web.py

from flask import Flask, g, render_template, abort
import models
import datetime

app = Flask(__name__)

@app.route('/')
def index():
    realm_count = g.db.query(models.Realm).count()
    return render_template("index.html",realm_count=realm_count)

@app.route('/realm')
def realms():
    realms = g.db.query(models.Realm).order_by(models.Realm.name.asc()).all()
    return render_template("realms.html",realms=realms)

@app.route("/realm/<realm>")
def view_realm(realm):
    try:
        realm = g.db.query(models.Realm).filter(models.Realm.slug == realm).one()
    except Exception:
        abort(404)

    most_popular_items = g.db.query(models.Price.item_id).filter(models.Price.day == datetime.datetime.today()).order_by(models.Price.quantity.desc()).limit(5).all()
    item_names = g.db.query(models.Item).filter(models.Item.name.in_([x.item_id for x in most_popular_items])).all()

    item_name_dict = {x.id:x for x in item_names}
    return render_template("realm.html", realm=realm, popular_items=most_popular_items, names=item_name_dict)

@app.before_request
def before_request():
    g.db = models.Session()

@app.after_request
def after_request(r):
    g.db.close()
    return r


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)#, debug=True)