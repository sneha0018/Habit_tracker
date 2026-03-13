from flask import Flask, render_template, request, jsonify
from database import init_db, get_db
import json
from datetime import datetime, date

app = Flask(__name__)

@app.before_request
def setup():
    init_db()

@app.route('/')
def index():
    return render_template('index.html')

# ── Habits CRUD ──────────────────────────────────────────────
@app.route('/api/habits', methods=['GET'])
def get_habits():
    db = get_db()
    habits = db.execute('SELECT * FROM habits ORDER BY created_at').fetchall()
    return jsonify([dict(h) for h in habits])

@app.route('/api/habits', methods=['POST'])
def add_habit():
    data = request.json
    db = get_db()
    db.execute(
        'INSERT INTO habits (name, icon, color, goal, frequency) VALUES (?,?,?,?,?)',
        (data['name'], data.get('icon','⭐'), data.get('color','#a78bfa'),
         data.get('goal', 30), data.get('frequency','daily'))
    )
    db.commit()
    habit = db.execute('SELECT * FROM habits ORDER BY id DESC LIMIT 1').fetchone()
    return jsonify(dict(habit))

@app.route('/api/habits/<int:hid>', methods=['DELETE'])
def delete_habit(hid):
    db = get_db()
    db.execute('DELETE FROM habits WHERE id=?', (hid,))
    db.execute('DELETE FROM logs WHERE habit_id=?', (hid,))
    db.commit()
    return jsonify({'ok': True})

# ── Logs ────────────────────────────────────────────────────
@app.route('/api/log', methods=['POST'])
def toggle_log():
    data = request.json
    hab_id = data['habit_id']
    log_date = data['date']  # "YYYY-MM-DD"
    db = get_db()
    existing = db.execute(
        'SELECT id FROM logs WHERE habit_id=? AND date=?', (hab_id, log_date)
    ).fetchone()
    if existing:
        db.execute('DELETE FROM logs WHERE id=?', (existing['id'],))
        done = False
    else:
        db.execute('INSERT INTO logs (habit_id, date) VALUES (?,?)', (hab_id, log_date))
        done = True
    db.commit()
    return jsonify({'done': done, 'date': log_date})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    month = request.args.get('month')   # "YYYY-MM"
    year  = request.args.get('year')    # "YYYY"
    db = get_db()
    if month:
        rows = db.execute(
            "SELECT * FROM logs WHERE date LIKE ?", (f"{month}-%",)
        ).fetchall()
    elif year:
        rows = db.execute(
            "SELECT * FROM logs WHERE date LIKE ?", (f"{year}-%",)
        ).fetchall()
    else:
        rows = db.execute('SELECT * FROM logs').fetchall()
    return jsonify([dict(r) for r in rows])

# ── Stats ────────────────────────────────────────────────────
@app.route('/api/stats')
def stats():
    today = date.today().isoformat()
    month = today[:7]
    db = get_db()
    habits = db.execute('SELECT * FROM habits').fetchall()
    total = len(habits)
    done_today = db.execute(
        "SELECT COUNT(DISTINCT habit_id) FROM logs WHERE date=?", (today,)
    ).fetchone()[0]
    month_logs = db.execute(
        "SELECT COUNT(*) FROM logs WHERE date LIKE ?", (f"{month}-%",)
    ).fetchone()[0]
    return jsonify({
        'total_habits': total,
        'done_today': done_today,
        'month_logs': month_logs,
        'today': today
    })

if __name__ == '__main__':
    app.run(debug=True)