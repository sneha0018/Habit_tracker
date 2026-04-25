from flask import Flask, render_template, request, jsonify, redirect, session, url_for
from database import init_db, get_db
from werkzeug.security import generate_password_hash, check_password_hash
import json
from datetime import datetime, date
from datetime import timedelta
import sqlite3
app = Flask(__name__)
app.secret_key = "your_secret_key"

@app.before_request
def setup():
    init_db()


# ── Habits CRUD ──────────────────────────────────────────────
@app.route('/api/habits', methods=['GET'])
def get_habits():
    if 'user_id' not in session:
        return jsonify([])

    user_id = session['user_id']
    db = get_db()

    habits = db.execute(
        'SELECT * FROM habits WHERE user_id = ? ORDER BY created_at',
        (user_id,)
    ).fetchall()

    return jsonify([dict(h) for h in habits])

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        conn = sqlite3.connect('habits.db')
        c = conn.cursor()

        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
        except:
            return "User already exists"

        return redirect('/login')

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('habits.db')
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = c.fetchone()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            return redirect('/')
        else:
            return "Invalid credentials"

    return render_template('login.html')

@app.route('/api/habits', methods=['POST'])
def add_habit():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    user_id = session['user_id']   # 🔥 ADD THIS

    db = get_db()
    db.execute(
        'INSERT INTO habits (name, icon, color, goal, frequency, user_id) VALUES (?,?,?,?,?,?)',
        (
            data['name'],
            data.get('icon','⭐'),
            data.get('color','#a78bfa'),
            data.get('goal', 30),
            data.get('frequency','daily'),
            user_id   # 🔥 ADD THIS
        )
    )
    db.commit()

    habit = db.execute(
        'SELECT * FROM habits WHERE user_id = ? ORDER BY id DESC LIMIT 1',
        (user_id,)
    ).fetchone()

    return jsonify(dict(habit))

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    return render_template('index.html')

    return render_template('index.html')

@app.route('/api/habits/<int:hid>', methods=['DELETE'])
def delete_habit(hid):
    db = get_db()
    db.execute('DELETE FROM habits WHERE id=?', (hid,))
    db.execute('DELETE FROM logs WHERE habit_id=?', (hid,))
    db.commit()
    return jsonify({'ok': True})


def calculate_streak(habit_id):
    try:
        today = date.today().isoformat()
        db = get_db()

        logs = db.execute(
            'SELECT date FROM logs WHERE habit_id=? ORDER BY date DESC',
            (habit_id,)
        ).fetchall()
        log_dates = [row['date'] for row in logs]

        habit = db.execute(
            'SELECT freeze_available, freeze_date, longest_streak FROM habits WHERE id=?',
            (habit_id,)
        ).fetchone()

        count, freeze_used, check_date = 0, False, date.today()

        for _ in range(365):
            date_str = check_date.isoformat()
            if date_str in log_dates:
                count += 1
            else:
                if freeze_used or habit['freeze_available'] != 1:
                    break
                can_freeze = habit['freeze_date'] is None or \
                             (date.today() - date.fromisoformat(habit['freeze_date'])).days > 7
                if can_freeze:
                    freeze_used = True
                else:
                    break
            check_date -= timedelta(days=1)

        if freeze_used:
            db.execute('UPDATE habits SET freeze_available=0, freeze_date=? WHERE id=?', (today, habit_id))
        if count > (habit['longest_streak'] or 0):
            db.execute('UPDATE habits SET longest_streak=? WHERE id=?', (count, habit_id))
        db.execute('UPDATE habits SET streak=? WHERE id=?', (count, habit_id))
        db.commit()
        return count

    except Exception as e:
        print(f"STREAK ERROR: {e}")   # ← will print exact error in terminal
        return 0                       # ← returns 0 instead of crashing

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
    new_streak = calculate_streak(hab_id)        # ← add this
    return jsonify({'done': done, 'date': log_date, 'streak': new_streak})

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
    if 'user_id' not in session:
        return jsonify({})

    user_id = session['user_id']
    today = date.today().isoformat()
    month = today[:7]
    db = get_db()

    # Get user's habits
    habits = db.execute(
        'SELECT id FROM habits WHERE user_id = ?',
        (user_id,)
    ).fetchall()

    habit_ids = [h['id'] for h in habits]

    total = len(habit_ids)

    if total == 0:
        return jsonify({
            'total_habits': 0,
            'done_today': 0,
            'month_logs': 0,
            'today': today
        })

    # Convert to tuple for SQL
    placeholders = ','.join(['?'] * len(habit_ids))

    # Done today (ONLY user's habits)
    done_today = db.execute(
        f"SELECT COUNT(DISTINCT habit_id) FROM logs WHERE date=? AND habit_id IN ({placeholders})",
        [today] + habit_ids
    ).fetchone()[0]

    # Monthly logs
    month_logs = db.execute(
        f"SELECT COUNT(*) FROM logs WHERE date LIKE ? AND habit_id IN ({placeholders})",
        [f"{month}-%"] + habit_ids
    ).fetchone()[0]

    return jsonify({
        'total_habits': total,
        'done_today': done_today,
        'month_logs': month_logs,
        'today': today
    })

if __name__ == '__main__':
    app.run(debug=True)