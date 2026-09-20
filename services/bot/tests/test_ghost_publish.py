import base64,json,unittest
from ghost_publish import token
class JwtTests(unittest.TestCase):
    def test_claims(self):
        encoded=token("test:"+"ab"*32)
        h,p,s=encoded.split(".")
        decode=lambda x:json.loads(base64.urlsafe_b64decode(x+"="*(-len(x)%4)))
        self.assertEqual(decode(h)["kid"],"test")
        self.assertEqual(decode(p)["aud"],"/admin/")
        self.assertEqual(len(base64.urlsafe_b64decode(s+"="*(-len(s)%4))),32)
if __name__=="__main__":unittest.main()
