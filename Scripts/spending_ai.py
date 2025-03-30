# spending_ai_integrated.py
from flask import Flask, request, jsonify, render_template
import sqlite3
import datetime
from collections import defaultdict
from contextlib import closing
import os  
import tempfile# Added for path handling

# --- AI Integration ---
# Assuming Main.py is in a 'Scripts' subfolder relative to this file
# Adjust the path if your folder structure is different
import sys

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))
# Construct the path to the Scripts folder
scripts_dir = os.path.join(current_dir, "Scripts")
# Add the Scripts directory to the Python path
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)
    print(f"DEBUG: Added {scripts_dir} to sys.path")
else:
    print(f"DEBUG: {scripts_dir} already in sys.path")

print(f"DEBUG: Current sys.path: {sys.path}") # Verify the path list

FinancialSummaryGenerator = None 
try:
    # Now import the required class and functions from Main.py
    from Main import FinancialSummaryGenerator, GOOGLE_API_KEY, AI_ENABLED, convert_csv


    print("Successfully imported FinancialSummaryGenerator from Main.py")
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "YOUR_API_KEY":
        print(
            "Warning: Google API Key not configured in Main.py. AI features may not work."
        )
        AI_ENABLED = False
    else:
        AI_ENABLED = True
except ImportError as e:
    print(f"Error importing from Main.py: {e}")
    print("AI recommendations will be disabled.")
    print("Warning: convert_csv function not found in Main.py. CSV conversion might not work.")
    def convert_csv(input_file, output_file=None):
        print("Placeholder convert_csv: Returning input path.")
        if output_file: return output_file
        return input_file
    # Define a placeholder class if import fails
    class FinancialSummaryGenerator:
        def __init__(self):
            self.user_data = {
                "income": {},
                "expenses": {},
                "savings": {},
                "debt": {},
                "high_ticket_purchases": [],
            }
            self.financial_metrics = {}
            self.recommendations = []

        def analyze_data(self):
            pass

        def generate_ai_recommendations(self):
            pass  # Does nothing if AI fails

    AI_ENABLED = False
# --- End AI Integration ---

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

# Constants (Keep these as they are)
VALID_CATEGORIES = [
    "groceries",
    "transport",
    "utilities",
    "entertainment",
    "dining",
    "shopping",
    "subscription",
    "other",
]
ESSENTIAL_CATEGORIES = ["groceries", "transport", "utilities"]
DB_NAME = "spending_ai.db"  # Use a constant for the DB name


def create_db():
    # (Keep the create_db function exactly as provided in your sample)
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # Users table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL, /* Consider hashing passwords! */
                streak_days INTEGER DEFAULT 0,
                last_transaction_date DATE
            )
        """
        )
        # Transactions table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                flagged BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
        )
        # Budgets table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS budgets (
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                monthly_limit REAL NOT NULL,
                current_spend REAL DEFAULT 0,
                PRIMARY KEY (user_id, category),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
        )
        # Spending patterns table (Keep as is)
        cursor.execute(
            """
           CREATE TABLE IF NOT EXISTS spending_patterns (
               user_id INTEGER NOT NULL,
               category TEXT NOT NULL,
               day_of_week INTEGER NOT NULL,
               hour_of_day INTEGER NOT NULL,
               amount REAL NOT NULL,
               timestamp DATETIME NOT NULL,
               FOREIGN KEY (user_id) REFERENCES users(id)
           )
       """
        )
        # Create indexes (Keep as is)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_transactions_flagged ON transactions(flagged)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_spending_patterns_user ON spending_patterns(user_id)"
        )


# --- Validation Functions (Keep as provided) ---
def validate_input(data, required_fields):
    if not isinstance(data, dict):
        raise ValueError("Input must be a JSON object")
    missing = [field for field in required_fields if field not in data]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
    return {k: v.strip() if isinstance(v, str) else v for k, v in data.items()}


def validate_category(category):
    category = category.lower().strip()
    if category not in VALID_CATEGORIES:
        raise ValueError(
            f"Invalid category. Must be one of: {', '.join(VALID_CATEGORIES)}"
        )
    return category


def validate_amount(amount):
    try:
        amount = float(str(amount).replace(",", "."))
        if amount <= 0:
            raise ValueError("Amount must be positive")
        return amount
    except (ValueError, TypeError):
        raise ValueError("Invalid amount format")


def validate_timestamp(timestamp_str=None):
    if timestamp_str:
        try:
            try:  # Try parsing with timezone
                timestamp = datetime.datetime.strptime(
                    timestamp_str, "%Y-%m-%d %H:%M:%S%z"
                )
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
                return timestamp
            except ValueError:  # Fallback without timezone
                timestamp = datetime.datetime.strptime(
                    timestamp_str, "%Y-%m-%d %H:%M:%S"
                )
                return timestamp.replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            raise ValueError("Invalid timestamp format. Use YYYY-MM-DD HH:MM:SS")
    return datetime.datetime.now(datetime.timezone.utc)


# --- Core Logic Functions (Keep `detect_behavioral_context` and `is_impulsive` as provided) ---
def detect_behavioral_context(user_id, transaction):
    if transaction["category"] in ESSENTIAL_CATEGORIES:
        return []
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        triggers = []
        if 22 <= transaction["timestamp"].hour or transaction["timestamp"].hour <= 4:
            triggers.append("late_night_purchase")
        placeholders = ",".join(["?"] * len(ESSENTIAL_CATEGORIES))
        query = f"""
            SELECT COUNT(*) FROM transactions
            WHERE user_id=? AND category NOT IN ({placeholders})
            AND timestamp > datetime(?, '-1 hour')
        """
        cursor.execute(
            query, [user_id] + ESSENTIAL_CATEGORIES + [transaction["timestamp"]]
        )
        if cursor.fetchone()[0] >= 2:  # 3rd transaction in the hour
            triggers.append("rapid_fire_spending")
        cursor.execute(
            """
            SELECT COUNT(*) FROM transactions
            WHERE user_id=? AND category=?
            AND timestamp > datetime(?, '-7 days')
        """,
            (user_id, transaction["category"], transaction["timestamp"]),
        )
        if cursor.fetchone()[0] >= 4:  # 5th transaction in the week
            triggers.append("high_frequency_category")
        return triggers


def is_impulsive(user_id, amount, category, timestamp):
    if category in ESSENTIAL_CATEGORIES:
        return False
    behavioral_triggers = detect_behavioral_context(
        user_id, {"timestamp": timestamp, "category": category}
    )
    if "late_night_purchase" in behavioral_triggers and amount > 20:
        return True
    if "rapid_fire_spending" in behavioral_triggers and amount > 30:
        return True
    if "high_frequency_category" in behavioral_triggers and amount > 50:
        return True
    return False


# --- AI Integration: Helper to get financial snapshot ---
def get_user_financial_snapshot(user_id):
    """
    Gathers necessary data for the AI model from the database.
    Attempts to structure the data similarly to what might be input
    manually or via CSV in the original Main.py script.
    """
    snapshot = {
        "income": {},
        "expenses": {},
        "savings": {},
        "debt": {},
        "high_ticket_purchases": [],
    }
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # --- 1. Estimate Monthly Income (Still an estimation - needs refinement) ---
        # Using average *non-essential* spending might give a slightly better clue
        # than total spending, but still very rough.
        placeholders = ",".join(["?"] * len(ESSENTIAL_CATEGORIES))
        cursor.execute(
            f"""
            SELECT SUM(amount)
            FROM transactions
            WHERE user_id = ?
            AND timestamp > datetime('now', '-3 months')
            AND category NOT IN ({placeholders})
        """,
            [user_id] + ESSENTIAL_CATEGORIES,
        )
        non_essential_spend_3mo = cursor.fetchone()[0] or 0
        avg_monthly_non_essential = non_essential_spend_3mo / 3.0

        # Estimate income based on non-essential spend + estimated essential spend. VERY ROUGH.
        # Assume essentials are a fixed amount or proportion for now. This needs a better source.
        estimated_essentials = 1500  # Example fixed amount for rent, groceries etc.
        estimated_income = max(
            3000, estimated_essentials + avg_monthly_non_essential * 1.5
        )  # Ensure a minimum
        snapshot["income"]["monthly"] = round(estimated_income, 2)
        print(
            f"Debug: Estimated monthly income for user {user_id}: {snapshot['income']['monthly']:.2f}"
        )

        # --- 2. Get Monthly Expenses by Category (Mapped to standard names) ---
        cursor.execute(
            """
            SELECT category, SUM(amount)
            FROM transactions
            WHERE user_id = ? AND timestamp > datetime('now', '-1 month')
            GROUP BY category
        """,
            (user_id,),
        )
        expenses_this_month = cursor.fetchall()
        # Map DB categories to names potentially expected by AI prompt / Main.py structure
        # Try to align with categories mentioned in Main.py comments or standard ones
        expense_map = {
            "groceries": "Food",
            "transport": "Transportation",
            "utilities": "Utilities",  # Assuming utilities exist
            "entertainment": "Entertainment",
            "dining": "Dining",  # Keep specific if available
            "shopping": "Shopping",  # Keep specific if available
            "subscription": "Subscriptions",
            "other": "Miscellaneous",  # Align with Main.py's use of 'miscellaneous'
            # Add mappings if you have categories like 'rent', 'insurance' etc.
            # 'rent': 'Rent/Mortgage',
            # 'insurance': 'Insurance',
        }
        total_expenses_calc = 0
        for category, total in expenses_this_month:
            program_cat = expense_map.get(
                category, category.capitalize()
            )  # Default to capitalized DB name
            snapshot["expenses"][program_cat] = round(total, 2)
            total_expenses_calc += total

        # Add zero for categories not found this month but potentially expected
        expected_cats = [
            "Rent/Mortgage",
            "Utilities",
            "Food",
            "Transportation",
            "Entertainment",
            "Insurance",
            "Miscellaneous",
        ]
        for cat in expected_cats:
            if cat not in snapshot["expenses"]:
                snapshot["expenses"][cat] = 0.0

        # --- 3. Estimate Savings (Still an estimation) ---
        monthly_savings_est = max(
            0, snapshot["income"]["monthly"] - total_expenses_calc
        )
        snapshot["savings"]["monthly_contribution"] = round(monthly_savings_est, 2)
        # Current savings - Needs a DB field. Estimate as 3x monthly contribution.
        snapshot["savings"]["current"] = round(monthly_savings_est * 3, 2)
        print(
            f"Debug: Estimated savings (monthly/current): {snapshot['savings']['monthly_contribution']:.2f} / {snapshot['savings']['current']:.2f}"
        )

        # --- 4. Get Debt (Placeholder - Add example data for testing) ---
        # !!! IMPORTANT: This is placeholder data because your DB doesn't store debt. !!!
        # !!! In a real app, you would fetch this from dedicated debt tables. !!!
        # Add some example debt to make the snapshot more realistic for the AI prompt
        snapshot["debt"] = {
            "Credit Cards": {"amount": 2500.00, "interest": 19.9},
            "Student Loans": {"amount": 15000.00, "interest": 5.5},
            # Add other debt types if relevant to your testing
            # 'Car Loans': {'amount': 8000.00, 'interest': 4.2}
        }
        print(f"Debug: Using PLACEHOLDER debt data: {snapshot['debt']}")

        # --- 5. Get Recent High-Ticket Purchases (Using DB query > $100) ---
        # This structure is okay, mimics the list of dicts from Main.py
        cursor.execute(
            """
            SELECT category, amount, timestamp
            FROM transactions
            WHERE user_id = ? AND amount > 100 AND timestamp > datetime('now', '-3 months')
            ORDER BY timestamp DESC
            LIMIT 5
        """,
            (user_id,),
        )
        ht_purchases = cursor.fetchall()
        for category, amount, ts_str in ht_purchases:
            try:
                timestamp_obj = datetime.datetime.fromisoformat(ts_str)
                # Use a more descriptive item name if possible, otherwise use category
                item_name = (
                    f"Purchase in {expense_map.get(category, category.capitalize())}"
                )
                snapshot["high_ticket_purchases"].append(
                    {
                        "item": item_name,
                        "amount": round(amount, 2),
                        "date": timestamp_obj.date(),  # Keep as date object
                        "category": expense_map.get(category, category.capitalize()),
                    }
                )
            except ValueError:
                print(
                    f"Warning: Could not parse timestamp '{ts_str}' for high-ticket purchase."
                )
        print(
            f"Debug: Found {len(snapshot['high_ticket_purchases'])} high-ticket purchases."
        )

    return snapshot


# --- Flask Routes ---


@app.route("/register", methods=["POST"])
def register():
    # (Keep the register function exactly as provided)
    try:
        data = validate_input(request.get_json(), ["username", "password"])
        username = data["username"]
        password = data["password"]  # IMPORTANT: Hash passwords in a real app!
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO users (username, password) VALUES (?, ?)",
                    (username, password),
                )
                conn.commit()
                return (
                    jsonify(
                        {
                            "status": "success",
                            "message": "User registered successfully",
                            "user_id": cursor.lastrowid,
                        }
                    ),
                    201,
                )
            except sqlite3.IntegrityError:
                return (
                    jsonify({"status": "error", "message": "Username already exists"}),
                    400,
                )
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Registration failed: {e}")  # Log errors
        return (
            jsonify({"status": "error", "message": f"An unexpected error occurred"}),
            500,
        )


@app.route("/add_transaction", methods=["POST"])
def add_transaction():
    try:
        # --- Basic Transaction Handling (Mostly as provided) ---
        data = validate_input(request.get_json(), ["user_id", "amount", "category"])
        user_id = int(data["user_id"])
        amount = validate_amount(data["amount"])
        category = validate_category(data["category"])
        timestamp = validate_timestamp(data.get("timestamp"))

        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()

            # Verify user
            cursor.execute(
                "SELECT id, streak_days, last_transaction_date FROM users WHERE id=?",
                (user_id,),
            )
            user = cursor.fetchone()
            if not user:
                return jsonify({"status": "error", "message": "User not found"}), 404
            user_id_db, streak_days, last_date = user
            today = timestamp.date()

            # Budget Check (Keep as provided)
            budget_warning = None
            cursor.execute(
                "SELECT monthly_limit, current_spend FROM budgets WHERE user_id=? AND category=?",
                (user_id, category),
            )
            budget = cursor.fetchone()
            if budget:
                limit, spent = budget
                new_total = spent + amount
                budget_percent = (
                    min(int((new_total / limit) * 100), 999) if limit > 0 else 0
                )
                if new_total > limit:
                    budget_warning = {
                        "severity": "critical",
                        "message": f"🚨 Budget exceeded by ${new_total - limit:.2f} ({budget_percent}%)",
                        "limit": limit,
                        "spent": new_total,
                    }
                elif new_total > limit * 0.9:
                    budget_warning = {
                        "severity": "warning",
                        "message": f"⚠️ Approaching budget limit ({budget_percent}%)",
                        "limit": limit,
                        "spent": new_total,
                    }

            # Impulse detection (Keep as provided)
            flagged = is_impulsive(user_id, amount, category, timestamp)

            # Record transaction & spending pattern (Keep as provided)
            cursor.execute(
                "INSERT INTO transactions (user_id, amount, category, timestamp, flagged) VALUES (?, ?, ?, ?, ?)",
                (user_id, amount, category, timestamp, flagged),
            )
            transaction_id = cursor.lastrowid  # Get the ID
            cursor.execute(
                "INSERT INTO spending_patterns (user_id, category, day_of_week, hour_of_day, amount, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    user_id,
                    category,
                    timestamp.weekday(),
                    timestamp.hour,
                    amount,
                    timestamp,
                ),
            )

            # Update streak (Keep as provided)
            if not flagged:
                if last_date:
                    if isinstance(last_date, str):
                        last_date = datetime.datetime.strptime(
                            last_date, "%Y-%m-%d"
                        ).date()
                    if today == last_date:
                        pass
                    elif (today - last_date).days == 1:
                        streak_days += 1
                    else:
                        streak_days = 1
                else:
                    streak_days = 1
                cursor.execute(
                    "UPDATE users SET streak_days = ?, last_transaction_date = ? WHERE id=?",
                    (streak_days, today.isoformat(), user_id),
                )
            else:  # Reset streak if impulsive
                streak_days = 0
                cursor.execute(
                    "UPDATE users SET streak_days = 0 WHERE id=?", (user_id,)
                )

            # Update budget (Keep as provided)
            if budget:
                cursor.execute(
                    "UPDATE budgets SET current_spend = current_spend + ? WHERE user_id=? AND category=?",
                    (amount, user_id, category),
                )

            conn.commit()

            # --- Generate AI Transaction Analysis ---
            transaction_analysis = None
            recommendations = []
            print(f"Debug: AI_ENABLED = {AI_ENABLED}")
            # Check if this is a user-input transaction (default is True if not specified)
            is_user_input = data.get("user_input", True)

            # Initialize generator - empty by default
            generator = FinancialSummaryGenerator()

            # Only run AI analysis if enabled AND not a user input transaction
            if AI_ENABLED and is_user_input:
                try:
                    # 1. Get financial snapshot for context
                    snapshot = get_user_financial_snapshot(user_id)

                    # 2. Initialize the generator and load data
                    generator = FinancialSummaryGenerator()
                    generator.user_data = snapshot  # Load snapshot into the generator
                    generator.analyze_data()  # Calculate metrics based on snapshot

                    # 3. Prepare transaction data for analysis
                    # Include budget info and other financial context if available
                    budget_limit_data = {}
                    budget_spending_data = {}

                    # Get all budget limits for user
                    cursor.execute(
                        "SELECT category, monthly_limit, current_spend FROM budgets WHERE user_id=?",
                        (user_id,),
                    )
                    budgets = cursor.fetchall()
                    for budget_category, limit, spent in budgets:
                        budget_limit_data[budget_category] = limit
                        budget_spending_data[budget_category] = spent

                    # Build transaction context
                    transaction_data = {
                        "amount": amount,
                        "category": category,
                        "timestamp": timestamp,
                        "financial_context": {
                            "monthly_income": snapshot["income"].get("monthly", 0),
                            "budget_limit": budget_limit_data,
                            "current_spending": budget_spending_data,
                            "flagged_as_impulsive": flagged,
                        },
                    }

                    # 4. Analyze the transaction
                    transaction_analysis = generator.analyze_transaction(
                        transaction_data
                    )
                    print(
                        f"Debug: Calling generate_ai_recommendations for user {user_id}"
                    )
                    generator.analyze_transaction(transaction_data)
                    print(
                        f"Debug: AI recommendations generated: {len(generator.recommendations)} items"
                    )
                    ai_recommendations = (
                        generator.recommendations
                    )  # Get the list of dicts

                except Exception as ai_error:
                    app.logger.error(
                        f"AI recommendation generation failed for user {user_id}: {ai_error}"
                    )
                    # Optionally add a generic message if AI fails
                    ai_recommendations = [
                        {
                            "title": "Recommendation Engine Unavailable",
                            "description": "Could not generate personalized recommendations at this time.",
                            "category": "System",
                        }
                    ]

            # Prepare response
            response_data = {
                "status": "success",
                "data": {
                    "transaction_id": transaction_id,
                    "amount": amount,
                    "category": category,
                    "timestamp": timestamp.isoformat(),
                    "flagged": flagged,
                    "streak": streak_days,
                    "insights": {
                        "recommendations": (
                            generator.recommendations
                            if hasattr(generator, "recommendations")
                            and generator.recommendations
                            else []
                        )
                    },
                },
            }

            # Add transaction analysis if available
            if transaction_analysis:
                response_data["data"]["analysis"] = {
                    "advice": transaction_analysis.get("advice", ""),
                    "tags": transaction_analysis.get("tags", []),
                    "impact": transaction_analysis.get("impact", ""),
                    "ai_generated": transaction_analysis.get("ai_generated", False),
                }

            if budget_warning:
                # Ensure 'warnings' key exists and is a list
                if "warnings" not in response_data:
                    response_data["warnings"] = []
                response_data["warnings"].append(budget_warning)

            return jsonify(response_data), 200

    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        app.logger.error(
            f"Add transaction failed: {e}", exc_info=True
        )  # Log detailed error
        return (
            jsonify({"status": "error", "message": f"Transaction processing failed"}),
            500,
        )


# --- Other Routes (Keep /projections, /suggestions, /heatmap, /alerts, /budgets as provided) ---
# Note: You might want to update /suggestions to also use the AI or remove it if redundant


@app.route("/projections/<int:user_id>", methods=["GET"])
def show_projections(user_id):
    # (Keep this function as is, or adapt if needed)
    # Example placeholder implementation:
    try:
        # Replace with actual projection logic if available
        projections = get_user_financial_snapshot(user_id)["savings"]  # Example
        return jsonify({"status": "success", "data": projections})
    except Exception as e:
        app.logger.error(f"Failed to get projections for user {user_id}: {e}")
        return (
            jsonify({"status": "error", "message": "Could not retrieve projections"}),
            500,
        )


@app.route("/suggestions/<int:user_id>", methods=["GET"])
def show_suggestions(user_id):
    # This now potentially overlaps with AI recommendations.
    # Decide if you want to keep this or rely solely on AI via /add_transaction
    try:
        # Option 1: Keep original suggestions
        # suggestions = get_cool_down_suggestions(user_id)

        # Option 2: Call AI generation separately here (might be slow)
        if AI_ENABLED:
            snapshot = get_user_financial_snapshot(user_id)
            generator = FinancialSummaryGenerator()
            generator.user_data = snapshot
            generator.analyze_data()
            generator.generate_ai_recommendations()
            suggestions = generator.recommendations
        else:
            suggestions = [
                {
                    "title": "AI Disabled",
                    "description": "AI features not available.",
                    "category": "System",
                }
            ]

        return jsonify({"status": "success", "data": {"suggestions": suggestions}})
    except Exception as e:
        app.logger.error(f"Failed to get suggestions for user {user_id}: {e}")
        return (
            jsonify({"status": "error", "message": "Could not retrieve suggestions"}),
            500,
        )


@app.route("/heatmap/<int:user_id>", methods=["GET"])
def get_heatmap(user_id):
    # (Keep this function as provided in your sample)
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT category, day_of_week, SUM(amount) FROM spending_patterns WHERE user_id=? GROUP BY category, day_of_week",
                (user_id,),
            )
            weekly_data = defaultdict(lambda: [0] * 7)
            for category, day, total in cursor.fetchall():
                weekly_data[category][day] = total

            cursor.execute(
                "SELECT category, hour_of_day, SUM(amount) FROM spending_patterns WHERE user_id=? GROUP BY category, hour_of_day",
                (user_id,),
            )
            daily_data = defaultdict(lambda: [0] * 24)
            for category, hour, total in cursor.fetchall():
                daily_data[category][hour] = total

            return jsonify(
                {
                    "status": "success",
                    "data": {
                        "weekly_pattern": weekly_data,
                        "daily_pattern": daily_data,
                    },
                }
            )
    except Exception as e:
        app.logger.error(f"Heatmap generation failed for user {user_id}: {e}")
        return (
            jsonify({"status": "error", "message": "Could not generate heatmap"}),
            500,
        )


@app.route("/alerts/<int:user_id>", methods=["GET"])
def get_all_alerts(user_id):
    # (Keep this function as provided in your sample)
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            alerts = []
            cursor.execute(
                "SELECT category, monthly_limit, current_spend FROM budgets WHERE user_id=? AND current_spend > monthly_limit * 0.8 ORDER BY current_spend DESC",
                (user_id,),
            )
            for category, limit, spent in cursor.fetchall():
                percent = min(int((spent / limit) * 100), 999) if limit > 0 else 0
                alerts.append(
                    {
                        "type": "budget_warning",
                        "category": category,
                        "severity": "critical" if spent > limit else "warning",
                        "message": f"{category} spending at {percent}% of budget",
                        "limit": limit,
                        "spent": spent,
                    }
                )
            return jsonify({"status": "success", "data": {"alerts": alerts}})
    except Exception as e:
        app.logger.error(f"Failed to get alerts for user {user_id}: {e}")
        return jsonify({"status": "error", "message": "Could not retrieve alerts"}), 500


@app.route("/budgets", methods=["POST"])
def set_budget():
    # (Keep this function as provided in your sample)
    try:
        data = validate_input(request.get_json(), ["user_id", "category", "limit"])
        user_id = int(data["user_id"])
        category = validate_category(data["category"])
        limit = validate_amount(data["limit"])
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM users WHERE id=?", (user_id,))
            if not cursor.fetchone():
                return jsonify({"status": "error", "message": "User not found"}), 404
            # Reset current_spend when setting/replacing budget for the month
            cursor.execute(
                "INSERT OR REPLACE INTO budgets (user_id, category, monthly_limit, current_spend) VALUES (?, ?, ?, 0)",
                (user_id, category, limit),
            )
            conn.commit()
            return (
                jsonify(
                    {
                        "status": "success",
                        "data": {
                            "user_id": user_id,
                            "category": category,
                            "monthly_limit": limit,
                        },
                    }
                ),
                201,
            )
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Budget setting failed for user {user_id}: {e}")
        return jsonify({"status": "error", "message": f"Budget setting failed"}), 500


@app.route("/")  # Route for the base URL
def index():
    return render_template("test_ui.html")


@app.route("/transactions/<int:user_id>", methods=["GET"])
def get_transactions(user_id):
    """Retrieve transaction history for a specific user"""
    try:
        # Get optional query parameters for filtering
        category = request.args.get('category')
        days = request.args.get('days')
        flagged = request.args.get('flagged')
        limit = request.args.get('limit', 50)  # Default to 50 transactions
        
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute("SELECT 1 FROM users WHERE id=?", (user_id,))
            if not cursor.fetchone():
                return jsonify({"status": "error", "message": "User not found"}), 404
            
            # Build the query with potential filters
            query = "SELECT id, amount, category, timestamp, flagged FROM transactions WHERE user_id=?"
            params = [user_id]
            
            if category:
                query += " AND category=?"
                params.append(category)
                
            if days:
                try:
                    days_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=int(days))
                    query += " AND timestamp >= ?"
                    params.append(days_ago.strftime("%Y-%m-%d %H:%M:%S"))
                except ValueError:
                    return jsonify({"status": "error", "message": "Invalid 'days' parameter"}), 400
                    
            if flagged is not None:
                is_flagged = flagged.lower() in ['true', '1', 'yes']
                query += " AND flagged = ?"
                params.append(1 if is_flagged else 0)
            
            # Order by most recent first
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(int(limit))
            
            cursor.execute(query, params)
            transactions = []
            for id, amount, category, timestamp, flagged in cursor.fetchall():
                transactions.append({
                    "transaction_id": id,
                    "amount": amount,
                    "category": category,
                    "timestamp": timestamp,
                    "flagged": bool(flagged)
                })
            
            # Get total stats
            cursor.execute("SELECT COUNT(*), SUM(amount) FROM transactions WHERE user_id=?", (user_id,))
            count, total = cursor.fetchone()
            
            # Get category breakdown
            cursor.execute(
                "SELECT category, COUNT(*), SUM(amount) FROM transactions WHERE user_id=? GROUP BY category",
                (user_id,)
            )
            categories = {}
            for cat, cat_count, cat_total in cursor.fetchall():
                categories[cat] = {
                    "count": cat_count,
                    "total": cat_total
                }
            
            return jsonify({
                "status": "success",
                "data": {
                    "transactions": transactions,
                    "stats": {
                        "total_count": count or 0,
                        "total_amount": total or 0,
                        "categories": categories
                    }
                }
            }), 200
    except Exception as e:
        app.logger.error(f"Failed to get transactions for user {user_id}: {e}")
        return jsonify({"status": "error", "message": "Could not retrieve transactions"}), 500

@app.route('/analyze_csv', methods=['POST'])
def analyze_csv():
    """
    Handles CSV file upload, analyzes it using FinancialSummaryGenerator,
    and returns AI recommendations.
    """
    if 'csv_file' not in request.files:
        return jsonify({"status": "error", "message": "No CSV file part in the request"}), 400

    file = request.files['csv_file']
    user_id = request.form.get('user_id', '1') # Get user ID from form data, default to '1'

    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400

    if file and file.filename.endswith('.csv'):
        # --- Securely save the uploaded file temporarily ---
        temp_dir = tempfile.mkdtemp() # Create a temporary directory
        temp_filepath = os.path.join(temp_dir, file.filename)
        try:
            file.save(temp_filepath)
            app.logger.info(f"CSV file saved temporarily to: {temp_filepath}")

            # --- Initialize Generator ---
            generator = FinancialSummaryGenerator()

            # --- Attempt to Convert and Import ---
            # Optional: Convert if your CSV might not be in the exact expected format
            # converted_filepath = convert_csv(temp_filepath) # convert_csv should handle naming
            # if not converted_filepath:
            #     raise ValueError("CSV conversion failed.")
            # app.logger.info(f"CSV converted (if necessary) to: {converted_filepath}")

            # Import data using the potentially converted path
            # success = generator.import_from_csv(converted_filepath) 

            # --- OR Import Directly (if conversion is not needed or handled elsewhere) ---
            success = generator.import_from_csv(temp_filepath) # Use the direct temp path

            if not success:
                raise ValueError("Failed to import data from CSV.")

            # --- Perform Analysis & Get Recommendations ---
            generator.analyze_data()
            generator.generate_ai_recommendations() # This populates generator.recommendations [cite: 3]

            recommendations = generator.recommendations if hasattr(generator, 'recommendations') else []
            app.logger.info(f"Generated {len(recommendations)} recommendations for user {user_id} from CSV.")

            # --- Cleanup: Remove temporary file and directory ---
            os.remove(temp_filepath)
            # if converted_filepath != temp_filepath: # Remove converted file if different
            #     os.remove(converted_filepath) 
            os.rmdir(temp_dir)

            # --- Return Success Response ---
            return jsonify({
                "status": "success",
                "data": {
                    "user_id": user_id, # Include user ID in response if useful
                    "recommendations": recommendations 
                }
            }), 200

        except Exception as e:
             # --- Cleanup on Error ---
             if os.path.exists(temp_filepath):
                 os.remove(temp_filepath)
             # if 'converted_filepath' in locals() and os.path.exists(converted_filepath):
             #     os.remove(converted_filepath)
             if os.path.exists(temp_dir):
                os.rmdir(temp_dir)

             app.logger.error(f"CSV Analysis failed: {e}", exc_info=True)
             return jsonify({"status": "error", "message": f"An error occurred during analysis: {e}"}), 500
        finally:
             # Ensure cleanup happens even if unexpected errors occur before explicit removal
             if os.path.exists(temp_dir):
                try:
                    if os.path.exists(temp_filepath): os.remove(temp_filepath)
                    # if 'converted_filepath' in locals() and os.path.exists(converted_filepath): os.remove(converted_filepath)
                    os.rmdir(temp_dir)
                except OSError as cleanup_error:
                    app.logger.error(f"Error during temp directory cleanup: {cleanup_error}")


    else:
        return jsonify({"status": "error", "message": "Invalid file type. Please upload a .csv file"}), 400
# --- Main Execution ---
if __name__ == "__main__":
    # Configure logging
    import logging

    logging.basicConfig(level=logging.INFO)  # Use INFO or DEBUG
    app.logger.setLevel(logging.INFO)

    create_db()  # Ensure DB exists
    # Consider using a production server like gunicorn or waitress instead of Flask's built-in server
    app.run(debug=True)  # debug=True is helpful for development, disable for production
