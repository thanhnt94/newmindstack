
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
import base64

def to_base64_url(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

# Generate EC Key Pair (Prime256v1 is P-256)
private_key = ec.generate_private_key(ec.SECP256R1())
public_key = private_key.public_key()

# Serialize Private Key (Integer format is tricky, usually DER PKCS8 is fine, 
# but for VAPID raw scalar is often used. 
# PyWebPush accepts PEM path too, but for .env we often want base64.
# Let's simple use base64 url encoded DER for generic storage)

private_val = private_key.private_numbers().private_value
# 32 bytes for P-256
private_bytes = private_val.to_bytes(32, byteorder='big')
private_b64 = to_base64_url(private_bytes)

# Serialize Public Key (Uncompressed point format: 0x04 + x + y)
# 65 bytes
public_bytes = public_key.public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint
)
public_b64 = to_base64_url(public_bytes)

with open('mindstack_app/vapid_keys.txt', 'w') as f:
    f.write(f"VAPID_PRIVATE_KEY={private_b64}\n")
    f.write(f"VAPID_PUBLIC_KEY={public_b64}\n")
    f.write("VAPID_EMAIL=mailto:admin@mindstack.app\n")

print("Keys saved to mindstack_app/vapid_keys.txt")
