
import os
import jwt
from jwt import PyJWKClient
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# JWKS URL for your Supabase project (RS256)
# Set this in your .env: SUPABASE_JWKS_URL=https://<project-ref>.supabase.co/.well-known/jwks.json
SUPABASE_JWKS_URL = os.getenv("SUPABASE_JWKS_URL")

# Cache the JWKS client to avoid fetching keys on every request
_jwks_client = None

def get_jwks_client():
    """Get or create a cached JWKS client."""
    global _jwks_client
    if _jwks_client is None:
        if not SUPABASE_JWKS_URL:
            raise ValueError("SUPABASE_JWKS_URL is not set")
        _jwks_client = PyJWKClient(SUPABASE_JWKS_URL)
    return _jwks_client

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Verifies the Supabase JWT token from the Authorization header.
    Uses RS256 with JWKS (new Supabase signing keys).
    Returns the decoded payload if valid.
    """
    token = credentials.credentials
    
    if not SUPABASE_JWKS_URL:
        print("⚠️  WARNING: SUPABASE_JWKS_URL is not set. Token verification will fail.")
        raise HTTPException(status_code=500, detail="Server misconfiguration: Missing JWKS URL")

    try:
        # Get the signing key from JWKS
        jwks_client = get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        # Verify and decode the token using ES256 (ECC P-256 key)
        payload = jwt.decode(
            token, 
            signing_key.key, 
            algorithms=["ES256"], 
            audience="authenticated",
            options={"verify_exp": True}
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidAudienceError:
        raise HTTPException(status_code=401, detail="Invalid audience")
    except jwt.InvalidTokenError as e:
        print(f"Invalid token error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print(f"Token validation error: {e}")
        raise HTTPException(status_code=401, detail="Could not validate credentials")
