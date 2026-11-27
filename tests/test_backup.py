import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BackupRestoreTest(unittest.TestCase):
    def test_backup_and_restore_preserve_database(self):
        with tempfile.TemporaryDirectory(prefix="hs-backup-test-") as temp:
            data=Path(temp)/"data"; backup=Path(temp)/"backups"; restored=Path(temp)/"restored"
            env=dict(os.environ,DATA_DIR=str(data),BACKUP_DIR=str(backup))
            subprocess.run([sys.executable,"-c","from app.server import migrate,connect;migrate();c=connect();c.execute(\"INSERT INTO households(id,name) VALUES('home','Home')\");c.commit();c.close()"],cwd=ROOT,env=env,check=True)
            subprocess.run([sys.executable,"scripts/backup.py"],cwd=ROOT,env=env,check=True,capture_output=True,text=True)
            archive=next(backup.glob("*.tar.gz"))
            restore_env=dict(os.environ,DATA_DIR=str(restored))
            subprocess.run([sys.executable,"scripts/restore.py",str(archive)],cwd=ROOT,env=restore_env,check=True,capture_output=True,text=True)
            with sqlite3.connect(restored/"household.sqlite3") as con:
                self.assertEqual(con.execute("SELECT name FROM households WHERE id='home'").fetchone()[0],"Home")
                self.assertEqual(con.execute("PRAGMA integrity_check").fetchone()[0],"ok")


if __name__ == "__main__":
    unittest.main()
