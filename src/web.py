# Web.py

from flask import Flask, g, render_template, abort, request, redirect, url_for, jsonify
import models
import json
import datetime
from sqlalchemy import func, exists

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

    most_popular_items = g.db.query(models.Price).filter(models.Price.realm_id == realm.id).filter(models.Price.day == datetime.datetime.today().date()) \
                                                         .order_by(models.Price.quantity.desc()).limit(5).all()
    item_names = g.db.query(models.Item).filter(models.Item.id.in_([x.item_id for x in most_popular_items])).all()

    item_name_dict = {x.id:x for x in item_names}
    return render_template("realm.html", realm=realm, popular_items=most_popular_items, names=item_name_dict)


@app.route("/item")
def view_items():
    total_items = g.db.query(models.Item).count()
    return render_template("itemsearch.html", count=total_items)


@app.route("/item/<name>")
def view_item(name):
    items = g.db.query(models.Item).filter(models.Item.name == name).order_by(models.Item.quality.desc()).all()
    if not len(items):
        abort(404)

    return render_template("item.html", items=items, name=name, first_item=items[0])


@app.route("/getprices/<int:id>/<server>/<faction>")
def get_prices(id, server, faction):
    try:
        realm_id = g.db.query(models.Realm.id).filter(models.Realm.slug == server).one()
    except Exception:
        return jsonify(error="No realm exists")

    today = datetime.datetime.now().date()
    before = today - datetime.timedelta(days=30)

    prices = g.db.query(models.Price).filter_by(realm_id=realm_id, faction=faction, item_id=id) \
                                                .filter(models.Price.day.between(before, today)).order_by(models.Price.day).all()

    return jsonify(error=None,
                   data=[((p.day.year, p.day.month, p.day.day), p.bid) for p in prices])



@app.route("/item/search")
def item_search():
    term = request.args.get("term")
    names = g.db.query(models.Item).filter(func.lower(models.Item.name).startswith(term.lower())).distinct().limit(20).all()
    return json.dumps([{"id":x.id, "label":x.name, "value":x.name} for x in names])


@app.before_request
def before_request():
    g.db = models.Session()

@app.after_request
def after_request(r):
    g.db.close()
    return r


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)