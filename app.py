import os
import json
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# Environment variables for credentials
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON")
TWILIO_WHATSAPP_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER")

# Google Sheets setup
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)
sheet = gc.open("LoyaltyProgram").sheet1  # Sheet name

# Helper functions
def get_user_row(name):
    records = sheet.get_all_records()
    for idx, rec in enumerate(records, start=2):  # Sheet rows start at 2
        if rec.get("Name") == name:
            return idx, rec
    return None, None

def update_points(row, points):
    sheet.update_cell(row, 2, points)  # Assuming column B is Points

def append_history(name, action):
    sheet.append_row([name, action])

# Webhook for Twilio WhatsApp
@app.route("/whatsapp", methods=['POST'])
def whatsapp_webhook():
    incoming_msg = request.values.get('Body', '').strip()
    from_number = request.values.get('From', '')
    resp = MessagingResponse()
    msg = resp.message()

    incoming_parts = incoming_msg.split()
    command = incoming_parts[0].upper() if incoming_parts else ""

    # HI command
    if command == "HI":
        msg.body(
            "👋 Welcome to Petroflexi energies limited loyal program! Here are the commands you can use:\n"
            "JOIN <Your Name> - set your name\n"
            "BUY <voucher> - earn points\n"
            "CHECK - see your points\n"
            "REDEEM - redeem points\n"
            "HISTORY - view your points history"
        )
    # JOIN command
    elif command == "JOIN" and len(incoming_parts) > 1:
        name = " ".join(incoming_parts[1:])
        row, _ = get_user_row(name)
        if row:
            msg.body(f"Dear {name}, you are already registered. Send BUY <voucher> to earn points.")
        else:
            sheet.append_row([name, 0])  # Initialize points to 0
            msg.body(
                f"Dear {name}, your registration was successful. Kindly type BUY followed by the voucher number given to you by the Staff to earn points."
            )
    # BUY command
    elif command == "BUY" and len(incoming_parts) > 1:
        voucher = incoming_parts[1]
        # Implement voucher validation logic here
        # Example: pseudo logic (replace with real sheet validation)
        name_row, user_data = get_user_row("Demo User")  # Replace "Demo User" with your lookup
        if not name_row:
            msg.body("You need to JOIN first.")
        elif voucher == "GAS-LKM0P":
            points = user_data.get("Points", 0) + 10
            update_points(name_row, points)
            append_history("Demo User", f"BUY {voucher}")
            msg.body(f"Dear Demo User, congratulations 👏 points updated successfully. Kindly send CHECK to see your current point balance.")
        else:
            msg.body(f"Oops, sorry Demo User, voucher is invalid. Kindly recheck and enter again.")
    # CHECK command
    elif command == "CHECK":
        name_row, user_data = get_user_row("Demo User")  # Replace with correct name
        if user_data:
            points = user_data.get("Points", 0)
            msg.body(f"💎 Your total points: {points}")
        else:
            msg.body("You need to JOIN first.")
    # REDEEM command
    elif command == "REDEEM":
        name_row, user_data = get_user_row("Demo User")  # Replace with correct name
        if user_data:
            points = user_data.get("Points", 0)
            if points >= 10:
                points -= 10
                update_points(name_row, points)
                append_history("Demo User", "REDEEM 10 points")
                msg.body("Congratulations! You have 🎉 Redeemed 10 points for a reward!")
            else:
                msg.body(f"⚠ You need at least 10 points to redeem. Current: {points}")
        else:
            msg.body("You need to JOIN first.")
    # HISTORY command
    elif command == "HISTORY":
        records = sheet.get_all_records()
        history_text = ""
        for rec in records:
            history_text += f"{rec.get('Name')} - {rec.get('Points')} points\n"
        msg.body(history_text or "No history yet.")
    else:
        msg.body("Unknown command. Please send HI to see available commands.")

    return str(resp)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
