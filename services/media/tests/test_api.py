import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import app

class MediaValidationTests(unittest.TestCase):
    def test_auth_missing(self):
        from fastapi import HTTPException
        with patch.object(app,"TOKEN","test-token"):
            with self.assertRaises(HTTPException) as err:
                app.authorize(None)
            self.assertEqual(err.exception.status_code,401)
    def test_auth_valid(self):
        with patch.object(app,"TOKEN","test-token"):
            app.authorize("Bearer test-token")
    def test_health(self):
        self.assertEqual(app.health(),{"ok":True})

if __name__=="__main__":
    unittest.main()
