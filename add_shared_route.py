import re

with open('app.py', 'r') as f:
    app_py = f.read()

route_code = """
@app.route("/shared/<int:item_id>", methods=["GET"])
def shared_curriculum(item_id):
    item = db.session.get(SearchHistory, item_id)
    if not item:
        return jsonify({"error": "Curriculum not found"}), 404
        
    try:
        curr_data = json.loads(item.curriculum)
    except Exception:
        curr_data = []
        
    return render_template("shared.html", skill=item.skill, curriculum=curr_data)
"""

if "@app.route(\"/shared/<int:item_id>" not in app_py:
    app_py = app_py.replace('if __name__ == "__main__":', route_code + '\nif __name__ == "__main__":')
    with open('app.py', 'w') as f:
        f.write(app_py)
