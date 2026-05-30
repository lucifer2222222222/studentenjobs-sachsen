import os, logging
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
CORS(app)

STARTED = datetime.utcnow().isoformat() + "Z"

JOBS = [
    {"id":1,"title":"Crew Member","company":"McDonald's","city":"Dresden","district":"Dresden Mitte","type":"Minijob","timing":"Sofort","category":"🍔 Food","description":"Flexible hours, no experience needed. Apply directly on our website.","url":"https://jobs.mcdonalds.de","via":"mcdonalds.de","is_new":True},
    {"id":2,"title":"Crew Member","company":"McDonald's","city":"Leipzig","district":"Leipzig Mitte","type":"Minijob","timing":"Sofort","category":"🍔 Food","description":"Flexible hours, no experience needed.","url":"https://jobs.mcdonalds.de","via":"mcdonalds.de","is_new":True},
    {"id":3,"title":"Crew Member","company":"McDonald's","city":"Chemnitz","district":"Chemnitz","type":"Minijob","timing":"Sofort","category":"🍔 Food","description":"Flexible hours, no experience needed.","url":"https://jobs.mcdonalds.de","via":"mcdonalds.de","is_new":False},
    {"id":4,"title":"Küchenhelfer/in","company":"Burger King","city":"Dresden","district":"Dresden","type":"Minijob","timing":"Evenings","category":"🍔 Food","description":"Kitchen assistance at Burger King Dresden.","url":"https://www.burgerking.de/jobs","via":"burgerking.de","is_new":True},
    {"id":5,"title":"Barista","company":"Starbucks","city":"Dresden","district":"Dresden Mitte","type":"Werkstudent","timing":"Flexible","category":"🍔 Food","description":"Coffee preparation and customer service.","url":"https://starbucks.com/careers","via":"starbucks.com","is_new":True},
    {"id":6,"title":"Kassierer/in","company":"REWE","city":"Dresden","district":"Dresden","type":"Minijob","timing":"Flexible","category":"🛒 Retail","description":"Checkout and customer service at REWE Dresden.","url":"https://karriere.rewe.de","via":"rewe-group.com","is_new":False},
    {"id":7,"title":"Kassierer/in","company":"REWE","city":"Leipzig","district":"Leipzig","type":"Minijob","timing":"Flexible","category":"🛒 Retail","description":"Checkout and customer service at REWE Leipzig.","url":"https://karriere.rewe.de","via":"rewe-group.com","is_new":False},
    {"id":8,"title":"Regalmitarbeiter/in","company":"Lidl","city":"Dresden","district":"Dresden","type":"Minijob","timing":"Early mornings","category":"🛒 Retail","description":"Stock replenishment at Lidl Dresden.","url":"https://jobs.lidl.de","via":"lidl.de","is_new":False},
    {"id":9,"title":"Regalmitarbeiter/in","company":"Lidl","city":"Chemnitz","district":"Chemnitz","type":"Minijob","timing":"Early mornings","category":"🛒 Retail","description":"Stock replenishment at Lidl Chemnitz.","url":"https://jobs.lidl.de","via":"lidl.de","is_new":True},
    {"id":10,"title":"Kassenmitarbeiter/in","company":"Aldi","city":"Freiberg","district":"Freiberg","type":"Minijob","timing":"Flexible","category":"🛒 Retail","description":"Checkout at Aldi Freiberg.","url":"https://www.aldi-sued.de/karriere","via":"aldi.de","is_new":True},
    {"id":11,"title":"Aushilfe","company":"Edeka","city":"Dresden","district":"Dresden","type":"Minijob","timing":"Flexible","category":"🛒 Retail","description":"General store assistance at Edeka Dresden.","url":"https://verbund.edeka/karriere","via":"edeka.de","is_new":True},
    {"id":12,"title":"Aushilfe","company":"Edeka","city":"Leipzig","district":"Leipzig","type":"Minijob","timing":"Flexible","category":"🛒 Retail","description":"General store assistance at Edeka Leipzig.","url":"https://verbund.edeka/karriere","via":"edeka.de","is_new":False},
    {"id":13,"title":"Verkäufer/in","company":"H&M","city":"Dresden","district":"Dresden Centrum","type":"Minijob","timing":"Weekends","category":"🛒 Retail","description":"Sales and customer service at H&M Dresden.","url":"https://career.hm.com","via":"hm.com","is_new":False},
    {"id":14,"title":"Verkäufer/in","company":"DM Drogerie","city":"Dresden","district":"Dresden","type":"Minijob","timing":"Flexible","category":"💊 Healthcare","description":"Customer service at DM Dresden.","url":"https://www.dm.de/unternehmen/karriere","via":"dm.de","is_new":False},
    {"id":15,"title":"Verkäufer/in","company":"DM Drogerie","city":"Leipzig","district":"Leipzig","type":"Minijob","timing":"Flexible","category":"💊 Healthcare","description":"Customer service at DM Leipzig.","url":"https://www.dm.de/unternehmen/karriere","via":"dm.de","is_new":False},
    {"id":16,"title":"Verkäufer/in","company":"Rossmann","city":"Chemnitz","district":"Chemnitz","type":"Minijob","timing":"Flexible","category":"💊 Healthcare","description":"Customer service at Rossmann Chemnitz.","url":"https://www.rossmann.de/karriere","via":"rossmann.de","is_new":True},
    {"id":17,"title":"Warehouse Assistant","company":"Amazon","city":"Leipzig","district":"Leipzig Süd","type":"Teilzeit","timing":"Weekends","category":"📦 Warehouse","description":"Picking and packing at Amazon Leipzig fulfillment center.","url":"https://amazon.jobs","via":"amazon.jobs","is_new":True},
    {"id":18,"title":"Paketzusteller/in","company":"DHL","city":"Dresden","district":"Dresden","type":"Nebenjob","timing":"Mornings","category":"📦 Warehouse","description":"Package delivery in Dresden area. Driving licence required.","url":"https://careers.dhl.com","via":"careers.dhl.com","is_new":True},
    {"id":19,"title":"Paketzusteller/in","company":"DHL","city":"Leipzig","district":"Leipzig","type":"Nebenjob","timing":"Mornings","category":"📦 Warehouse","description":"Package delivery in Leipzig area.","url":"https://careers.dhl.com","via":"careers.dhl.com","is_new":False},
    {"id":20,"title":"Aushilfe Lager","company":"Hermes","city":"Leipzig","district":"Leipzig","type":"Minijob","timing":"Evenings","category":"📦 Warehouse","description":"Parcel sorting at Hermes Leipzig depot.","url":"https://karriere.hermesworld.com","via":"hermesworld.com","is_new":True},
    {"id":21,"title":"Lagerhelfer/in","company":"DPD","city":"Dresden","district":"Dresden","type":"Minijob","timing":"Early mornings","category":"📦 Warehouse","description":"Parcel sorting at DPD depot Dresden.","url":"https://jobs.dpd.de","via":"dpd.de","is_new":True},
    {"id":22,"title":"Delivery Rider","company":"Lieferando","city":"Dresden","district":"Dresden","type":"Nebenjob","timing":"Evenings/Weekends","category":"🚗 Delivery","description":"Food delivery by bike or scooter in Dresden. Very flexible hours.","url":"https://lieferando.de/jobs","via":"lieferando.de","is_new":True},
    {"id":23,"title":"Delivery Rider","company":"Lieferando","city":"Leipzig","district":"Leipzig","type":"Nebenjob","timing":"Evenings/Weekends","category":"🚗 Delivery","description":"Food delivery in Leipzig. Flexible hours.","url":"https://lieferando.de/jobs","via":"lieferando.de","is_new":False},
    {"id":24,"title":"Rezeptionist/in","company":"Ibis Hotel","city":"Dresden","district":"Dresden","type":"Teilzeit","timing":"Mornings/Evenings","category":"🏨 Hotel","description":"Front desk and guest services at Ibis Hotel Dresden.","url":"https://careers.accor.com","via":"ibis.com","is_new":False},
    {"id":25,"title":"Haushaltshelfer/in","company":"Motel One","city":"Leipzig","district":"Leipzig","type":"Minijob","timing":"Mornings","category":"🏨 Hotel","description":"Room cleaning at Motel One Leipzig.","url":"https://www.motel-one.com/de/jobs","via":"motel-one.com","is_new":True},
    {"id":26,"title":"Kinomitarbeiter/in","company":"CinemaxX","city":"Dresden","district":"Dresden","type":"Nebenjob","timing":"Evenings/Weekends","category":"🎬 Entertainment","description":"Ticket sales and cinema operations at CinemaxX Dresden.","url":"https://cinemaxx.de","via":"cinemaxx.de","is_new":False},
    {"id":27,"title":"Fitnesstrainer/in","company":"McFit","city":"Leipzig","district":"Leipzig","type":"Werkstudent","timing":"Flexible","category":"🎬 Entertainment","description":"Coaching and customer support at McFit Leipzig.","url":"https://mcfit.com","via":"mcfit.com","is_new":False},
    {"id":28,"title":"Markthelfer/in","company":"OBI Baumarkt","city":"Görlitz","district":"Görlitz","type":"Minijob","timing":"Flexible","category":"🔧 Hardware","description":"Customer service and shelf stocking at OBI Görlitz.","url":"https://www.obi.de/unternehmen/karriere","via":"obi.de","is_new":True},
    {"id":29,"title":"Tankwart/in","company":"Aral","city":"Zwickau","district":"Zwickau","type":"Minijob","timing":"Weekends","category":"🏢 Other","description":"Customer service at Aral petrol station Zwickau.","url":"https://www.aral.de/karriere","via":"aral.de","is_new":False},
    {"id":30,"title":"Paketsortierung","company":"Amazon","city":"Leipzig","district":"Leipzig Süd","type":"Minijob","timing":"Early mornings","category":"📦 Warehouse","description":"Early morning parcel sorting at Amazon Leipzig.","url":"https://amazon.jobs","via":"amazon.jobs","is_new":True},
]

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status":"ok","jobs":len(JOBS)})

@app.route("/api/status", methods=["GET"])
def api_status():
    return jsonify({"status":"ok","job_count":len(JOBS),"last_updated":STARTED,"refreshing":False,"next_refresh":"N/A"})

@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    city     = request.args.get("city","").strip()
    category = request.args.get("category","").strip()
    q        = request.args.get("q","").strip().lower()
    limit    = min(int(request.args.get("limit",100)),200)
    offset   = int(request.args.get("offset",0))
    jobs = JOBS
    if city and city.lower() != "all saxony":
        jobs = [j for j in jobs if j["city"].lower()==city.lower()]
    if category and category.lower() != "all jobs":
        cat = category.split(" ",1)[-1].lower() if " " in category else category.lower()
        jobs = [j for j in jobs if cat in j["category"].lower()]
    if q:
        jobs = [j for j in jobs if q in j["title"].lower() or q in j["company"].lower()]
    return jsonify({"total":len(jobs),"offset":offset,"limit":limit,"jobs":jobs[offset:offset+limit],"last_updated":STARTED})

@app.route("/api/cities", methods=["GET"])
def get_cities():
    return jsonify(sorted({j["city"] for j in JOBS}))

@app.route("/api/categories", methods=["GET"])
def get_categories():
    return jsonify(sorted({j["category"] for j in JOBS}))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
