from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from cryptography.hazmat.primitives import serialization

def validator(token, pub_key, expected_iss, expected_aud, required_scope):
    try:
        claims = jwt.decode(token, pub_key, algorithms=["RS256"], audience=expected_aud, issuer=expected_iss)
    except jwt.exceptions.InvalidTokenError:
        return "authentication error", 401

    token_scope = claims.get("scope", "").split()
    if required_scope not in token_scope:
        return "authorization error", 403

    return "Status OK", 200


expected_iss = "https://my-test-issuer.local"
expected_aud = "fal-image-api"
required_scope = "image:generate"

# The first step is to retrieve the public key from the .pem file
with open("public_key.pem", "rb") as f:
    pub_key = serialization.load_pem_public_key(
        f.read()
    )
    
# Let's create instance of am app first to start receiving any requests
app = FastAPI()

# FastAPI allows you to extract the Bearer token using this helper 
security_scheme = HTTPBearer()

# Set up an endpoint to get requests from the client and retrieve the access token from the url
@app.get("/generate")
def generate(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)):

    # Read the token from the URL
    received_token = credentials.credentials
    error_msg, error_code = validator(received_token, pub_key, expected_iss, expected_aud, required_scope)

    if error_code == 401:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail= error_msg
        )
    elif error_code == 403:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_msg
        )

    return {
        "status": "SUCCESS",
        "message": "Token validation successful!"
    }