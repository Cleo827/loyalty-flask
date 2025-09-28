from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from verify import handle_message

app = Flask(__name__)

@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    incoming_msg = request.values.get("Body", "").strip()
    resp = MessagingResponse()
    msg = resp.message()

    response_text = handle_message(incoming_msg)
    msg.body(response_text)
    
    return str(resp)

if __name__ == "__main__":
    app.run(debug=True)
