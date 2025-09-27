import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ---------------- Environment Variables ----------------
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER")

# Google credentials JSON stored as string in environment variable
google_creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
creds_dict = json.loads(google_creds_json)

# ---------------- Google Sheets Setup ----------------
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)

# ---------------- Sheets ----------------
# Main customer sheet
sheet = gc.open("LoyaltyProgram").sheet1
# Voucher sheet
voucher_sheet = gc.open("LoyaltyProgram").worksheet("Vouchers")
# History log sheet
history_sheet = gc.open("LoyaltyProgram").worksheet("History")

# ---------------- Helper Functions ----------------
def get_customer(phone):
    """Retrieve customer record by phone number"""
    records = sheet.get_all_records()
    for record in records:
        if str(record['Phone']) == str(phone):
            return record
    return None

def redeem_voucher(phone, voucher_code):
    """Redeem a voucher for a customer"""
    customer = get_customer(phone)
    if not customer:
        return "Customer not found"

    # Check if voucher exists and is unused
    vouchers = voucher_sheet.get_all_records()
    voucher = next((v for v in vouchers if v['Code'] == voucher_code), None)
    if not voucher:
        return "Voucher not found"
    if voucher.get('Used') == 'Yes':
        return "Voucher already used"

    # Mark voucher as used
    cell = voucher_sheet.find(voucher_code)
    voucher_sheet.update_cell(cell.row, cell.col + 1, 'Yes')  # Assuming next column is 'Used'

    # Update customer points or log
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{now}: Redeemed voucher {voucher_code}"
    history_sheet.append_row([phone, log_entry])

    return "Voucher redeemed successfully"

# Example usage
if __name__ == "__main__":
    phone = "2348152830742"
    voucher_code = "GAS-DRG007"
    result = redeem_voucher(phone, voucher_code)
    print(result)
