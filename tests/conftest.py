# tests/conftest.py
import os
import jwt
import jwt.exceptions

# Patch base64url_decode if missing.
try:
    from jwt.utils import base64url_decode
except ImportError:
    import base64
    def base64url_decode(input):
        if isinstance(input, str):
            input = input.encode("utf-8")
        rem = len(input) % 4
        if rem:
            input += b'=' * (4 - rem)
        return base64.urlsafe_b64decode(input)
    jwt.utils.base64url_decode = base64url_decode

# Patch base64url_encode if missing.
try:
    from jwt.utils import base64url_encode
except ImportError:
    import base64
    def base64url_encode(input):
        if isinstance(input, str):
            input = input.encode("utf-8")
        return base64.urlsafe_b64encode(input).rstrip(b'=')
    jwt.utils.base64url_encode = base64url_encode

# Patch der_to_raw_signature if missing.
try:
    from jwt.utils import der_to_raw_signature
except ImportError:
    def der_to_raw_signature(der_sig, key_length):
        # Dummy implementation for testing purposes.
        return der_sig
    jwt.utils.der_to_raw_signature = der_to_raw_signature

# Patch force_bytes if missing.
try:
    from jwt.utils import force_bytes
except ImportError:
    def force_bytes(value, encoding="utf-8", errors="strict"):
        if isinstance(value, str):
            return value.encode(encoding, errors)
        return value
    jwt.utils.force_bytes = force_bytes

# Patch from_base64url_uint if missing.
try:
    from jwt.utils import from_base64url_uint
except ImportError:
    def from_base64url_uint(val):
        decoded = jwt.utils.base64url_decode(val)
        return int.from_bytes(decoded, 'big')
    jwt.utils.from_base64url_uint = from_base64url_uint

# Patch is_pem_format if missing.
try:
    from jwt.utils import is_pem_format
except ImportError:
    def is_pem_format(value):
        if isinstance(value, bytes):
            value = value.decode("utf-8", "ignore")
        return value.startswith("-----BEGIN")
    jwt.utils.is_pem_format = is_pem_format

# Patch is_ssh_key if missing.
try:
    from jwt.utils import is_ssh_key
except ImportError:
    def is_ssh_key(value):
        # Dummy implementation: always return False for tests.
        return False
    jwt.utils.is_ssh_key = is_ssh_key

if not hasattr(jwt.exceptions, "InvalidKeyError"):
    jwt.exceptions.InvalidKeyError = Exception

# Set required environment variables for tests.
os.environ['COGNITO_USER_POOL_ID'] = 'dummy_pool'
os.environ['COGNITO_APP_CLIENT_ID'] = 'dummy_client'
os.environ['CONNECTIONS_TABLE'] = 'dummy_table'
os.environ['AWS_REGION'] = 'us-east-1'
os.environ['COGNITO_REGION'] = 'us-east-1'