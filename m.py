import bcrypt

password = 'your_password'
hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
print(hashed_password)

