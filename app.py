# app.py
import os
from flask import Flask, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from twilio.rest import Client

app = Flask(__name__)

# ---------------- Environment Variables ----------------
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER")
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON")

# ---------------- Twilio Setup ----------------
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# ---------------- Google Sheets Setup ----------------
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
# Load creds from environment variable JSON
import json
creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)

# Main customer sheet
sheet = gc.open("LoyaltyProgram").sheet1
# Voucher sheet
voucher_sheet = gc.open("LoyaltyProgram").worksheet("Vouchers")
# History sheet
history_sheet = gc.open("LoyaltyProgram").worksheet("History")

# ---------------- Helper Functions ----------------
def find_customer(phone):
    all_data = sheet.get_all_records()
    for row in all_data:
        if str(row["Phone"]) == str(phone):
            return row
    return None

def send_whatsapp_message(to_number, message):
    twilio_client.messages.create(
        from_='whatsapp:' + TWILIO_WHATSAPP_NUMBER,
        to='whatsapp:' + to_number,
        body=message
    )

# ---------------- Flask Routes ----------------
@app.route("/sms", methods=["POST"])
def sms_reply():
    incoming_msg = request.form.get('Body', '').strip()
    from_number = request.form.get('From', '').replace("whatsapp:", "")
    
    # ---------------- Registration ----------------
    if incoming_msg.lower().startswith("join"):
        name = incoming_msg[4:].strip()
        if find_customer(from_number):
            send_whatsapp_message(from_number, f"Dear {name}, this number already exists in database")
            return jsonify({"status": "exists"})
        # Append new customer
        sheet.append_row([from_number, name, 0, '', f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Joined as {name}"])
        send_whatsapp_message(from_number, f"Dear {name}, your registration was successful, kindly type Buy followed by the voucher number given to you by the Staff to Earn points")
        return jsonify({"status": "joined"})
    
    # ---------------- Buy Voucher ----------------
    elif incoming_msg.upper().startswith("BUY"):
        voucher_code = incoming_msg.split()[1].strip().upper()
        customer = find_customer(from_number)
        if not customer:
            send_whatsapp_message(from_number, "You need to join first by typing 'Join YourName'")
            return jsonify({"status": "not_registered"})
        
        # Find voucher
        vouchers = voucher_sheet.get_all_records()
        voucher_row = next((v for v in vouchers if v["Voucher"] == voucher_code), None)
        
        if not voucher_row:
            send_whatsapp_message(from_number, f"Oops, sorry {customer['Name']} voucher is invalid kindly recheck and enter again")
            return jsonify({"status": "invalid_voucher"})
        if voucher_row["Status"].lower() == "used":
            send_whatsapp_message(from_number, f"Oops, sorry {customer['Name']} voucher is already used by another customer")
            return jsonify({"status": "voucher_used"})
        
        # Mark voucher as used
        cell = voucher_sheet.find(voucher_code)
        voucher_sheet.update_cell(cell.row, cell.col + 1, f"Used by {customer['Name']} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        # Update points
        new_points = int(customer['Points']) + 1
        customer_row = sheet.find(str(from_number)).row
        sheet.update_cell(customer_row, 3, new_points)
        # Log history
        history_sheet.append_row([from_number, customer["Name"], voucher_code, datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        send_whatsapp_message(from_number, f"Dear {customer['Name']}, congratulations 👏 points updated successfully, Kindly send CHECK to see your current point Balance")
        return jsonify({"status": "voucher_redeemed"})
    
    # ---------------- Check Balance ----------------
    elif incoming_msg.lower() == "check":
        customer = find_customer(from_number)
        if customer:
            send_whatsapp_message(from_number, f"Dear {customer['Name']}, your current points balance is {customer['Points']}")
            return jsonify({"status": "checked"})
        else:
            send_whatsapp_message(from_number, "You are not registered yet.")
            return jsonify({"status": "not_registered"})
    
    # ---------------- Default ----------------
    else:
        send_whatsapp_message(from_number, "Invalid command. Use JOIN, BUY <voucher>, or CHECK.")
        return jsonify({"status": "invalid_command"})

if __name__ == "__main__":
    app.run(debug=True)
