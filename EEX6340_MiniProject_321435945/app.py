from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import datetime
import os

app = Flask(__name__)
DATA_FILE = 'data/purchases.json'
SHOPPING_FILE = 'data/shopping_list.json'  # separate shopping list

# Load JSON data
def load_data(file=DATA_FILE):
    if not os.path.exists(file):
        return []
    with open(file, 'r') as f:
        return json.load(f)

# Save JSON data
def save_data(data, file=DATA_FILE):
    os.makedirs(os.path.dirname(file), exist_ok=True)
    with open(file, 'w') as f:
        json.dump(data, f, indent=4)

# Healthier substitute suggestions
def healthier_substitute(item):
    substitutes = {
        "bread": "brown bread",
        "soda": "sparkling water",
        "butter": "olive oil",
        "chocolate": "dark chocolate",
        "milk": "low-fat milk or almond milk",
        "coconut oil": "olive oil",
        "wheat flour": "Atta flour",
        "bun": "Cereal",
        "juice bottle": "Home made fruit juices",
        "white rice": "red rice"
    }
    return substitutes.get(item.lower(), None)

# Calculate expiry date automatically
def calculate_expiry(name, purchase_date):
    name = name.lower()
    if name in ["milk", "bread", "bun"]:
        return purchase_date + datetime.timedelta(days=3)
    elif name in ["wheat flour", "coconut oil"]:
        return purchase_date + datetime.timedelta(days=60)
    elif name in ["fruits","eggs"]:
        return purchase_date + datetime.timedelta(days=7)
    elif name in ["butter", "cheese"]:
        return purchase_date + datetime.timedelta(days=30)
    else:
        return purchase_date + datetime.timedelta(days=90)

# Detect expiring items
def expiring_items(purchases):
    expiring = []
    today = datetime.date.today()
    for item in purchases:
        exp_date = datetime.datetime.strptime(item['expiry'], '%Y-%m-%d').date()
        days_left = (exp_date - today).days

        if days_left < 0:
            status = "expired"
        elif days_left <= 3:
            status = "high" if days_left <= 1 else "medium"
        else:
            continue

        expiring.append({
            "name": item['name'],
            "expiry": exp_date.strftime('%Y-%m-%d'),
            "purchase": item['purchase'],
            "days_left": max(days_left, 0),
            "status": status
        })
    return expiring

# Rule-based suggestions for items bought last week
def rule_based_suggestions(purchases):
    today = datetime.date.today()
    suggestions = []
    for item in purchases:
        purchase_date = datetime.datetime.strptime(item['purchase'], '%Y-%m-%d').date()
        if 0 <= (today - purchase_date).days <= 7:  # bought in last 7 days
            suggestions.append({"name": item['name']})
    return suggestions

# Main route
@app.route("/", methods=["GET", "POST"])
def index():
    purchases = load_data()
    shopping_list = load_data(SHOPPING_FILE)
    
    if request.method == "POST":
        name = request.form.get("name")
        purchase_str = request.form.get("purchase")
        if purchase_str:
            purchase_date = datetime.datetime.strptime(purchase_str, "%Y-%m-%d").date()
        else:
            purchase_date = datetime.date.today()

        expiry_date = calculate_expiry(name, purchase_date)

        purchases.append({
            "name": name,
            "purchase": purchase_date.strftime("%Y-%m-%d"),
            "expiry": expiry_date.strftime("%Y-%m-%d")
        })
        save_data(purchases)
        return redirect(url_for("index"))

    suggestions = rule_based_suggestions(purchases)
    expiring = expiring_items(purchases)

    return render_template("index.html",
                           purchases=purchases,
                           suggestions=[],  # leave empty; healthy substitutes handled dynamically
                           expiring=expiring,
                           rule_suggestions=suggestions,
                           shopping_list=shopping_list)

# Handle Yes/No response for rule-based suggestion
@app.route("/shopping_response/<item>/<response>")
def shopping_response(item, response):
    shopping_list = load_data(SHOPPING_FILE)
    added = False
    if response.lower() == "yes" and item not in shopping_list:
        shopping_list.append(item)
        save_data(shopping_list, SHOPPING_FILE)
        added = True
    return jsonify({"added": added})

# Healthier substitute route
@app.route("/substitute/<item>")
def substitute(item):
    sub = healthier_substitute(item)
    return jsonify({"substitute": sub})

if __name__ == "__main__":
    app.run(debug=True)
