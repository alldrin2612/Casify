from flask import Flask, request, jsonify, session
from flask_cors import CORS
import supabase

# Initialize Flask App
app = Flask(__name__)
app.secret_key = "supersecretkey"  # Change this to a secure key
CORS(app)

# Initialize Supabase
SUPABASE_URL = "your-supabase-url"
SUPABASE_KEY = "your-supabase-key"
supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)

# Add to Cart API
@app.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    if 'user' not in session:
        return jsonify({"error": "User not logged in"}), 401
    
    data = request.json
    user_id = session['user']
    case_id = data.get('case_id')
    case_name = data.get('case_name')
    price = data.get('price')
    
    response = supabase_client.table('cart').insert({
        "user_id": user_id,
        "case_id": case_id,
        "case_name": case_name,
        "price": price
    }).execute()
    
    return jsonify({"message": "Item added to cart", "data": response})

# View Cart API
@app.route('/cart', methods=['GET'])
def view_cart():
    if 'user' not in session:
        return jsonify({"error": "User not logged in"}), 401
    
    user_id = session['user']
    response = supabase_client.table('cart').select('*').eq('user_id', user_id).execute()
    return jsonify(response['data'])

# View Past Orders API
@app.route('/orders', methods=['GET'])
def view_orders():
    if 'user' not in session:
        return jsonify({"error": "User not logged in"}), 401
    
    user_id = session['user']
    response = supabase_client.table('orders').select('*').eq('user_id', user_id).execute()
    return jsonify(response['data'])

if __name__ == '__main__':
    app.run(debug=True)