import os
import json
from flask import Flask, request
from twilio.rest import Client
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ===== Environment variables =====
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

# ===== Twilio Client =====
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# ===== Google Sheets Setup =====
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)
sheet = gc.open("LoyaltyProgram").sheet1  # Replace with your spreadsheet name

# ===== Flask App =====
app = Flask(__name__)

def send_whatsapp(to_number, message):
    client.messages.create(
        from_='whatsapp:' + TWILIO_WHATSAPP_NUMBER,
        to='whatsapp:' + to_number,
        body=message
    )

@app.route("/whatsapp", methods=['POST'])
def whatsapp_webhook():
    incoming_msg = request.values.get('Body', '').strip()
    from_number = request.values.get('From', '').replace('whatsapp:', '')

    # ==== Command: HI ====
    if incoming_msg.lower() == "hi":
        reply = (
            "👋 Welcome to Petroflexi Energies Limited Loyalty Program!\n"
            "Commands you can use:\n"
            "JOIN <Your Name> - set your name\n"
            "BUY <Voucher> - earn points\n"
            "CHECK - see your points\n"
            "REDEEM - redeem points\n"
            "HISTORY - view your points history"
        )
        send_whatsapp(from_number, reply)
        return '', 200

    # ==== Command: JOIN ====
    if incoming_msg.lower().startswith("join "):
        name = incoming_msg[5:].strip()
        # Save user to sheet if not exists
        users = sheet.col_values(1)
        if name not in users:
            sheet.append_row([name, 0])  # Name, Points
        reply = f"Dear {name}, your registration was successful. Kindly type BUY followed by the voucher number given to you by the staff to earn points."
        send_whatsapp(from_number, reply)
        return '', 200

    # ==== Command: BUY ====
    if incoming_msg.lower().startswith("buy "):
        voucher = incoming_msg[4:].strip()
        # Here you should verify voucher using verify.py logic
        # For demonstration, assume all vouchers starting with "GAS" are valid
        users = sheet.get_all_records()
        user_row = None
        user_name = None
        for idx, u in enumerate(users, start=2):
            if from_number == u.get('Phone', from_number):  # Replace with actual phone check
                user_row = idx
                user_name = u['Name']
        if voucher.startswith("GAS"):
            # Increment points
            if user_row:
                current_points = int(sheet.cell(user_row, 2).value)
                sheet.update_cell(user_row, 2, current_points + 1)
            reply = f"Dear {user_name}, congratulations 👏 points updated successfully. Kindly send CHECK to see your current point balance."
        else:
            reply = f"Oops, sorry {user_name}, voucher is invalid. Kindly recheck and enter again."
        send_whatsapp(from_number, reply)
        return '', 200

    # ==== Command: CHECK ====
    if incoming_msg.lower() == "check":
        users = sheet.get_all_records()
        user_name = from_number
        points = 0
        for u in users:
            if from_number == u.get('Phone', from_number):
                user_name = u['Name']
                points = u['Points']
        send_whatsapp(from_number, f"💎 Your total points: {points}")
        return '', 200

    # ==== Command: REDEEM ====
    if incoming_msg.lower() == "redeem":
        users = sheet.get_all_records()
        user_row = None
        user_name = from_number
        points = 0
        for idx, u in enumerate(users, start=2):
            if from_number == u.get('Phone', from_number):
                user_row = idx
                user_name = u['Name']
                points = u['Points']
        if points >= 10:
            sheet.update_cell(user_row, 2, points - 10)
            reply = f"Congratulations {user_name}, you have 🎉 redeemed 10 points for a reward!"
        else:
            reply = f"⚠ You need at least 10 points to redeem. Current: {points}"
        send_whatsapp(from_number, reply)
        return '', 200

    # ==== Command: HISTORY ====
    if incoming_msg.lower() == "history":
        # Send the full history from sheet
        records = sheet.get_all_records()
        history_text = ""
        for r in records:
            history_text += f"{r['Name']}: {r['Points']} points\n"
        send_whatsapp(from_number, history_text or "No history found.")
        return '', 200

    # Unknown command
    send_whatsapp(from_number, "⚠ Unknown command. Please type HI to see available commands.")
    return '', 200

if __name__ == "__main__":
    app.run(debug=True)
