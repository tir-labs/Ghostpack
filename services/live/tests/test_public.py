import os,tempfile,unittest
from pathlib import Path
from fastapi import HTTPException
import store
from public import published_event
class PublicTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        store.DB=str(Path(self.temp.name)/"live.sqlite3")
        store.init()
    def tearDown(self):self.temp.cleanup()
    def test_no_unpublished_leak(self):
        e=store.event("Test")
        pending=store.submit(e["id"],"reporter","Private tip",[{"private_path":"/secret"}])
        with self.assertRaises(HTTPException):published_event(e["id"])
        with store.connect() as c:
            c.execute("UPDATE events SET ghost_post_id=? WHERE id=?",("ghost-post",e["id"]))
            c.commit()
        self.assertEqual(published_event(e["id"])["updates"],[])
        store.decide(pending["id"],1,"editor","approve")
        self.assertEqual(published_event(e["id"])["updates"],[])
        store.published(pending["id"],"https://example.org/post/")
        result=published_event(e["id"])
        self.assertEqual(len(result["updates"]),1)
        self.assertNotIn("media",result["updates"][0])
if __name__=="__main__":unittest.main()
