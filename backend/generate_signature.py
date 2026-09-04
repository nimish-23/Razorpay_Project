import os
import hmac
import hashlib
from dotenv import load_dotenv

load_dotenv()

body = b'{"event":"test"}'
secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")

print("SECRET FOUND:", bool(secret))

signature = hmac.new(
    secret.encode(),
    body,
    hashlib.sha256
).hexdigest()

print("SIGNATURE:", signature)
