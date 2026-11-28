"""test_bundled_helper_copies.py - 验证 optimus_dirs.py 的两份副本字节级一致。"""

import pathlib
import unittest


class TestBundledHelperCopies(unittest.TestCase):
    def test_optimus_dirs_copies_identical(self):
        root = pathlib.Path(__file__).resolve().parent.parent
        a = root / "plugins/optimus-backend/skills/optimus-backend-api-connect/scripts/optimus_dirs.py"
        b = root / "plugins/optimus-devops/skills/jenkins-build/scripts/optimus_dirs.py"
        self.assertTrue(a.exists(), f"源文件不存在: {a}")
        self.assertTrue(b.exists(), f"副本文件不存在: {b}")
        self.assertEqual(a.read_bytes(), b.read_bytes(),
                         "两份 optimus_dirs.py 副本内容不一致，请同步修改")


if __name__ == "__main__":
    unittest.main()
