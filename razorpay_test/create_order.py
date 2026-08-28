import razorpay
import os
from dotenv import load_dotenv

# Load from the backend/.env file we created earlier
dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'backend', '.env')
load_dotenv(dotenv_path)

KEY_ID = os.getenv("RAZORPAY_KEY_ID")
KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

client = razorpay.Client(auth=(KEY_ID, KEY_SECRET))

data = {
    "amount": 10000,
    "currency": "INR",
    "receipt": "test_receipt_001"
}

order = client.order.create(data=data)

print("Order created!")
print(order)
print()
print("Order ID:", order["id"])