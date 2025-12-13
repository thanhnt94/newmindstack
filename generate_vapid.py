from pywebpush import WebPusher

# Generate VAPID keys
private_key = WebPusher.gen_private_key()
vapid_keys = WebPusher.gen_vapid_keys(private_key)

print(f"VAPID_PRIVATE_KEY={vapid_keys['private_key']}")
print(f"VAPID_PUBLIC_KEY={vapid_keys['public_key']}")
print(f"VAPID_EMAIL=mailto:admin@mindstack.app")

# Instruction: Add these to your .env file
