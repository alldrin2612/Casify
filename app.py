import os
import time
import json
import secrets
import re
from flask import Flask, request, redirect, render_template, session, flash, url_for, jsonify
from supabase import create_client, Client
from werkzeug.utils import secure_filename
from PIL import Image
from dotenv import load_dotenv
from datetime import datetime
import time
import requests


# Initialize Flask app
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Initialize Supabase client
load_dotenv()
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Helper functions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.template_filter('fromjson')
def fromjson(value):
    return json.loads(value)

def check_auth():
    if 'user_id' not in session:
        return False
    return True

def get_user_data():
    if not check_auth():
        return None
    
    user_id = session['user_id']
    response = supabase.table('users').select('*').eq('id', user_id).execute()
    
    if response.data:
        return response.data[0]
    return None

@app.template_filter('format_datetime')
def format_datetime(value):
    if isinstance(value, int):  # If stored as Unix timestamp
        return datetime.utcfromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(value, str):  # If stored as a string
        try:
            return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            return value  # Return as is if parsing fails
    return value



# Routes
@app.route('/')
def home():
    user = get_user_data()
    return render_template('index.html', user=user)

# Authentication routes
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        username = request.form['username']
        password = request.form['password']
        
        # Check if username already exists
        response = supabase.table('users').select('*').eq('username', username).execute()
        if response.data:
            flash('Username already exists')
            return render_template('login.html')
        
        # Hash the password
        hashed_password = hash_password(password)
        
        # Insert the new user
        user_data = {
            'first_name': first_name,
            'last_name': last_name,
            'username': username,
            'password': hashed_password
        }
        
        response = supabase.table('users').insert(user_data).execute()
        
        if response.data:
            # Login the user
            user_id = response.data[0]['id']
            session['user_id'] = user_id
            session['username'] = username
            flash('Signup successful!')
            return redirect(url_for('home'))
        else:
            flash('Signup failed')
            return render_template('login.html')
    
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Get user by username
        response = supabase.table('users').select('*').eq('username', username).execute()
        
        if response.data:
            stored_password = response.data[0]['password']
            # Verify the password against stored hash
            if verify_password(password, stored_password):
                user_id = response.data[0]['id']
                session['user_id'] = user_id
                session['username'] = username
                flash('Login successful!')
                return redirect(url_for('home'))
        
        flash('Invalid username or password')
        return render_template('login.html')
    
    return render_template('login.html')

def hash_password(password):
    # Using bcrypt for secure password hashing
    import bcrypt
    # Generate a salt and hash the password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password, hashed_password):
    # Verify a password against the stored hash
    import bcrypt
    try:
        # Ensure both the plaintext password and stored hash are properly encoded
        plain_password_bytes = plain_password.encode('utf-8')
        
        # If the hashed_password is already in bytes, use it directly; otherwise encode it
        if isinstance(hashed_password, bytes):
            hashed_password_bytes = hashed_password
        else:
            hashed_password_bytes = hashed_password.encode('utf-8')
            
        # Use bcrypt to verify the password
        return bcrypt.checkpw(plain_password_bytes, hashed_password_bytes)
    except Exception as e:
        print(f"Password verification error: {e}")
        return False

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully')
    return redirect(url_for('home'))

# Cart management routes
@app.route('/cart', methods=['GET'])
def view_cart():
    if not check_auth():
        flash('Please login to view your cart')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    response = supabase.table('cart').select('*').eq('user_id', user_id).execute()
    
    cart_items = response.data
    total_price = sum(item['price'] for item in cart_items)
    
    return render_template('cart.html', cart_items=cart_items, total_price=total_price, user=get_user_data())

@app.route('/cart/add', methods=['POST'])
def add_to_cart():
    try:
        if not check_auth():
            return jsonify({'success': False, 'message': 'Please login to add items to cart'}), 401
        
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID not found in session'}), 400
        
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': 'No data received'}), 400
        
        case_type = data.get('case_type')
        
        # Handle custom cases differently
        if case_type == 'custom':
            # For custom cases, we first need to create a custom case entry
            custom_case = {
                'user_id': user_id,
                'image_path': data.get('image_path'),
                'created_at': datetime.now().isoformat()
            }
            
            # Insert the custom case first
            custom_case_response = supabase.table('custom_cases').insert(custom_case).execute()
            
            if not custom_case_response.data:
                print(f"Supabase error: {custom_case_response.error}")
                return jsonify({'success': False, 'message': 'Failed to create custom case'}), 500
            
            # Get the ID of the newly created custom case
            custom_case_id = custom_case_response.data[0]['id']
            
            # Now we can add to cart with the custom case ID
            cart_item = {
                'user_id': user_id,
                'case_id': custom_case_id,  # Use the custom case ID
                'case_type': 'custom',
                'image_path': data.get('image_path'),
                'price': data.get('price', 30.00),
                'quantity': data.get('quantity', 1)
            }
        else:
            # For regular cases, use the provided case_id
            cart_item = {
                'user_id': user_id,
                'case_id': data.get('case_id'),
                'case_type': data.get('case_type'),
                'image_path': data.get('image_path'),
                'price': data.get('price', 25.99),
                'quantity': data.get('quantity', 1)
            }
        
        # Log the data for debugging
        print(f"Attempting to add to cart: {cart_item}")
        
        response = supabase.table('cart').insert(cart_item).execute()
        
        if response.data:
            # Return product info for a richer notification if available
            product_name = "Custom Case" if case_type == 'custom' else data.get('case_type', 'Item')
            return jsonify({
                'success': True, 
                'message': f"{product_name} added to cart",
                'item': cart_item
            })
        else:
            print(f"Supabase error: {response.error}")
            return jsonify({'success': False, 'message': 'Database error'}), 500
    except Exception as e:
        print(f"Error adding to cart: {str(e)}")
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@app.route('/cart/remove/<int:item_id>', methods=['POST'])
def remove_from_cart(item_id):
    if not check_auth():
        return jsonify({'success': False, 'message': 'Please login to remove items from cart'}), 401
    
    user_id = session['user_id']
    
    response = supabase.table('cart').delete().eq('id', item_id).eq('user_id', user_id).execute()
    
    if response.data:
        return jsonify({'success': True, 'message': 'Item removed from cart'})
    else:
        return jsonify({'success': False, 'message': 'Failed to remove item from cart'})

# Checkout route
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if not check_auth():
        flash('Please login to checkout')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    if request.method == 'POST':
        # Get cart items
        cart_response = supabase.table('cart').select('*').eq('user_id', user_id).execute()
        cart_items = cart_response.data
        
        if not cart_items:
            flash('Your cart is empty')
            return redirect(url_for('view_cart'))
        
        # Get form data
        shipping_address = request.form['shipping_address']
        payment_method = request.form['payment_method']
        
        # Calculate total price
        total_price = sum(item['price'] * item['quantity'] for item in cart_items)
        
        # Create order
        order_data = {
            'user_id': user_id,
            'shipping_address': shipping_address,
            'payment_method': payment_method,
            'total_price': total_price,
            'status': 'Delivered',
            'items': json.dumps(cart_items)
        }
        
        order_response = supabase.table('orders').insert(order_data).execute()
        
        if order_response.data:
            # Clear cart
            supabase.table('cart').delete().eq('user_id', user_id).execute()
            
            flash('Order placed successfully')
            return redirect(url_for('order_confirmation', order_id=order_response.data[0]['id']))
        else:
            flash('Failed to place order')
            return redirect(url_for('view_cart'))
    
    # Get cart items for display
    cart_response = supabase.table('cart').select('*').eq('user_id', user_id).execute()
    cart_items = cart_response.data
    total_price = sum(item['price'] * item['quantity'] for item in cart_items)
    
    return render_template('checkout.html', cart_items=cart_items, total_price=total_price, user=get_user_data())

@app.route('/order/confirmation/<int:order_id>')
def order_confirmation(order_id):
    if not check_auth():
        flash('Please login to view order confirmation')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    response = supabase.table('orders').select('*').eq('id', order_id).eq('user_id', user_id).execute()
    
    if response.data:
        order = response.data[0]
        return render_template('order_confirmation.html', order=order, user=get_user_data())
    else:
        flash('Order not found')
        return redirect(url_for('home'))

# Custom case creation routes
@app.route('/custom_case', methods=['GET'])
def custom_case():
    if not check_auth():
        flash('Please login to create custom cases')
        return redirect(url_for('login'))
    
    return render_template('custom_case.html', user=get_user_data())

def paste_image_on_case_template(image_path, user_id):
    try:
        # Open the uploaded image
        user_image = Image.open(image_path)
        
        # Open the case template
        case_template = Image.open('static/assets/templatewhite.png')
        
        # Resize the user image to completely fill the case template's dimensions
        user_image = user_image.resize(case_template.size)
        
        # Create a new image with the same size as the template
        final_image = Image.new('RGBA', case_template.size)
        
        # Paste the user image onto the final image
        final_image.paste(user_image, (0, 0))
        
        # Paste the template on top with alpha support
        final_image.paste(case_template, (0, 0), case_template)
        
        # Save the final image
        timestamp = int(time.time())
        output_filename = f"case_{user_id}_{timestamp}.png"
        
        # Save directly to static/uploads directory
        static_uploads_dir = os.path.join('static', 'uploads')
        if not os.path.exists(static_uploads_dir):
            os.makedirs(static_uploads_dir)
            
        output_path = os.path.join(static_uploads_dir, output_filename)
        final_image.save(output_path)
        
        # Return a URL path that will work with the frontend
        url_path = url_for('static', filename=f'uploads/{output_filename}')
        return url_path
    except Exception as e:
        print(f"Error in paste_image_on_case_template: {e}")
        raise

@app.route('/custom_case/upload', methods=['POST'])
def upload_image():
    if not check_auth():
        return jsonify({'success': False, 'message': 'Please login to upload images'}), 401
    
    user_id = session['user_id']
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file part'})
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file'})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        
        # Save uploaded file to a temporary location
        temp_dir = os.path.join('static', 'temp')
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            
        file_path = os.path.join(temp_dir, filename)
        file.save(file_path)
        
        try:
            # Process the image
            image_url = paste_image_on_case_template(file_path, user_id)
            
            # Clean up the original uploaded file
            os.remove(file_path)
            
            return jsonify({
                'success': True, 
                'message': 'Image uploaded successfully',
                'image_path': image_url
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error processing image: {str(e)}'
            }), 500
    
    return jsonify({'success': False, 'message': 'Invalid file type'})


@app.route('/generate_ai_image', methods=['POST'])
def generate_ai_image():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login to generate images'})
    
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        
        if not prompt:
            return jsonify({'success': False, 'message': 'No prompt provided'})
        
        # Hugging Face API endpoint for SDXL
        API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
        headers = {"Authorization": f"Bearer {os.environ.get('HF_API_KEY')}"}
        
        # Make request to Hugging Face API
        response = requests.post(
            API_URL,
            headers=headers,
            json={"inputs": prompt}
        )
        
        # Check if the request was successful
        if response.status_code != 200:
            return jsonify({'success': False, 'message': f'Failed to generate image: {response.text}'})
        
        # Save the image temporarily
        user_id = session['user_id']
        temp_dir = os.path.join('static', 'temp')
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            
        temp_path = os.path.join(temp_dir, f"temp_{user_id}_{int(time.time())}.png")
        
        with open(temp_path, 'wb') as f:
            f.write(response.content)
        
        # Use your existing function to paste onto template
        try:
            url_path = paste_image_on_case_template(temp_path, user_id)
            
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
            return jsonify({'success': True, 'image_path': url_path})
            
        except Exception as e:
            print(f"Error in paste_image_on_case_template: {e}")
            return jsonify({'success': False, 'message': f'Error processing image: {str(e)}'})
            
    except Exception as e:
        print(f"Error in generate_ai_image: {e}")
        return jsonify({'success': False, 'message': f'An error occurred while generating the image: {str(e)}'})

@app.route('/orders')
def order_history():
    if not check_auth():
        flash('Please login to view your orders')
        return redirect(url_for('login'))
    
    user_id = session.get('user_id')
    if not user_id:
        flash('Session expired. Please login again.')
        return redirect(url_for('login'))

    # Fetch orders from Supabase
    response = supabase.table('orders').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()
    
    # Ensure orders is a list
    orders = response.data if response.data else []

    # Parse 'items' field for each order
    for order in orders:
        # Rename the 'items' key to 'order_items' to avoid conflict with built-in method
        if 'items' in order:
            if isinstance(order['items'], str):
                try:
                    order['order_items'] = json.loads(order['items'])
                except json.JSONDecodeError:
                    order['order_items'] = []
            else:
                order['order_items'] = order['items']

    return render_template('orders.html', orders=orders, user=get_user_data())

@app.route('/cart/buy-again/<int:order_id>', methods=['POST'])
def buy_again(order_id):
    if not check_auth():
        return jsonify({'success': False, 'message': 'Please login to add items to cart'}), 401
    
    user_id = session['user_id']
    
    # Get the order
    order_response = supabase.table('orders').select('*').eq('id', order_id).eq('user_id', user_id).execute()
    
    if not order_response.data:
        return jsonify({'success': False, 'message': 'Order not found'}), 404
    
    order = order_response.data[0]
    
    # Parse order items
    if isinstance(order['items'], str):
        try:
            order_items = json.loads(order['items'])
        except json.JSONDecodeError:
            return jsonify({'success': False, 'message': 'Invalid order data'}), 500
    else:
        order_items = order['items']
    
    # Add each item back to cart
    items_added = 0
    for item in order_items:
        # For custom cases, we need to create a new custom case entry
        if item['case_type'] == 'custom':
            # Create a new custom case
            custom_case = {
                'user_id': user_id,
                'image_path': item['image_path'],
                'created_at': datetime.now().isoformat()
            }
            
            # Insert the custom case
            custom_case_response = supabase.table('custom_cases').insert(custom_case).execute()
            
            if not custom_case_response.data:
                continue
            
            # Get the ID of the newly created custom case
            custom_case_id = custom_case_response.data[0]['id']
            
            # Add to cart with the new custom case ID
            cart_item = {
                'user_id': user_id,
                'case_id': custom_case_id,
                'case_type': 'custom',
                'image_path': item['image_path'],
                'price': item['price'],
                'quantity': item['quantity']
            }
        else:
            # For regular cases, use the original case_id
            cart_item = {
                'user_id': user_id,
                'case_id': item['case_id'],
                'case_type': item['case_type'],
                'image_path': item.get('image_path'),
                'price': item['price'],
                'quantity': item['quantity']
            }
        
        # Add item to cart
        response = supabase.table('cart').insert(cart_item).execute()
        
        if response.data:
            items_added += 1
    
    if items_added > 0:
        return jsonify({
            'success': True, 
            'message': f'{items_added} items added to cart',
            'redirect': url_for('view_cart')
        })
    else:
        return jsonify({
            'success': False, 
            'message': 'Failed to add items to cart'
        }), 500

# Add this to your Flask app (app.py)

@app.route('/chat', methods=['POST'])
def chat():
    if not check_auth():
        return jsonify({'success': False, 'message': 'Please login to use the chat'}), 401
    
    try:
        data = request.get_json()
        user_message = data.get('message')
        
        if not user_message:
            return jsonify({'success': False, 'message': 'No message provided'})
        
        # Get user data for personalization
        user = get_user_data()
        user_name = user['first_name'] if user else "there"
        
        # Call Hugging Face API for the assistant response
        response = get_assistant_response(user_message, user_name)
        
        return jsonify({
            'success': True,
            'response': response
        })
    
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }), 500

def get_assistant_response(user_message, user_name):
    try:
        # Hugging Face API endpoint for an assistant model
        API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
        headers = {"Authorization": f"Bearer {os.environ.get('HF_API_KEY')}"}
        
        # Create a prompt in the format expected by the model - maintaining Casper but making him more versatile
        prompt = f"""
<s>[INST] You are Casper, a smart and creative AI assistant who provides concise, thoughtful responses.
Instructions:
1. Keep your responses brief and to the point (typically 1-3 sentences).
2. Be creative and thoughtful in your answers.
3. Don't use unnecessary preambles or closings.
4. Provide direct, helpful information with a friendly tone.
5. If you don't know something, briefly acknowledge it rather than making up information.
6. When appropriate, use clever analogies or examples to explain complex concepts simply.
7. Balance brevity with helpfulness - prioritize quality information over wordiness.

User query from {user_name}: {user_message} [/INST]
"""
        
        # Make request to Hugging Face API with parameters optimized for concise but smart responses
        response = requests.post(
            API_URL,
            headers=headers,
            json={
                "inputs": prompt, 
                "parameters": {
                    "max_new_tokens": 150,  # Limited for conciseness but enough for smart responses
                    "temperature": 0.65,    # Balanced for creativity while staying focused
                    "top_p": 0.88,          # Slightly diverse token selection
                    "do_sample": True,      # Enable sampling for natural responses
                    "repetition_penalty": 1.15  # Stronger discouragement of repetitive text
                }
            }
        )
        
        # Check if the request was successful
        if response.status_code != 200:
            print(f"Error from Hugging Face API: {response.text}")
            return "Connection issue. Try again soon."
        
        # Parse the response
        result = response.json()
        
        # Extract the model's response from the result
        assistant_response = ""
        if isinstance(result, list) and len(result) > 0:
            if isinstance(result[0], dict) and "generated_text" in result[0]:
                full_text = result[0]["generated_text"]
                inst_end = full_text.find("[/INST]")
                if inst_end != -1:
                    assistant_response = full_text[inst_end + 7:].strip()
                    if assistant_response.endswith("</s>"):
                        assistant_response = assistant_response[:-4].strip()
            else:
                full_text = str(result[0])
                inst_end = full_text.find("[/INST]")
                if inst_end != -1:
                    assistant_response = full_text[inst_end + 7:].strip()
                    if assistant_response.endswith("</s>"):
                        assistant_response = assistant_response[:-4].strip()
        elif isinstance(result, dict) and "generated_text" in result:
            full_text = result["generated_text"]
            inst_end = full_text.find("[/INST]")
            if inst_end != -1:
                assistant_response = full_text[inst_end + 7:].strip()
                if assistant_response.endswith("</s>"):
                    assistant_response = assistant_response[:-4].strip()
        
        # Post-process to ensure conciseness - trim lengthy responses
        if assistant_response:
            # Split into sentences and limit if necessary
            sentences = re.split(r'(?<=[.!?])\s+', assistant_response)
            if len(sentences) > 3:
                assistant_response = ' '.join(sentences[:3])
            
            # Remove any common closing phrases
            closing_phrases = [
                "hope that helps",
                "let me know if you need more information",
                "feel free to ask",
                "is there anything else"
            ]
            
            for phrase in closing_phrases:
                assistant_response = re.sub(f"(?i){phrase}.*", "", assistant_response)
                
            # Trim any extra whitespace
            assistant_response = assistant_response.strip()
            
            # If empty after cleaning, provide fallback
            if not assistant_response:
                return "I can help with that succinctly."
                
            return assistant_response
        
        return "I'll help with that briefly."
    
    except Exception as e:
        print(f"Error getting assistant response: {e}")
        return "Technical issue. Please try again."
    
if __name__ == '__main__':
    app.run(debug=True)