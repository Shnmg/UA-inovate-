from flask import Flask, request, jsonify
import sqlite3
import datetime
from collections import defaultdict

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # For proper emoji display

# Constants
VALID_CATEGORIES = ['groceries', 'transport', 'utilities', 'entertainment', 
                   'dining', 'shopping', 'subscription', 'other']
ESSENTIAL_CATEGORIES = ['groceries', 'transport', 'utilities']

def create_db():
    conn = sqlite3.connect('spending_ai.db')
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            streak_days INTEGER DEFAULT 0
        )
    ''')

    # Transactions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            category TEXT,
            mood TEXT,
            timestamp DATETIME,
            flagged BOOLEAN,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Cooldowns
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cooldowns (
            user_id INTEGER,
            category TEXT,
            expires_at DATETIME,
            PRIMARY KEY (user_id, category),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Budgets
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS budgets (
            user_id INTEGER,
            category TEXT,
            monthly_limit REAL,
            current_spend REAL DEFAULT 0,
            PRIMARY KEY (user_id, category),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Spending patterns (for heatmap)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS spending_patterns (
            user_id INTEGER,
            category TEXT,
            day_of_week INTEGER,
            hour_of_day INTEGER,
            amount REAL,
            timestamp DATETIME,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()

# Helper Functions
def is_impulsive(user_id, amount, category, mood, timestamp):
    if category in ESSENTIAL_CATEGORIES:
        return False
        
    if isinstance(timestamp, str):
        dt = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    else:
        dt = timestamp
        
    hour = dt.hour
    is_late_night = hour >= 22 or hour <= 4
    
    conn = sqlite3.connect('spending_ai.db')
    cursor = conn.cursor()
    
    # Same-day spending
    cursor.execute('''
        SELECT COUNT(*) FROM transactions 
        WHERE user_id=? AND date(timestamp)=date(?)
    ''', (user_id, dt))
    daily_transactions = cursor.fetchone()[0]
    
    # Recent purchases
    cursor.execute('''
        SELECT COUNT(*) FROM transactions 
        WHERE user_id=? AND timestamp > datetime(?, '-1 hour')
    ''', (user_id, dt))
    recent_transactions = cursor.fetchone()[0]
    
    is_stressed = mood and "stress" in mood.lower()
    
    # Category-specific rules
    if category == 'entertainment':
        flagged = amount > 50 or (is_late_night and amount > 20)
    elif category == 'shopping':
        flagged = amount > 75 or (is_stressed and amount > 30)
    else:
        flagged = (
            (is_late_night and amount > 20) or
            (amount > 50 and recent_transactions >= 2) or
            (is_stressed and amount > 30) or
            (daily_transactions > 5 and amount > 10)
        )
    
    conn.close()
    return flagged

def detect_recurring(user_id, category, amount):
    conn = sqlite3.connect('spending_ai.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT amount, COUNT(*) as count 
        FROM transactions 
        WHERE user_id=? AND category=?
        AND timestamp > datetime('now', '-30 days')
        GROUP BY amount
        HAVING count >= 2
        ORDER BY count DESC
    ''', (user_id, category))
    
    for rec_amount, count in cursor.fetchall():
        if abs(rec_amount - amount) <= (rec_amount * 0.15):
            return True, rec_amount
    return False, None

# API Endpoints
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    
    conn = sqlite3.connect('spending_ai.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO users (username, password) 
            VALUES (?, ?)
        ''', (username, password))
        conn.commit()
        return jsonify({"message": "User registered successfully!"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists"}), 400
    finally:
        conn.close()

@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    # Debugging: Print raw request data
    print("\n=== New Transaction Request ===")
    print("Headers:", dict(request.headers))
    print("Raw data:", request.data.decode('utf-8'))
    
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": "Invalid or empty JSON"}), 400
            
        # Debugging: Print parsed JSON
        print("\n=== Parsed JSON Data ===")
        print("Type:", type(data))
        print("Content:", data)
        
        # Validate required fields
        required_fields = ['user_id', 'amount', 'category']
        if not all(field in data for field in required_fields):
            return jsonify({
                "error": "Missing required fields",
                "required": required_fields,
                "received": list(data.keys())
            }), 400

        # Robust amount parsing with detailed error reporting
        print("\n=== Parsing Amount ===")
        print("Original amount value:", data['amount'])
        print("Amount type:", type(data['amount']))
        
        try:
            amount_str = str(data['amount']).strip().replace(',', '.')  # Handle both comma and decimal
            amount = float(amount_str)
            print("Successfully converted amount:", amount)
        except ValueError as e:
            return jsonify({
                "error": "Invalid amount format",
                "details": str(e),
                "received_value": str(data['amount']),
                "expected_format": "Number (e.g., 30 or 30.50)",
                "suggestion": "Use period as decimal separator"
            }), 400

        # Parse and validate other fields
        try:
            user_id = int(data['user_id'])
        except ValueError:
            return jsonify({"error": "user_id must be an integer"}), 400
            
        category = data['category'].lower().strip()
        mood = data.get('mood', '').lower().strip()

        if amount <= 0:
            return jsonify({"error": "Amount must be positive"}), 400
            
        if category not in VALID_CATEGORIES:
            return jsonify({
                "error": "Invalid category",
                "valid_categories": VALID_CATEGORIES,
                "received_category": category
            }), 400

        # Handle timestamp
        timestamp = datetime.datetime.now()
        if 'timestamp' in data:
            try:
                timestamp = datetime.datetime.strptime(data['timestamp'], "%Y-%m-%d %H:%M:%S")
                print("Using provided timestamp:", timestamp)
            except ValueError:
                return jsonify({
                    "error": "Invalid timestamp format",
                    "expected_format": "YYYY-MM-DD HH:MM:SS",
                    "received_value": data['timestamp']
                }), 400

        # Database operations
        conn = sqlite3.connect('spending_ai.db')
        cursor = conn.cursor()

        # Verify user exists
        cursor.execute("SELECT 1 FROM users WHERE id=?", (user_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"error": "User not found"}), 404

        # Check for recent transactions
        cursor.execute('''
            SELECT amount, timestamp FROM transactions 
            WHERE user_id=? AND category=?
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (user_id, category))
        last_transaction = cursor.fetchone()
        
        # Cooldown check
        is_in_cooldown = False
        last_amount = None
        last_time = None
        hours_since_last = None
        
        if last_transaction:
            last_amount, last_time_str = last_transaction
            last_time = datetime.datetime.strptime(last_time_str, "%Y-%m-%d %H:%M:%S")
            hours_since_last = (timestamp - last_time).total_seconds() / 3600
            cursor.execute('''
                SELECT 1 FROM cooldowns 
                WHERE user_id=? AND category=? AND expires_at > ?
            ''', (user_id, category, timestamp))
            is_in_cooldown = bool(cursor.fetchone())

        # Budget check
        budget_warning = None
        cursor.execute('''
            SELECT monthly_limit, current_spend 
            FROM budgets 
            WHERE user_id=? AND category=?
        ''', (user_id, category))
        budget = cursor.fetchone()
        
        if budget:
            limit, spent = budget
            if spent + amount > limit * 0.8:
                budget_percent = int((spent + amount) / limit * 100)
                budget_warning = {
                    "type": "budget_alert",
                    "message": f"⚠️ This will use {budget_percent}% of your {category} budget",
                    "limit": limit,
                    "new_total": spent + amount,
                    "remaining": limit - (spent + amount)
                }

        # Impulse detection
        flagged = False
        warning_msg = None
        if category not in ESSENTIAL_CATEGORIES + ['subscription']:
            flagged = is_impulsive(user_id, amount, category, mood, timestamp)
            if flagged:
                cursor.execute('''
                    INSERT OR REPLACE INTO cooldowns 
                    (user_id, category, expires_at)
                    VALUES (?, ?, datetime('now', '+24 hours'))
                ''', (user_id, category))
                warning_msg = "🚨 Impulse detected!" 

        # Generate deterrence alerts
        deterrence_alerts = []
        
        if is_in_cooldown and last_amount:
            deterrence_alerts.append({
                "type": "cooldown_warning",
                "message": f"🔄 You recently spent ${last_amount:.2f} on {category} {hours_since_last:.1f}h ago",
                "suggestion": "Consider waiting 24h unless essential",
                "time_since_last": f"{hours_since_last:.1f} hours",
                "previous_amount": last_amount
            })
            
        if "stress" in mood and amount > 30:
            deterrence_alerts.append({
                "type": "emotional_spending",
                "message": "🧠 Stress spending detected",
                "suggestion": "Try a 10-minute walk before deciding",
                "amount": amount,
                "mood": mood
            })
            
        if budget_warning:
            deterrence_alerts.append(budget_warning)

        # Log transaction
        cursor.execute('''
            INSERT INTO transactions 
            (user_id, amount, category, mood, timestamp, flagged)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, amount, category, mood, timestamp, flagged))

        # Record spending pattern
        cursor.execute('''
            INSERT INTO spending_patterns 
            (user_id, category, day_of_week, hour_of_day, amount, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, category, timestamp.weekday(), timestamp.hour, amount, timestamp))

        # Update streak if not impulsive
        if not flagged:
            cursor.execute('''
                UPDATE users SET streak_days = streak_days + 1 
                WHERE id=?
            ''', (user_id,))

        # Update budget if exists
        if budget:
            cursor.execute('''
                UPDATE budgets 
                SET current_spend = current_spend + ? 
                WHERE user_id=? AND category=?
            ''', (amount, user_id, category))

        conn.commit()
        conn.close()

        return jsonify({
            "message": "Transaction processed successfully",
            "allowed": True,
            "flagged": flagged,
            "warning": warning_msg,
            "deterrence_alerts": deterrence_alerts if deterrence_alerts else None,
            "amount": amount,
            "category": category,
            "budget_impact": {
                "percentage_used": budget_percent if budget else None,
                "remaining": limit - (spent + amount) if budget else None
            } if budget else None,
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S")
        }), 200

    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON format"}), 400
    except ValueError as e:
        return jsonify({"error": f"Invalid data: {str(e)}"}), 400
    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.route('/heatmap/<int:user_id>', methods=['GET'])
def get_heatmap(user_id):
    conn = sqlite3.connect('spending_ai.db')
    cursor = conn.cursor()
    
    # Weekly pattern
    cursor.execute('''
        SELECT category, day_of_week, SUM(amount) as total
        FROM spending_patterns
        WHERE user_id=?
        GROUP BY category, day_of_week
    ''', (user_id,))
    
    weekly_data = defaultdict(lambda: [0]*7)
    for category, day, total in cursor.fetchall():
        weekly_data[category][day] = total
    
    # Daily pattern
    cursor.execute('''
        SELECT category, hour_of_day, SUM(amount) as total
        FROM spending_patterns
        WHERE user_id=?
        GROUP BY category, hour_of_day
    ''', (user_id,))
    
    daily_data = defaultdict(lambda: [0]*24)
    for category, hour, total in cursor.fetchall():
        daily_data[category][hour] = total
    
    conn.close()
    
    return jsonify({
        "weekly_pattern": weekly_data,
        "daily_pattern": daily_data
    })

@app.route('/alerts/<int:user_id>', methods=['GET'])
def get_all_alerts(user_id):
    conn = sqlite3.connect('spending_ai.db')
    cursor = conn.cursor()
    
    alerts = []
    
    # 1. Budget alerts
    cursor.execute('''
        SELECT category, monthly_limit, current_spend 
        FROM budgets 
        WHERE user_id=? AND current_spend > monthly_limit * 0.8
    ''', (user_id,))
    
    for category, limit, spent in cursor.fetchall():
        alerts.append({
            "type": "budget_warning",
            "message": f"{category} spending reached {int(spent/limit*100)}% of budget",
            "category": category,
            "spent": spent,
            "limit": limit
        })
    
    # 2. Spending spikes - FIXED QUERY
    cursor.execute('''
        WITH monthly_totals AS (
            SELECT 
                category, 
                strftime('%Y-%m', timestamp) as month,
                SUM(amount) as monthly_total
            FROM transactions 
            WHERE user_id=?
            GROUP BY category, month
        )
        SELECT 
            category,
            SUM(CASE WHEN month = strftime('%Y-%m', 'now') THEN monthly_total ELSE 0 END) as current_month,
            AVG(CASE WHEN month != strftime('%Y-%m', 'now') THEN monthly_total ELSE NULL END) as avg_monthly
        FROM monthly_totals
        GROUP BY category
        HAVING current_month > avg_monthly * 1.3
    ''', (user_id,))
    
    for category, current, avg in cursor.fetchall():
        if avg:  # Only alert if we have historical data
            alerts.append({
                "type": "spending_spike",
                "message": f"Spending on {category} is {int((current/avg-1)*100)}% higher than usual",
                "category": category,
                "current": current,
                "average": avg
            })
    
    conn.close()
    return jsonify({"alerts": alerts}), 200

@app.route('/budgets', methods=['POST'])
def set_budget():
    data = request.get_json()
    user_id = data.get('user_id')
    category = data.get('category')
    limit = data.get('limit')
    
    if not all([user_id, category, limit]):
        return jsonify({"error": "Missing required fields"}), 400
    
    try:
        limit = float(limit)
        if limit <= 0:
            return jsonify({"error": "Limit must be positive"}), 400
            
        if category.lower() not in VALID_CATEGORIES:
            return jsonify({"error": "Invalid category"}), 400
            
        conn = sqlite3.connect('spending_ai.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO budgets 
            (user_id, category, monthly_limit)
            VALUES (?, ?, ?)
        ''', (user_id, category.lower(), limit))
        
        conn.commit()
        return jsonify({
            "message": f"Budget set for {category}",
            "limit": limit
        }), 201
    except ValueError:
        return jsonify({"error": "Invalid limit amount"}), 400
    finally:
        conn.close()

if __name__ == '__main__':
    create_db()
    app.run(debug=True)