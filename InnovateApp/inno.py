from flask import Flask, request, jsonify
import sqlite3
import datetime
from collections import defaultdict
from contextlib import closing

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # For proper emoji display

# Constants
VALID_CATEGORIES = ['groceries', 'transport', 'utilities', 'entertainment', 
                   'dining', 'shopping', 'subscription', 'other']
ESSENTIAL_CATEGORIES = ['groceries', 'transport', 'utilities']

def create_db():
    with sqlite3.connect('spending_ai.db') as conn:
        cursor = conn.cursor()
        
        # Users table with streak tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                streak_days INTEGER DEFAULT 0,
                last_transaction_date DATE
            )
        ''')

        # Transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                flagged BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # Cooldowns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cooldowns (
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                expires_at DATETIME NOT NULL,
                PRIMARY KEY (user_id, category),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # Budgets table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS budgets (
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                monthly_limit REAL NOT NULL,
                current_spend REAL DEFAULT 0,
                PRIMARY KEY (user_id, category),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # Spending patterns (for heatmap)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS spending_patterns (
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                day_of_week INTEGER NOT NULL,
                hour_of_day INTEGER NOT NULL,
                amount REAL NOT NULL,
                timestamp DATETIME NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_flagged ON transactions(flagged)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_spending_patterns_user ON spending_patterns(user_id)')

def validate_input(data, required_fields):
    """Validate and sanitize input data"""
    if not isinstance(data, dict):
        raise ValueError("Input must be a JSON object")
    
    missing = [field for field in required_fields if field not in data]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
    
    return {k: v.strip() if isinstance(v, str) else v for k, v in data.items()}

def validate_category(category):
    """Validate and normalize category"""
    category = category.lower().strip()
    if category not in VALID_CATEGORIES:
        raise ValueError(f"Invalid category. Must be one of: {', '.join(VALID_CATEGORIES)}")
    return category

def validate_amount(amount):
    """Validate and convert amount to float"""
    try:
        amount = float(str(amount).replace(',', '.'))
        if amount <= 0:
            raise ValueError("Amount must be positive")
        return amount
    except (ValueError, TypeError):
        raise ValueError("Invalid amount format")

def validate_timestamp(timestamp_str=None):
    """Validate and return timezone-aware timestamp
    
    Args:
        timestamp_str: Optional timestamp string in format YYYY-MM-DD HH:MM:SS
        
    Returns:
        datetime: Timezone-aware datetime object (UTC if no timezone specified)
        
    Raises:
        ValueError: If timestamp format is invalid
    """
    if timestamp_str:
        try:
            # First try parsing with timezone info if present
            try:
                timestamp = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S%z")
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
                return timestamp
            except ValueError:
                # Fall back to parsing without timezone
                timestamp = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                return timestamp.replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            raise ValueError("Invalid timestamp format. Use YYYY-MM-DD HH:MM:SS")
    # Return current UTC time if no timestamp provided
    return datetime.datetime.now(datetime.timezone.utc)

def detect_behavioral_context(user_id, transaction):
    """Detects spending contexts for non-essential categories only"""
    if transaction['category'] in ESSENTIAL_CATEGORIES:
        return []
    
    with sqlite3.connect('spending_ai.db') as conn:
        cursor = conn.cursor()
        triggers = []
        
        # Late-night spending (10PM-4AM)
        if 22 <= transaction['timestamp'].hour or transaction['timestamp'].hour <= 4:
            triggers.append("late_night_purchase")
        
        # Rapid-fire transactions (3+ in 1 hour)
        placeholders = ','.join(['?']*len(ESSENTIAL_CATEGORIES))
        query = f'''
            SELECT COUNT(*) FROM transactions 
            WHERE user_id=? AND category NOT IN ({placeholders}) 
            AND timestamp > datetime(?, '-1 hour')
        '''
        cursor.execute(query, [user_id] + ESSENTIAL_CATEGORIES + [transaction['timestamp']])
        if cursor.fetchone()[0] >= 2:
            triggers.append("rapid_fire_spending")
        
        # High-frequency categories (5+ same category/week)
        cursor.execute('''
            SELECT COUNT(*) FROM transactions
            WHERE user_id=? AND category=?
            AND timestamp > datetime(?, '-7 days')
        ''', (user_id, transaction['category'], transaction['timestamp']))
        if cursor.fetchone()[0] >= 4:
            triggers.append("high_frequency_category")
        
        return triggers

def is_impulsive(user_id, amount, category, timestamp):
    """Determines if a transaction is impulsive - never for essentials"""
    if category in ESSENTIAL_CATEGORIES:
        return False
        
    behavioral_triggers = detect_behavioral_context(user_id, {
        'timestamp': timestamp,
        'category': category
    })
    
    # Decision matrix with clear thresholds
    if "late_night_purchase" in behavioral_triggers and amount > 20:
        return True
    if "rapid_fire_spending" in behavioral_triggers and amount > 30:
        return True
    if "high_frequency_category" in behavioral_triggers and amount > 50:
        return True
        
    return False

def get_future_projections(user_id):
    with sqlite3.connect('spending_ai.db') as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                category,
                SUM(amount) as total_spend,
                COUNT(*) as transaction_count
            FROM transactions
            WHERE user_id = ? 
            AND timestamp > datetime('now', '-3 months')
            GROUP BY category
        ''', (user_id,))
        
        projections = {}
        for category, total, count in cursor.fetchall():
            if count >= 3 and total >= 50:  # Only include significant categories
                avg_monthly = total / 3
                projections[category] = {
                    "avg_monthly": round(avg_monthly, 2),
                    "projected_yearly": round(avg_monthly * 12, 2),
                    "potential_investment": round(avg_monthly * 12 * (1.07 ** 5), 2)
                }
        
        return projections

def get_cool_down_suggestions(user_id, current_category=None):
    """Generates suggestions only for non-essential categories"""
    if current_category in ESSENTIAL_CATEGORIES:
        return []
    
    with sqlite3.connect('spending_ai.db') as conn:
        cursor = conn.cursor()
        suggestions = []
        
        # Time-based patterns
        placeholders = ','.join(['?']*len(ESSENTIAL_CATEGORIES))
        query = f'''
            SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
            FROM transactions 
            WHERE user_id = ? AND flagged = 1
            AND category NOT IN ({placeholders})
            GROUP BY hour
            ORDER BY count DESC
            LIMIT 1
        '''
        cursor.execute(query, [user_id] + ESSENTIAL_CATEGORIES)
        peak_hour = cursor.fetchone()
        
        if peak_hour:
            hour, count = peak_hour
            suggestions.append(f"⏰ Your impulsive purchases often occur around {int(hour)}:00")
        
        # Category-specific suggestions
        if current_category:
            cursor.execute('''
                SELECT AVG(amount) as avg_amount
                FROM transactions
                WHERE user_id = ? AND category = ? AND flagged = 1
            ''', (user_id, current_category))
            category_avg = cursor.fetchone()
            
            if category_avg and category_avg[0]:
                suggestions.append(
                    f"🛑 For {current_category}, consider waiting when amount exceeds ${category_avg[0]:.2f}"
                )
        
        return suggestions

@app.route('/register', methods=['POST'])
def register():
    try:
        data = validate_input(request.get_json(), ['username', 'password'])
        username = data['username']
        password = data['password']
        
        with sqlite3.connect('spending_ai.db') as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', 
                             (username, password))
                conn.commit()
                return jsonify({
                    "status": "success",
                    "message": "User registered successfully",
                    "user_id": cursor.lastrowid
                }), 201
            except sqlite3.IntegrityError:
                return jsonify({
                    "status": "error",
                    "message": "Username already exists"
                }), 400
                
    except ValueError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}"
        }), 500

@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    try:
        # Validate and parse input
        data = validate_input(request.get_json(), ['user_id', 'amount', 'category'])
        user_id = int(data['user_id'])
        amount = validate_amount(data['amount'])
        category = validate_category(data['category'])
        timestamp = validate_timestamp(data.get('timestamp'))
        
        with sqlite3.connect('spending_ai.db') as conn:
            cursor = conn.cursor()
            
            # Verify user exists
            cursor.execute('''
                SELECT id, streak_days, last_transaction_date 
                FROM users WHERE id=?
            ''', (user_id,))
            user = cursor.fetchone()
            if not user:
                return jsonify({
                    "status": "error",
                    "message": "User not found"
                }), 404
                
            user_id_db, streak_days, last_date = user
            today = timestamp.date()
            
            # Check budget
            budget_warning = None
            cursor.execute('''
                SELECT monthly_limit, current_spend 
                FROM budgets 
                WHERE user_id=? AND category=?
            ''', (user_id, category))
            budget = cursor.fetchone()
            
            if budget:
                limit, spent = budget
                new_total = spent + amount
                budget_percent = min(int((new_total / limit) * 100), 999)  # Cap at 999%
                
                if new_total > limit:
                    budget_warning = {
                        "severity": "critical",
                        "message": f"🚨 Budget exceeded by ${new_total - limit:.2f} ({budget_percent}%)",
                        "limit": limit,
                        "spent": new_total
                    }
                elif new_total > limit * 0.9:
                    budget_warning = {
                        "severity": "warning",
                        "message": f"⚠️ Approaching budget limit ({budget_percent}%)",
                        "limit": limit,
                        "spent": new_total
                    }

            # Impulse detection (never for essentials)
            flagged = is_impulsive(user_id, amount, category, timestamp)
            
            # Record transaction
            cursor.execute('''
                INSERT INTO transactions 
                (user_id, amount, category, timestamp, flagged)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, amount, category, timestamp, flagged))
            
            # Record spending pattern
            cursor.execute('''
                INSERT INTO spending_patterns 
                (user_id, category, day_of_week, hour_of_day, amount, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, category, timestamp.weekday(), timestamp.hour, amount, timestamp))

            # Update streak (only for non-impulsive transactions)
            if not flagged:
                if last_date:
                    if isinstance(last_date, str):
                        last_date = datetime.datetime.strptime(last_date, "%Y-%m-%d").date()
                    
                    if today == last_date:
                        pass  # Same day, no change
                    elif (today - last_date).days == 1:
                        streak_days += 1  # Consecutive day
                    else:
                        streak_days = 1  # Broken streak
                else:
                    streak_days = 1  # First transaction
                
                cursor.execute('''
                    UPDATE users 
                    SET streak_days = ?, last_transaction_date = ?
                    WHERE id=?
                ''', (streak_days, today.isoformat(), user_id))

            # Update budget if exists
            if budget:
                cursor.execute('''
                    UPDATE budgets 
                    SET current_spend = current_spend + ? 
                    WHERE user_id=? AND category=?
                ''', (amount, user_id, category))

            conn.commit()
            
            # Prepare response
            response = {
                "status": "success",
                "data": {
                    "transaction_id": cursor.lastrowid,
                    "amount": amount,
                    "category": category,
                    "timestamp": timestamp.isoformat(),
                    "flagged": flagged,
                    "streak": streak_days if not flagged else 0,
                    "insights": {
                        "projections": get_future_projections(user_id),
                        "suggestions": get_cool_down_suggestions(user_id, category)
                    }
                }
            }
            
            if budget_warning:
                response["warnings"] = [budget_warning]
            
            return jsonify(response), 200
            
    except ValueError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Transaction processing failed: {str(e)}"
        }), 500

@app.route('/projections/<int:user_id>', methods=['GET'])
def show_projections(user_id):
    try:
        projections = get_future_projections(user_id)
        return jsonify({
            "status": "success",
            "data": projections
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/suggestions/<int:user_id>', methods=['GET'])
def show_suggestions(user_id):
    try:
        suggestions = get_cool_down_suggestions(user_id)
        return jsonify({
            "status": "success",
            "data": {
                "suggestions": suggestions
            }
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/heatmap/<int:user_id>', methods=['GET'])
def get_heatmap(user_id):
    try:
        with sqlite3.connect('spending_ai.db') as conn:
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
            
            return jsonify({
                "status": "success",
                "data": {
                    "weekly_pattern": weekly_data,
                    "daily_pattern": daily_data
                }
            })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/alerts/<int:user_id>', methods=['GET'])
def get_all_alerts(user_id):
    try:
        with sqlite3.connect('spending_ai.db') as conn:
            cursor = conn.cursor()
            
            alerts = []
            
            # Budget alerts
            cursor.execute('''
                SELECT category, monthly_limit, current_spend 
                FROM budgets 
                WHERE user_id=? AND current_spend > monthly_limit * 0.8
                ORDER BY current_spend DESC
            ''', (user_id,))
            
            for category, limit, spent in cursor.fetchall():
                percent = min(int((spent / limit) * 100), 999)
                alerts.append({
                    "type": "budget_warning",
                    "category": category,
                    "severity": "critical" if spent > limit else "warning",
                    "message": f"{category} spending at {percent}% of budget",
                    "limit": limit,
                    "spent": spent
                })
            
            return jsonify({
                "status": "success",
                "data": {
                    "alerts": alerts
                }
            })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/budgets', methods=['POST'])
def set_budget():
    try:
        data = validate_input(request.get_json(), ['user_id', 'category', 'limit'])
        user_id = int(data['user_id'])
        category = validate_category(data['category'])
        limit = validate_amount(data['limit'])
        
        with sqlite3.connect('spending_ai.db') as conn:
            cursor = conn.cursor()
            
            # Verify user exists
            cursor.execute('SELECT 1 FROM users WHERE id=?', (user_id,))
            if not cursor.fetchone():
                return jsonify({
                    "status": "error",
                    "message": "User not found"
                }), 404
            
            cursor.execute('''
                INSERT OR REPLACE INTO budgets 
                (user_id, category, monthly_limit)
                VALUES (?, ?, ?)
            ''', (user_id, category, limit))
            
            conn.commit()
            
            return jsonify({
                "status": "success",
                "data": {
                    "user_id": user_id,
                    "category": category,
                    "monthly_limit": limit
                }
            }), 201
            
    except ValueError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Budget setting failed: {str(e)}"
        }), 500

if __name__ == '__main__':
    create_db()
    app.run(debug=True)