# SmartLoyalty

SmartLoyalty is a college-project MVP built with Flask and MySQL. It lets small businesses record purchases, collect purchase-specific ratings and comments, and reward customer loyalty.

## How a purchase and feedback work

1. The customer creates a SmartLoyalty account.
2. The business owner records a purchase using the customer's email and amount.
3. The app creates a unique feedback link and QR code for that purchase. The business shows or shares the QR code at checkout.
4. The customer scans it, selects a 1–5 rating, and can leave a comment. The customer does not need to sign in to submit feedback. Each purchase link can be used once.
5. The customer earns `floor(purchase amount / 100) + 5` points. They can sign in later to see their balance and redeem a reward.
6. The business dashboard shows purchases and submitted feedback.

For an in-person scan, the customer's phone must be able to reach the app. A local `127.0.0.1` link works only on the computer running the app. Use the computer's LAN address with both devices on the same Wi-Fi, or deploy the app to a public HTTPS address. A public GitHub repository by itself does not host or run the Flask app.

## Features

- Business and customer registration and sign-in with password hashing.
- Business dashboard with customer, purchase, sales, and feedback summaries.
- Purchase recording for registered customers.
- One-time, purchase-specific feedback links and QR codes.
- Ratings from 1 to 5 and optional written comments.
- Loyalty point balances, transaction records, reward catalogue, and redemption.
- CSRF protection on forms.

## Requirements

- Python 3.10 or newer
- MySQL Server 8

## Setup on Windows PowerShell

Open PowerShell in the cloned project folder:

```powershell
Set-Location path\to\SmartLoyalty
```

Create the database tables (safe to run again because the schema uses `IF NOT EXISTS`):

```powershell
Get-Content -Raw database\schema.sql | & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p -e "USE smartloyalty; SHOW TABLES;"
```

Create and configure the local environment file. Keep `.env` private; it is excluded by `.gitignore`.

```powershell
Copy-Item .env.example .env
notepad .env
```

Set `DB_USER`, `DB_PASSWORD`, `DB_NAME=smartloyalty`, and replace `SECRET_KEY` with a long random value. Do not commit `.env`.

Create a virtual environment inside the cloned project and run the app:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>. Keep the terminal open while the app runs. Press Ctrl+C to stop it. If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process Bypass` in that terminal and activate again.

### Scan the QR code with a phone on the same Wi-Fi

Set `FLASK_HOST=0.0.0.0` in `.env`, restart the app, and open `http://<computer-LAN-IP>:5000` on the phone. Record the purchase after opening the app through that address so the QR code contains the reachable LAN address. The computer firewall may ask to allow Python on a private network.

## Demo checklist

- [ ] Register a business and confirm its dashboard opens.
- [ ] Register a customer with a separate email.
- [ ] Sign in as the business, record the customer's purchase, and confirm the feedback link and QR appear.
- [ ] Open the link or scan the QR, submit a rating and comment, and confirm the link cannot be submitted twice.
- [ ] Sign in as the customer and check the points balance.
- [ ] Accumulate enough points to redeem a reward and confirm the balance decreases.
- [ ] Sign in as the business and confirm the purchase and feedback appear in its dashboard.

## Database tables

The schema creates nine tables: `businesses`, `users`, `customers`, `loyalty_accounts`, `purchases`, `feedback`, `points_transactions`, `rewards`, and `redemptions`.

## Scope and deployment

This MVP is for a classroom demonstration. It does not include email verification, account recovery, staff management, real payment processing, or production deployment configuration. A publicly usable instance needs a hosted MySQL database, a public HTTPS app host, and private deployment environment variables. Never put database credentials or real customer records in a public repository. Review security, privacy, backups, and applicable data-protection requirements before real-world use.
