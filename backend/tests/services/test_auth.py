import pytest
from app.services.auth import verify_password, get_password_hash, create_access_token

def test_password_hashing():
    password = "super_secure_password123"
    hashed = get_password_hash(password)
    
    # Check that it hashes
    assert hashed != password
    # Check that verification succeeds on the right password
    assert verify_password(password, hashed) is True
    # Check that verification fails on the wrong password
    assert verify_password("wrongpassword", hashed) is False

def test_create_access_token():
    data = {"sub": "test@example.com"}
    token = create_access_token(data)
    
    # Token should be a string and contain standard JWT segments (header.payload.signature)
    assert isinstance(token, str)
    assert len(token.split(".")) == 3
