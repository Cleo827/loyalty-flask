import os
import json
from datetime import datetime
from flask import Flask, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from twilio.rest import Client

app = Flask(__name__)

# ---------------- Google Sheets Setup ----------------
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Load Google credentials from environment variable
google_creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
creds_dict = json.loads(google_creds_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)

# Sheets
sheet = gc.open("LoyaltyProgram").sheet1
voucher_sheet = gc.open("LoyaltyProgram").worksheet("Vouchers")

# ---------------- Twilio Setup ----------------
twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER")
client = Client(twilio_sid, twilio_token)

# ---------------- Helper Functions ----------------
def get_customer_data():
    return sheet.get_all_records()

def verify_voucher(phone, voucher_code):
    records = get_customer_data()
    customer_row = None
    for idx, record in enumerate(records, start=2):  # headers in row 1
        if str(record['Phone']) == str(phone):
            customer_row = idx
            break

    if not customer_row:
        return False, "Customer not found."

    vouchers = voucher_sheet.col_values(1)
    if voucher_code not in vouchers:
        return False, "Invalid voucher code."

    # Mark voucher as used
    row_index = vouchers.index(voucher_code) + 1
    voucher_sheet.update_cell(row_index, 2, f"Used by {phone} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Update customer points/history
    current_points = records[customer_row-2]['Points']
    sheet.update_cell(customer_row, 3, current_points + 1)

    return True, "Voucher redeemed successfully."

# ---------------- Flask Route for Twilio ----------------
@app.route("/sms", methods=["POST"])
def sms_reply():
    from_number = request.form.get("From")
    body = request.form.get("Body").strip()

    # Expected format: VOUCHERCODE
    voucher_code = body.upper()
    success, message = verify_voucher(from_number.replace("whatsapp:", ""), voucher_code)

    # Send response back via Twilio
    client.messages.create(
        body=message,
        from_=twilio_whatsapp_number,
        to=from_number
    )

    return jsonify({"status": "success", "message": message})

if __name__ == "__main__":
    app.run(debug=True)
