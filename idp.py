# This is my attempt at constructing a resurce server that performs validation of JWT access tokens and responds with a status code
# Happens in 4 parts: payload, header, hashing and signing, outputs the jwt token in the form of header.payload.signature
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from datetime import datetime
from datetime import timezone
from datetime import timedelta
import jwt

def generate_rsa_key_pair(k_size):
    # Used to generate the private an dpublic keys for the RSA256 algorithm that will sign the token for us
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=k_size
    )

    # Now we derive public key from private key 
    public_key = private_key.public_key()

    return private_key,public_key


def mint_access_token(payload,header,pri_key):
    # The minter generates the signature and then builds the token for us - all done using jwt.encode!
    token = jwt.encode(payload=payload, key=pri_key, algorithm="RS256",headers = header)

    return token


if __name__ == "__main__":

    key_size = 2048
    pri_key, pub_key = generate_rsa_key_pair(key_size)

    # Now that we have a key value pair, we move on with the minting process

    now = datetime.now(tz=timezone.utc)
    payload = {
    "iss": "https://my-test-issuer.local",
    "aud": "fal-image-api",
    "sub": "agent-74",
    "scope": "image:generate",
    "iat": now,
    "exp": now + timedelta(seconds=3600)
    }

    header = {
        "typ":"JWT",
        "alg":"RS256"
    }

    token = mint_access_token(payload,header,pri_key)
    with open("token.txt", "w") as f:
        f.write(token)

    public_bytes = pub_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo 
    )

    with open("public_key.pem", "wb") as f:
        f.write(public_bytes)


