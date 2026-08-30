import requests

# Let's take the minted token from the file token.txt - read it basically - and send it 
# rescource server api that we have

with open("token.txt", "r") as f:
    token = f.read()

# Define the URL base so we can attach the bearer tokent to it and make requests to the endpoint we set up
URL = "http://127.0.0.1:8000/generate"

# Let's define a header and attach it to the url
header = {
    "Authorization":f"Bearer {token}"
}

# Send a request to the local FastAPI server 
response = requests.get(url=URL, headers=header)

print("Server Status Code:", response.status_code)
print("Server Response:", response.json())