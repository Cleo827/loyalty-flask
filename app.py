import os
from flask import Flask, request, jsonify
from twilio.rest import Client
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Flask app
app = Flask(__name__)

# Environment variables (never hardcode secrets!)
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER")
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON")

# Initialize Twilio client
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Google Sheet setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)
sheet = gc.open("LoyaltyProgram").sheet1  # your sheet name

# Helper functions
def send_whatsapp(to, message):
    client.messages.create(
        from_=f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",
        to=f"whatsapp:{to}",
        body=message
    )

def get_points_history(name):
    records = sheet.get_all_records()
    history = [r for r in records if r['Name'].lower() == name.lower()]
    return history

def get_total_points(name):
    history = get_points_history(name)
    return sum(int(r['Points']) for r in history) if history else 0

# Webhook routes
@app.route("/whatsapp", methods=["POST"])
@app.route("/sms", methods=["POST"])
def webhook():
    incoming_msg = request.values.get("Body", "").strip()
    from_number = request.values.get("From", "").replace("whatsapp:", "")

    parts = incoming_msg.split()
    command = parts[0].lower() if parts else ""

    if command == "hi":
        msg = (
            "👋 Welcome to Petroflexi energies limited loyal program! Here are the commands you can use:\n"
            "JOIN <Your Name> - set your name\n"
            "BUY <voucher> - earn points\n"
            "CHECK - see your points\n"
            "REDEEM - redeem points\n"
            "HISTORY - view your points history"
        )
    elif command == "join" and len(parts) > 1:
        name = " ".join(parts[1:])
        msg = f"Dear {name}, your registration was successful. Kindly type BUY followed by the voucher number given to you by the Staff to earn points"
    elif command == "buy" and len(parts) > 1:
        voucher = parts[1]
        name = "Customer"  # You can fetch this from a registration record if needed
        # Check voucher validity
        records = sheet.get_all_records()
        used_vouchers = [r['Voucher'] for r in records]
        if voucher in used_vouchers:
            msg = f"Oops, sorry {name}, voucher is already used by another customer."
        else:
            # Simulate updating points
            sheet.append_row([name, voucher, 10])  # Example: give 10 points per voucher
            msg = f"Dear {name}, congratulations 👏 points updated successfully. Kindly send CHECK to see your current point balance."
    elif command == "check":
        name = "Customer"  # Replace with registered name lookup
        total_points = get_total_points(name)
        msg = f"💎 Your total points: {total_points}"
    elif command == "redeem":
        name = "Customer"
        total_points = get_total_points(name)
        if total_points >= 10:
            # Redeem 10 points
            records = get_points_history(name)
            # Update points in Google Sheet logic here
            msg = "Congratulations 🎉 you have Redeemed 10 points for a reward!"
        else:
            msg = f"⚠ You need at least 10 points to redeem. Current: {total_points}"
    elif command == "history":
        name = "Customer"
        history = get_points_history(name)
        if history:
            msg = "\n".join([f"{r['Voucher']} -> {r['Points']} points" for r in history])
        else:
            msg = "No points history found."
    else:
        msg = "Command not recognized. Please send HI to see available commands."

    send_whatsapp(from_number, msg)
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    import json
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
