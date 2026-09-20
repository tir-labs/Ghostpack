import os,tempfile,unittest
from pathlib import Path
import store
class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        store.DB=str(Path(self.temp.name)/"live.sqlite3")
        store.init()
    def tearDown(self): self.temp.cleanup()
    def test_approval_and_archive(self):
        e=store.event("Breaking coverage","123456789012345678")
        u=store.submit(e["id"],"reporter","First report")
        store.decide(u["id"],1,"editor","hold","Verify attribution")
        v=store.revise(u["id"],"reporter","Verified report")
        self.assertEqual(v["version"],2)
        store.decide(u["id"],2,"editor","approve")
        with self.assertRaises(ValueError): store.decide(u["id"],2,"editor","approve")
        store.published(u["id"],"https://ghost.example.com/report/")
        result=store.end(e["id"])
        self.assertEqual(result["updates"][0]["state"],"published")
        self.assertEqual(len(result["updates"][0]["decisions"]),2)
if __name__=="__main__": unittest.main()
