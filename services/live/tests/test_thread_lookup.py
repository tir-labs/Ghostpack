import tempfile,unittest
from pathlib import Path
import store
class ThreadLookupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        store.DB=str(Path(self.tmp.name)/"db.sqlite3")
        store.init()
    def tearDown(self): self.tmp.cleanup()
    def test_lookup_survives_process_state(self):
        e=store.event("Test","123456789012345678")
        self.assertEqual(store.by_thread("123456789012345678")["id"],e["id"])
        store.end(e["id"])
        self.assertIsNone(store.by_thread("123456789012345678"))
if __name__=="__main__":unittest.main()
