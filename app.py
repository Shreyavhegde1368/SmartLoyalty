import os
import secrets
import io
import base64
from decimal import Decimal, InvalidOperation
from functools import wraps

import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
import qrcode

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-only-change-this-secret")
CSRFProtect(app)


def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "smartloyalty"),
    )


def query_one(sql, params=()):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()


def query_all(sql, params=()):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def login_required(role=None):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                flash("Please sign in first.", "warning")
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                flash("You do not have permission to access that page.", "danger")
                return redirect(url_for("index"))
            return fn(*args, **kwargs)
        return wrapped
    return decorator


@app.context_processor
def inject_globals():
    return {"current_user": session.get("name"), "current_role": session.get("role")}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register-business", methods=["GET", "POST"])
def register_business():
    if request.method == "POST":
        business_name = request.form.get("business_name", "").strip()
        business_type = request.form.get("business_type", "").strip()
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not all([business_name, business_type, name, email, password]):
            flash("Please complete every required field.", "danger")
            return render_template("register_business.html")
        if len(password) < 8:
            flash("Use a password with at least 8 characters.", "danger")
            return render_template("register_business.html")
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO businesses (name, business_type, email) VALUES (%s,%s,%s)",
                (business_name, business_type, email),
            )
            business_id = cur.lastrowid
            cur.execute(
                "INSERT INTO users (business_id, full_name, email, password_hash) VALUES (%s,%s,%s,%s)",
                (business_id, name, email, generate_password_hash(password)),
            )
            user_id = cur.lastrowid
            cur.executemany(
                "INSERT INTO rewards (business_id, reward_name, description, points_required) VALUES (%s,%s,%s,%s)",
                [
                    (business_id, "₹50 off", "Get ₹50 off your next purchase.", 100),
                    (business_id, "Free add-on", "Enjoy a complimentary add-on.", 150),
                    (business_id, "₹100 off", "Get ₹100 off your next purchase.", 200),
                ],
            )
            conn.commit()
            session.clear()
            session.update(user_id=user_id, business_id=business_id,
                           name=name, role="owner", email=email)
            flash("Your business account is ready. Welcome to SmartLoyalty!", "success")
            return redirect(url_for("business_dashboard"))
        except Error as exc:
            conn.rollback()
            app.logger.exception("Business registration failed")
            flash("Could not create account. Check that the email is unused and the database is available.", "danger")
        finally:
            cur.close()
            conn.close()
    return render_template("register_business.html")


@app.route("/register-customer", methods=["GET", "POST"])
def register_customer():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip() or None
        password = request.form.get("password", "")
        consent = 1 if request.form.get("consent") == "yes" else 0
        if not all([name, email, password]):
            flash("Name, email and password are required.", "danger")
            return render_template("register_customer.html")
        if len(password) < 8:
            flash("Use a password with at least 8 characters.", "danger")
            return render_template("register_customer.html")
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO customers (full_name,email,phone,marketing_consent,password_hash) VALUES (%s,%s,%s,%s,%s)",
                (name, email, phone, consent, generate_password_hash(password)),
            )
            conn.commit()
            customer_id = cur.lastrowid
            session.update(user_id=customer_id, name=name, role="customer", email=email)
            flash("Customer account created successfully.", "success")
            return redirect(url_for("customer_dashboard"))
        except Error as exc:
            flash("Could not register. This email may already be in use. " + str(exc), "danger")
        finally:
            if "cur" in locals():
                cur.close()
            if "conn" in locals():
                conn.close()
    return render_template("register_customer.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = query_one("SELECT user_id, full_name, email, password_hash, role, business_id FROM users WHERE email=%s", (email,))
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session.update(user_id=user["user_id"], name=user["full_name"],
                           email=user["email"], role=user["role"], business_id=user["business_id"])
            return redirect(url_for("business_dashboard" if user["role"] == "owner" else "index"))
        customer = query_one("SELECT customer_id, full_name, email, password_hash FROM customers WHERE email=%s", (email,))
        if customer and check_password_hash(customer["password_hash"], password):
            session.clear()
            session.update(user_id=customer["customer_id"], name=customer["full_name"],
                           email=customer["email"], role="customer")
            return redirect(url_for("customer_dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("index"))


@app.route("/business")
@login_required("owner")
def business_dashboard():
    bid = session["business_id"]
    stats = query_one("""
        SELECT COUNT(DISTINCT la.customer_id) customers,
               COUNT(p.purchase_id) purchases,
               COALESCE(SUM(p.amount),0) revenue,
               COALESCE(AVG(f.rating),0) avg_rating
        FROM loyalty_accounts la
        LEFT JOIN purchases p ON p.account_id=la.account_id
        LEFT JOIN feedback f ON f.purchase_id=p.purchase_id
        WHERE la.business_id=%s
    """, (bid,)) or {}
    recent = query_all("""
        SELECT p.purchase_id, c.full_name, p.amount, p.purchase_date, p.feedback_submitted
        FROM purchases p
        JOIN loyalty_accounts la ON la.account_id=p.account_id
        JOIN customers c ON c.customer_id=la.customer_id
        WHERE la.business_id=%s ORDER BY p.purchase_date DESC LIMIT 8
    """, (bid,))
    feedback = query_all("""
        SELECT c.full_name, f.rating, f.comments, f.submitted_at
        FROM feedback f JOIN purchases p ON p.purchase_id=f.purchase_id
        JOIN loyalty_accounts la ON la.account_id=p.account_id
        JOIN customers c ON c.customer_id=la.customer_id
        WHERE la.business_id=%s ORDER BY f.submitted_at DESC LIMIT 6
    """, (bid,))
    return render_template("business_dashboard.html", stats=stats, recent=recent, feedback=feedback)


@app.route("/purchase/new", methods=["GET", "POST"])
@login_required("owner")
def new_purchase():
    if request.method == "POST":
        email = request.form.get("customer_email", "").strip().lower()
        try:
            amount = Decimal(request.form.get("amount", "0"))
            if amount <= 0 or amount > Decimal("1000000"):
                raise InvalidOperation
        except (InvalidOperation, TypeError):
            flash("Enter a valid purchase amount.", "danger")
            return render_template("new_purchase.html")
        customer = query_one("SELECT customer_id FROM customers WHERE email=%s", (email,))
        if not customer:
            flash("No customer found with that email. Ask them to register first.", "warning")
            return render_template("new_purchase.html")
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO loyalty_accounts (customer_id,business_id) VALUES (%s,%s) "
                "ON DUPLICATE KEY UPDATE account_id=LAST_INSERT_ID(account_id)",
                (customer["customer_id"], session["business_id"]),
            )
            account_id = cur.lastrowid
            token = secrets.token_urlsafe(32)
            cur.execute(
                "INSERT INTO purchases (account_id,amount,qr_token) VALUES (%s,%s,%s)",
                (account_id, str(amount), token),
            )
            conn.commit()
            feedback_url = url_for("submit_feedback", token=token, _external=True)
            qr = qrcode.make(feedback_url)
            qr_buffer = io.BytesIO()
            qr.save(qr_buffer, format="PNG")
            qr_image = base64.b64encode(qr_buffer.getvalue()).decode("ascii")
            flash("Purchase saved. Share this feedback link or QR code with the customer.", "success")
            return render_template("purchase_created.html", feedback_url=feedback_url, qr_image=qr_image, token=token)
        except Error as exc:
            conn.rollback()
            app.logger.exception("Purchase creation failed")
            flash("Could not save purchase. Check the database and try again.", "danger")
        finally:
            cur.close()
            conn.close()
    return render_template("new_purchase.html")


@app.route("/feedback/<token>", methods=["GET", "POST"])
def submit_feedback(token):
    purchase = query_one("""
        SELECT p.purchase_id,p.amount,p.feedback_submitted,b.name business_name
        FROM purchases p JOIN loyalty_accounts la ON la.account_id=p.account_id
        JOIN businesses b ON b.business_id=la.business_id WHERE p.qr_token=%s
    """, (token,))
    if not purchase:
        return render_template("message.html", title="Link not found", message="This feedback link is invalid or has expired.")
    if purchase["feedback_submitted"]:
        return render_template("message.html", title="Already submitted", message="Feedback has already been submitted for this purchase.")
    if request.method == "POST":
        try:
            rating = int(request.form.get("rating", "0"))
        except ValueError:
            rating = 0
        comments = request.form.get("comments", "").strip()
        if rating not in range(1, 6):
            flash("Please choose a rating from 1 to 5.", "danger")
            return render_template("feedback.html", purchase=purchase)
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("SELECT account_id,feedback_submitted FROM purchases WHERE purchase_id=%s FOR UPDATE", (purchase["purchase_id"],))
            locked = cur.fetchone()
            if not locked or locked[1]:
                conn.rollback()
                return render_template("message.html", title="Already submitted", message="Feedback has already been submitted.")
            account_id = locked[0]
            earned = int(Decimal(str(purchase["amount"])) // Decimal("100")) + 5
            cur.execute("INSERT INTO feedback (purchase_id,rating,comments) VALUES (%s,%s,%s)",
                        (purchase["purchase_id"], rating, comments or None))
            cur.execute("UPDATE purchases SET feedback_submitted=TRUE WHERE purchase_id=%s", (purchase["purchase_id"],))
            cur.execute("UPDATE loyalty_accounts SET points_balance=points_balance+%s WHERE account_id=%s",
                        (earned, account_id))
            cur.execute(
                "INSERT INTO points_transactions (account_id,purchase_id,transaction_type,points,description) VALUES (%s,%s,'earned',%s,%s)",
                (account_id, purchase["purchase_id"], earned, "Purchase and feedback reward"),
            )
            conn.commit()
            return render_template("message.html", title="Thank you!", message=f"Your feedback was saved. You earned {earned} loyalty points.")
        except Error as exc:
            conn.rollback()
            app.logger.exception("Feedback submission failed")
            flash("Could not save feedback. Please try again.", "danger")
        finally:
            cur.close()
            conn.close()
    return render_template("feedback.html", purchase=purchase)


@app.route("/customer")
@login_required("customer")
def customer_dashboard():
    customer_id = session["user_id"]
    accounts = query_all("""
        SELECT la.account_id,la.points_balance,b.name business_name,b.business_type
        FROM loyalty_accounts la JOIN businesses b ON b.business_id=la.business_id
        WHERE la.customer_id=%s ORDER BY b.name
    """, (customer_id,))
    purchases = query_all("""
        SELECT p.purchase_id,p.amount,p.purchase_date,b.name business_name,p.feedback_submitted
        FROM purchases p JOIN loyalty_accounts la ON la.account_id=p.account_id
        JOIN businesses b ON b.business_id=la.business_id
        WHERE la.customer_id=%s ORDER BY p.purchase_date DESC LIMIT 10
    """, (customer_id,))
    return render_template("customer_dashboard.html", accounts=accounts, purchases=purchases)


@app.route("/rewards/<int:account_id>")
@login_required("customer")
def rewards_page(account_id):
    account = query_one("""
        SELECT la.account_id,la.points_balance,b.name business_name,b.business_id
        FROM loyalty_accounts la JOIN businesses b ON b.business_id=la.business_id
        WHERE la.account_id=%s AND la.customer_id=%s
    """, (account_id, session["user_id"]))
    if not account:
        flash("Loyalty account not found.", "danger")
        return redirect(url_for("customer_dashboard"))
    rewards = query_all("SELECT * FROM rewards WHERE business_id=%s AND active=TRUE ORDER BY points_required",
                        (account["business_id"],))
    return render_template("rewards.html", account=account, rewards=rewards)


@app.route("/redeem/<int:account_id>/<int:reward_id>", methods=["POST"])
@login_required("customer")
def redeem_reward(account_id, reward_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT la.points_balance,r.points_required,r.reward_name
            FROM loyalty_accounts la JOIN rewards r ON r.business_id=la.business_id
            WHERE la.account_id=%s AND r.reward_id=%s AND la.customer_id=%s AND r.active=TRUE
            FOR UPDATE
        """, (account_id, reward_id, session["user_id"]))
        row = cur.fetchone()
        if not row:
            flash("Reward or loyalty account not found.", "danger")
        elif row[0] < row[1]:
            flash("You do not have enough points for this reward.", "warning")
        else:
            cur.execute("UPDATE loyalty_accounts SET points_balance=points_balance-%s WHERE account_id=%s",
                        (row[1], account_id))
            cur.execute("INSERT INTO points_transactions (account_id,transaction_type,points,description) VALUES (%s,'spent',%s,%s)",
                        (account_id, -row[1], "Redeemed: " + row[2]))
            cur.execute("INSERT INTO redemptions (account_id,reward_id,points_spent) VALUES (%s,%s,%s)",
                        (account_id, reward_id, row[1]))
            conn.commit()
            flash("Reward redeemed successfully!", "success")
    except Error as exc:
        conn.rollback()
        app.logger.exception("Reward redemption failed")
        flash("Reward redemption failed. Please try again.", "danger")
    finally:
        cur.close()
        conn.close()
    return redirect(url_for("rewards_page", account_id=account_id))


@app.errorhandler(500)
def server_error(error):
    return render_template("message.html", title="Something went wrong",
                           message="The application encountered an error. Check your terminal for details."), 500


if __name__ == "__main__":
    app.run(
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
    )
