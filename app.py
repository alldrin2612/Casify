from flask import Flask, request, jsonify, session
from flask_cors import CORS
import supabase
from PIL import Image

# Initialize Flask App
app = Flask(__name__)
app.secret_key = "supersecretkey"  # Change this to a secure key
CORS(app)

# Initialize Supabase
SUPABASE_URL = "your-supabase-url"
SUPABASE_KEY = "your-supabase-key"
supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)

# User Signup API
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    
    response = supabase_client.auth.sign_up({
        "email": username,
        "password": password
    })
    
    if 'error' in response:
        return jsonify({"error": response['error']}), 400
    
    user_id = response['user']['id']
    supabase_client.table('users').insert({
        "id": user_id,
        "first_name": first_name,
        "last_name": last_name,
        "username": username
    }).execute()
    
    return jsonify({"message": "User registered successfully!"})

# User Login API
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    response = supabase_client.auth.sign_in_with_password({
        "email": username,
        "password": password
    })
    
    if 'error' in response:
        return jsonify({"error": "Invalid credentials"}), 401
    
    session['user'] = response['user']['id']
    return jsonify({"message": "Login successful!", "user_id": response['user']['id']})

# User Logout API
@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({"message": "Logout successful!"})

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

# Remove from Cart API
@app.route('/remove-from-cart', methods=['POST'])
def remove_from_cart():
    if 'user' not in session:
        return jsonify({"error": "User not logged in"}), 401
    
    data = request.json
    user_id = session['user']
    case_id = data.get('case_id')
    
    response = supabase_client.table('cart').delete().eq('user_id', user_id).eq('case_id', case_id).execute()
    return jsonify({"message": "Item removed from cart", "data": response})

# Get Total Price API
@app.route('/cart-total', methods=['GET'])
def cart_total():
    if 'user' not in session:
        return jsonify({"error": "User not logged in"}), 401
    
    user_id = session['user']
    response = supabase_client.table('cart').select('price').eq('user_id', user_id).execute()
    total_price = sum(item['price'] for item in response['data'])
    
    return jsonify({"total": total_price})

# View Past Orders API
@app.route('/orders', methods=['GET'])
def view_orders():
    if 'user' not in session:
        return jsonify({"error": "User not logged in"}), 401
    
    user_id = session['user']
    response = supabase_client.table('orders').select('*').eq('user_id', user_id).execute()
    return jsonify(response['data'])

# Place Order (Checkout) API
@app.route('/checkout', methods=['POST'])
def checkout():
    if 'user' not in session:
        return jsonify({"error": "User not logged in"}), 401
    
    user_id = session['user']
    cart_items = supabase_client.table('cart').select('*').eq('user_id', user_id).execute()['data']
    
    if not cart_items:
        return jsonify({"error": "Cart is empty"}), 400
    
    for item in cart_items:
        supabase_client.table('orders').insert({
            "user_id": user_id,
            "case_id": item.get('case_id'),
            "case_name": item.get('case_name'),
            "price": item.get('price')
        }).execute()
    
    supabase_client.table('cart').delete().eq('user_id', user_id).execute()
    return jsonify({"message": "Order placed successfully!"})

# Upload Custom Image API
@app.route('/upload-image', methods=['POST'])
def upload_image():
    if 'user' not in session:
        return jsonify({"error": "User not logged in"}), 401
    
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400
    
    image = request.files['image']
    base_template = Image.open("assets/templatewhite.png")
    uploaded_image = Image.open(image).resize((300, 500))
    base_template.paste(uploaded_image, (100, 100), uploaded_image)
    final_path = "assets/generated_case.png"
    base_template.save(final_path)
    
    return jsonify({"message": "Image uploaded successfully!", "image_path": final_path})

# AI Image Generation Placeholder API
@app.route('/generate-ai-image', methods=['POST'])
def generate_ai_image():
    if 'user' not in session:
        return jsonify({"error": "User not logged in"}), 401
    
    data = request.json
    description = data.get("description")
    
    base_template = Image.open("assets/templatewhite.png")
    ai_generated_image = Image.new("RGBA", (300, 500), (255, 0, 0, 128))
    base_template.paste(ai_generated_image, (100, 100), ai_generated_image)
    final_path = "assets/generated_ai_case.png"
    base_template.save(final_path)
    
    return jsonify({"message": "AI Image Generated!", "image_path": final_path})

# Add Custom Case to Cart API
@app.route('/add-custom-case-to-cart', methods=['POST'])
def add_custom_case_to_cart():
    if 'user' not in session:
        return jsonify({"error": "User not logged in"}), 401
    
    data = request.json
    user_id = session['user']
    image_path = data.get('image_path')
    price = 30.00
    
    response = supabase_client.table('cart').insert({
        "user_id": user_id,
        "case_name": "Custom Case",
        "image_path": image_path,
        "price": price
    }).execute()
    
    return jsonify({"message": "Custom case added to cart", "data": response})



if __name__ == '__main__':
    app.run(debug=True)