const API_BASE_URL = "http://127.0.0.1:5000";

// Signup Function
async function signup() {
    const username = document.getElementById("signup-username").value;
    const password = document.getElementById("signup-password").value;
    const firstName = document.getElementById("signup-firstname").value;
    const lastName = document.getElementById("signup-lastname").value;

    const response = await fetch(`${API_BASE_URL}/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, first_name: firstName, last_name: lastName })
    });

    const data = await response.json();
    alert(data.message || data.error);
}

// Login Function
async function login() {
    const username = document.getElementById("login-username").value;
    const password = document.getElementById("login-password").value;

    const response = await fetch(`${API_BASE_URL}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
    });

    const data = await response.json();
    if (data.user_id) {
        sessionStorage.setItem("user_id", data.user_id);
        alert("Login successful!");
        window.location.href = "index.html";
    } else {
        alert("Login failed!" + data.error);
    }
}

// Add to Cart
async function addToCart(caseId, caseName, price) {
    const userId = sessionStorage.getItem("user_id");
    if (!userId) {
        alert("Please login first!");
        return;
    }
    
    await fetch(`${API_BASE_URL}/add-to-cart`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ case_id: caseId, case_name: caseName, price })
    });
    alert("Item added to cart!");
}

// View Cart
async function loadCart() {
    const response = await fetch(`${API_BASE_URL}/cart`);
    const cartItems = await response.json();
    
    let cartHTML = "";
    cartItems.forEach(item => {
        cartHTML += `<div>${item.case_name} - $${item.price} <button onclick='removeFromCart("${item.case_id}")'>Remove</button></div>`;
    });
    document.getElementById("cart-container").innerHTML = cartHTML || "Your cart is empty";
}

// Remove from Cart
async function removeFromCart(caseId) {
    await fetch(`${API_BASE_URL}/remove-from-cart`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ case_id: caseId })
    });
    alert("Item removed from cart!");
    loadCart();
}

// Checkout
async function checkout() {
    await fetch(`${API_BASE_URL}/checkout`, { method: "POST" });
    alert("Order placed successfully!");
    loadCart();
}

// Upload Image for Custom Case
async function uploadImage() {
    const fileInput = document.getElementById("image-upload");
    const formData = new FormData();
    formData.append("image", fileInput.files[0]);

    const response = await fetch(`${API_BASE_URL}/upload-image`, {
        method: "POST",
        body: formData
    });
    
    const data = await response.json();
    document.getElementById("custom-case-preview").src = data.image_path;
}

// Generate AI Image for Custom Case
async function generateAIImage() {
    const description = document.getElementById("ai-description").value;
    const response = await fetch(`${API_BASE_URL}/generate-ai-image`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description })
    });
    
    const data = await response.json();
    document.getElementById("ai-case-preview").src = data.image_path;
}
