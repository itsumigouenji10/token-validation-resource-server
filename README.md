# Token Validation Resource Server

A small, self-contained OAuth 2.0 style system that mints a signed JWT access token, presents it over HTTP, and validates it on a protected API, returning the correct 401 / 403 / 200 responses. I built this to understand token validation from first principles rather than from a framework doing it invisibly for me.

It is deliberately split into three separate programs, because that mirrors how the real world actually works: the authority that issues tokens, the client that carries one, and the API that checks it are three different parties. Forcing them into one file would hide the exact separation the whole thing is meant to demonstrate.

## The three actors

**`idp.py`: the Authorization Server (the minter).**
Plays the role a real identity provider like Okta or PingOne would. It generates an RSA key pair, mints an RS256-signed access token with the standard claims (`iss`, `aud`, `sub`, `scope`, `iat`, `exp`), and publishes its outputs to disk: the token to `token.txt`, and its public key to `public_key.pem`. It signs with the private key; it never shares the private key.

**`server.py`: the Resource Server (the protected API).**
A FastAPI service. It does not mint tokens. It loads the public key at startup and, on each request, validates whatever token arrives. The issuer, audience, and required scope it checks against are the server's own configuration, set in advance. The client never gets to supply those; it only supplies the token. That separation is the point: the server decides the rules independently of whatever the caller sends.

**`client.py`: the Client (the caller).**
Reads the token from `token.txt` and presents it to the server in an `Authorization: Bearer <token>` header, then prints the response. It neither mints nor validates; it just carries the token, the way an app or agent would.

## How a token is validated

The server runs the checks in a deliberate order, authentication before authorization:

1. **Signature**: was this token really signed by the issuer, and untampered? (verified with the public key)
2. **Issuer (`iss`)**: is it from the issuer this server trusts?
3. **Audience (`aud`)**: is it actually meant for this server?
4. **Expiry (`exp`)**: is it still valid, not expired?
5. **Scope**: does the caller have the permission this endpoint requires?

The order matters. Everything that makes the token itself untrustworthy (steps 1–4) is an **authentication** failure and returns **401**. Only once a token is proven trustworthy does the server ask whether the caller is **authorized**, and a valid token missing the required scope returns **403**. You cannot meaningfully judge a token's permissions until you have confirmed the token telling you those permissions is genuine.

In the code, `jwt.decode()` performs steps 1–4 in a single call (signature, issuer, audience, and expiry) and raises an error if any fail; the scope check (step 5) runs only after that succeeds.

## The three outcomes

| Situation | What the server does | Response |
|---|---|---|
| Valid token, correct scope | signature, iss, aud, exp all pass; scope present | **200** `{"status": "SUCCESS", "message": "Token validation successful!"}` |
| Tampered / expired / wrong issuer or audience | `jwt.decode()` raises `InvalidTokenError` | **401** authentication error |
| Valid token, but missing the required scope | passes authentication, fails the scope check | **403** authorization error |

The 401 case is worth calling out, because it is a real security property rather than just an error path. If someone intercepts a token and changes any claim inside it (say, edits the scope to grant themselves more access), the signature no longer matches, because they do not have the private key to re-sign it. The server's signature check catches exactly that tampering and rejects it with a 401. That is the whole reason tokens are signed: not to keep their contents secret (they are readable by anyone), but to make any change to them detectable.

## Running it

You need three things in sync, and this tripped me up the first time (see the notes below), so the order matters:

```bash
# 1. Mint a fresh token and publish the public key
python idp.py

# 2. Start the resource server (loads the public key at startup)
#    Run with `python -m uvicorn` because uvicorn may not be on PATH.
python -m uvicorn server:app --reload

# 3. In a second terminal, send the token as a client
python client.py
```

A successful run prints:

```
Server Status Code: 200
Server Response: {'status': 'SUCCESS', 'message': 'Token validation successful!'}
```

## Things I learned building this (the honest version)

- **The three-actor split had to be real.** For a while it felt like everything "should" fit in one file, and I kept trying to force the client and the minter into the server. It was only once I accepted that the client and server are genuinely separate programs that talk over HTTP, not functions in one file, that the design made sense. My instinct that it did not belong in one file was right; I just did not trust it at first.

- **Why serialization actually matters.** Early on I skipped serializing the keys because everything was in memory and it worked fine. The moment the minter and the server became separate programs, the public key had to physically leave one program and reach the other, so it had to be serialized to PEM and written to a file. That is exactly what a real IdP's JWKS endpoint does: publish its public key so any resource server can fetch and verify with it.

- **Text mode vs binary mode.** The token is a string, so it is written and read as text (`"w"` / `"r"`). The PEM public key is bytes, so it uses binary mode (`"wb"` / `"rb"`). Mixing these up is a subtle source of bugs, I hit exactly this when `client.py` first read the token in binary mode and the token got formatted into the header as `b'...'`; switching it to text mode (`"r"`) fixed it.

- **`if __name__ == "__main__"` is context-dependent.** In `idp.py` it is the right tool, it guards the run-once minting code. In `server.py` it would have been the wrong tool: uvicorn *imports* the file to find the `app` object, and anything guarded by that block never runs on import. Same line, opposite answer, depending on whether the file is run directly or imported.

- **The bug that actually got me: everything has to be in sync.** My first end-to-end run returned a 401 on a token I was sure was valid. The cause was two stale-state problems at once: the token had expired (it only lasts an hour), *and* the server had loaded an older public key into memory at startup, from before I had re-run the minter. The fix was to re-run `idp.py`, restart the server so it loads the new key, and run the client immediately. The lesson that stuck: a running server holds its key in memory, so regenerating keys means restarting the server, and the token, the public key, and the running server all have to come from the same generation.

## What's next

- Swap the local minter for real token issuance from **Okta / PingOne**, and point the validator at their **JWKS endpoint** to fetch the public key instead of reading a local file. That turns this from a self-contained demo into a real IdP integration.
- Add a small script to demonstrate the 401 (tampered token) and 403 (wrong scope) paths automatically.

## A note on the code

The code here is my own, written and debugged as I worked through the concepts from first principles. I have kept the comments explaining not just what each part does but why it is there, because understanding the reasoning was the whole point of building this rather than letting a framework hide it.
