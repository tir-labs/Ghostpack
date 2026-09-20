import base64
import json
import unittest
from ghost import admin_token

class TokenTests(unittest.TestCase):
    def test_admin_jwt_fields(self):
        token = admin_token("test:" + "ab" * 32)
        header, payload, signature = token.split(".")
        decode = lambda s: json.loads(base64.urlsafe_b64decode(s + "=" * (-len(s) % 4)))
        self.assertEqual(decode(header)["kid"], "test")
        self.assertEqual(decode(payload)["aud"], "/admin/")
        self.assertEqual(len(base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))), 32)

if __name__ == "__main__":
    unittest.main()
