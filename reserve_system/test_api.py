import requests

base_url = "http://localhost:5000"

# Assuming user is logged in via cookie. We need a session cookie.
# First, let's login to get a session cookie.
session = requests.Session()
login_data = {"studentId": "12245607", "password": "password"} # Try some default password or check DB
# Actually, we can just hit the API if it's running. Is the server running?
try:
    res = session.get(f"{base_url}/api/machines")
    print("Machines fetched.")
except Exception as e:
    print(f"Server not running: {e}")
