import hashlib

password = 'your_password'
hashed_password = hashlib.sha256(password.encode()).hexdigest()
print(hashed_password)

