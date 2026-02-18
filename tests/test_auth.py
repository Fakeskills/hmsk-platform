from app.core.auth.security import hash_password, verify_password, create_access_token, decode_access_token, generate_refresh_token, hash_refresh_token
import uuid


def test_password_hash_roundtrip():
    plain = "MyS3cure!Pass"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_roundtrip():
    user_id, tenant_id = uuid.uuid4(), uuid.uuid4()
    token = create_access_token(user_id, tenant_id)
    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["tenant_id"] == str(tenant_id)


def test_refresh_token_hash():
    raw, hashed = generate_refresh_token()
    assert hashed == hash_refresh_token(raw)
