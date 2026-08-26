import secrets
import string

otp = ''.join(secrets.choice(string.digits) for _ in range(4))

