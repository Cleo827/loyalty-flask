from flask import Flask, request, jsonify
from twilio.rest import Client
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

app = Flask(__name__)

# Environment variables
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER")
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON")  # JSON string

# Twilio client
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
creds_dict = eval(GOOGLE_CREDENTIALS_JSON)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)
sheet = gc.open("gsa-loyalty").sheet1  # your sheet name

# Helper functions
def get_user_points(name):
    try:
        cell = sheet.find(name)
        points = int(sheet.cell(cell.row, 2).value)  # assuming points are in column B
        return points
    except:
        return 0

def update_user_points(name, points):
    try:
        cell = sheet.find(name)
        current_points = int(sheet.cell(cell.row, 2).value)
        sheet.update_cell(cell.row, 2, current_points + points)
        return True
    except:
        return False

def redeem_points(name, required=10):
    current = get_user_points(name)
    if current >= required:
        cell = sheet.find(name)
        sheet.update_cell(cell.row, 2, current - required)
        return True, required
    else:
        return False, current

@app.route("/incoming", methods=["POST"])
def incoming():
    incoming_msg = request.values.get("Body", "").strip()
    from_number = request.values.get("From", "")
    name = from_number.split(":")[-1]  # fallback to number if not joined

    response = ""
    parts = incoming_msg.split(" ", 1)
    command = parts[0].upper()

    if command == "HI":
        response = ("👋 Welcome to Petroflexi energies limited loyalty program! Here are the commands you can use:\n"
                    "JOIN <Your Name> - set your name\n"
                    "BUY <voucher> - earn points\n"
                    "CHECK - see your points\n"
                    "REDEEM - redeem points\n"
                    "HISTORY - view your points history")
    elif command == "JOIN" and len(parts) > 1:
        user_name = parts[1].strip()
        sheet.append_row([user_name, 0])  # initialize points to 0
        response = f"Dear {user_name}, your registration was successful. Kindly type BUY followed by the voucher number given to you by the Staff to earn points."
    elif command == "BUY" and len(parts) > 1:
        voucher = parts[1].strip()
        # Here you would validate the voucher using your verify_sheet logic
        valid, points, user_name, used = verify_voucher(voucher, from_number)
        if not valid:
            response = f"Oops, sorry {user_name}, voucher is invalid. Kindly recheck and enter again."
        elif used:
            response = f"Oops, sorry {user_name}, voucher is already used by another customer."
        else:
            update_user_points(user_name, points)
            response = f"Dear {user_name}, congratulations 👏 points updated successfully. Kindly send CHECK to see your current point balance."
    elif command == "CHECK":
        pts = get_user_points(name)
        response = f"💎 Your total points: {pts}"
    elif command == "REDEEM":
        success, val = redeem_points(name)
        if success:
            response = f"Congratulation you have 🎉 Redeemed {val} points for a reward!"
        else:
            response = f"⚠ You need at least 10 points to redeem. Current: {val}"
    elif command == "HISTORY":
        response = get_user_history(name)  # implement based on your sheet history
    else:
        response = "Command not recognized. Please use one of HI, JOIN, BUY, CHECK, REDEEM, HISTORY."

    client.messages.create(
        body=response,
        from_=f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",
        to=from_number
    )

    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
