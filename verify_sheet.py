import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from twilio.rest import Client

# Load secrets from environment variables
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER")
GOOGLE_CREDENTIALS_JSON = json.loads(os.environ.get("GOOGLE_CREDENTIALS_JSON"))

# Twilio client
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Google Sheet setup
scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_CREDENTIALS_JSON, scope)
gc = gspread.authorize(creds)

SHEET_NAME = "loyalty"  # Replace with your sheet name
sheet = gc.open(SHEET_NAME).sheet1

def handle_message(msg):
    msg_lower = msg.lower()
    
    # HI
    if msg_lower == "hi":
        return (
            "👋 Welcome to Petroflexi energies limited loyal program! Here are the commands you can use:\n"
            "JOIN <Your Name> - set your name\n"
            "BUY <voucher> - earn points\n"
            "CHECK - see your points\n"
            "REDEEM - redeem points\n"
            "HISTORY - view your points history"
        )
    
    # JOIN
    elif msg_lower.startswith("join "):
        name = msg[5:].strip()
        # Add user to sheet if needed
        # sheet.append_row([name, 0])  # Example
        return f"Dear {name}, your registration was successful. Kindly type BUY followed by the voucher number given to you by the Staff to earn points"
    
    # BUY
    elif msg_lower.startswith("buy "):
        voucher = msg[4:].strip()
        # Lookup voucher logic in sheet
        # Example logic:
        user_name = "clement ataba"  # Replace with dynamic if needed
        if voucher == "INVALID":
            return f"Oops, sorry {user_name}, voucher is invalid. Kindly recheck and enter again."
        elif voucher == "USED":
            return f"Oops, sorry {user_name}, voucher is already used by another customer."
        else:
            return f"Dear {user_name}, congratulations 👏 points updated successfully. Kindly send CHECK to see your current point balance."
    
    # CHECK
    elif msg_lower == "check":
        points = 50  # Replace with dynamic sheet value
        return f"💎 Your total points: {points}"
    
    # REDEEM
    elif msg_lower == "redeem":
        current_points = 10  # Replace with dynamic sheet value
        if current_points >= 10:
            # Deduct points logic
            return "Congratulation you have 🎉 Redeemed 10 points for a reward!"
        else:
            return f"⚠ You need at least 10 points to redeem. Current: {current_points}"
    
    # HISTORY
    elif msg_lower == "history":
        # Fetch full history from sheet
        history = ["01-01-2025: 10 points", "02-01-2025: 5 points"]  # Replace with dynamic
        return "Your points history:\n" + "\n".join(history)
    
    else:
        return "⚠ Unknown command. Please type HI to see available commands."
