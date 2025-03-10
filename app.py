from flask import Flask, request, jsonify, session, render_template
from flask_cors import CORS
import supabase
from PIL import Image
import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Flask App
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "supersecretkey"  # Change this to a secure key
CORS(app)

# Initialize Supabase
supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)
# Check if variables are loaded (for debugging)
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL or Key is missing. Check your .env file.")


# Home Page Route
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/index')
def index():
    return render_template('index.html')

# Render Pages
@app.route('/cart')
def cart_page():
    return render_template('cart.html')

@app.route('/create')
def create_page():
    return render_template('create.html')

@app.route('/orders')
def orders_page():
    return render_template('orders.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/checkout')
def checkout_page():
    return render_template('checkout.html')

if __name__ == '__main__':
    app.run(debug=True)