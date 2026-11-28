import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from optimus_dirs import skill_dirs  # noqa: E402


class TestOptimusDirs(unittest.TestCase):
    def test_env_override_wins(self):
        d = skill_dirs("s", env={"OPTIMUS_CACHE_DIR": "/x/cache"}, os_name="posix", home=Path("/h"))
        self.assertEqual(Path(d["cache_dir"]), Path("/x/cache").resolve() / "s")

    def test_relative_env_becomes_absolute(self):
        d = skill_dirs("s", env={"OPTIMUS_CACHE_DIR": "rel/cache"}, os_name="posix", home=Path("/h"))
        self.assertTrue(Path(d["cache_dir"]).is_absolute())
        self.assertEqual(Path(d["cache_dir"]), (Path.cwd() / "rel" / "cache" / "s").resolve())

    def test_path_with_spaces_preserved(self):
        d = skill_dirs("s", env={"OPTIMUS_CACHE_DIR": str(Path(tempfile.mkdtemp()) / "a b")},
                       os_name="posix", home=Path("/h"))
        self.assertIn("a b", d["cache_dir"])

    def test_windows_defaults(self):
        env = {"APPDATA": r"C:\U\R", "LOCALAPPDATA": r"C:\U\L"}
        d = skill_dirs("s", env=env, os_name="nt", home=Path(r"C:\U"))
        self.assertEqual(Path(d["config_dir"]), Path(r"C:\U\R") / "optimus" / "s")
        self.assertEqual(Path(d["cache_dir"]), Path(r"C:\U\L") / "optimus" / "cache" / "s")

    def test_posix_xdg_defaults(self):
        d = skill_dirs("s", env={}, os_name="posix", home=Path("/h"))
        self.assertEqual(Path(d["config_dir"]), Path("/h/.config/optimus/s"))
        self.assertEqual(Path(d["cache_dir"]), Path("/h/.cache/optimus/s"))

    def test_cli_prints_json_and_creates(self):
        tmp = Path(tempfile.mkdtemp()) / "a b"
        out = subprocess.run(
            [sys.executable, str(HERE / "optimus_dirs.py"), "s", "--create"],
            env={**os.environ, "OPTIMUS_CACHE_DIR": str(tmp), "OPTIMUS_CONFIG_DIR": str(tmp / "cfg")},
            capture_output=True, text=True, encoding="utf-8", check=True).stdout
        self.assertTrue(Path(json.loads(out)["cache_dir"]).is_dir())

    def test_feishu_token_cache_outside_skill_dir(self):
        sys.modules.setdefault("requests", types.ModuleType("requests"))
        sys.path.insert(0, str(HERE.parent))
        import fetch_feishu_doc
        tmp = tempfile.mkdtemp()
        p = fetch_feishu_doc.token_cache_file({"OPTIMUS_CACHE_DIR": tmp})
        self.assertEqual(p, Path(tmp).resolve() / "optimus-backend-api-connect" / ".feishu_token_cache.json")
        self.assertNotIn(str(HERE.parent.resolve()), str(p.resolve()))


if __name__ == "__main__":
    unittest.main()
