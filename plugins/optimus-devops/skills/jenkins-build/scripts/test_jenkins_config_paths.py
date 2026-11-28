"""test_jenkins_config_paths.py - jenkins_config_paths 单元测试。"""

import pathlib
import sys
import tempfile
import unittest

# scripts/ 目录本文件所在，确保能导入同目录模块
_SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS_DIR))

from jenkins_config_paths import (  # noqa: E402
    PROJECT_DIR_ENV,
    config_search_paths,
    find_config,
)


class TestJenkinsConfigPaths(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.home = self.tmp / "home"
        self.proj = self.tmp / "proj"
        self.cfg = self.tmp / "cfg"
        for d in (self.home, self.proj, self.cfg):
            d.mkdir()
        # env 只含 OPTIMUS_CONFIG_DIR，使 skill_dirs 落到 cfg/jenkins-build/
        self.env = {"OPTIMUS_CONFIG_DIR": str(self.cfg)}

    def test_project_dir_env_beats_cwd(self):
        # 配置只放在 proj/；cwd=tmp（模拟 skill 目录）；env 含 JENKINS_BUILD_PROJECT_DIR=proj → 命中 proj/
        config_file = self.proj / "jenkins-config.yaml"
        config_file.write_text("jenkins: {}")
        env = {**self.env, PROJECT_DIR_ENV: str(self.proj)}
        result = find_config(env=env, home=self.home, cwd=self.tmp)
        self.assertIsNotNone(result)
        path, is_legacy = result
        self.assertEqual(path, config_file)
        self.assertFalse(is_legacy)

    def test_new_config_beats_legacy(self):
        # cfg/jenkins-build/ 与 home/.claude/ 都有配置 → 命中 cfg，is_legacy False
        new_cfg_dir = self.cfg / "jenkins-build"
        new_cfg_dir.mkdir()
        new_config = new_cfg_dir / "jenkins-config.yaml"
        new_config.write_text("jenkins: {}")
        legacy_dir = self.home / ".claude"
        legacy_dir.mkdir()
        (legacy_dir / "jenkins-config.yaml").write_text("jenkins: {}")
        result = find_config(env=self.env, home=self.home, cwd=self.proj)
        self.assertIsNotNone(result)
        path, is_legacy = result
        self.assertEqual(path, new_config)
        self.assertFalse(is_legacy)

    def test_legacy_only_is_flagged(self):
        # 只有 home/.claude/ 有配置 → 命中且 is_legacy True
        legacy_dir = self.home / ".claude"
        legacy_dir.mkdir()
        legacy_config = legacy_dir / "jenkins-config.yaml"
        legacy_config.write_text("jenkins: {}")
        result = find_config(env=self.env, home=self.home, cwd=self.proj)
        self.assertIsNotNone(result)
        path, is_legacy = result
        self.assertEqual(path, legacy_config)
        self.assertTrue(is_legacy)

    def test_none_found(self):
        # 三处都没有 → find_config 返回 None
        result = find_config(env=self.env, home=self.home, cwd=self.proj)
        self.assertIsNone(result)

    def test_order_is_fixed(self):
        # config_search_paths 三项顺序与 is_legacy 标志 == [False, False, True]
        paths = config_search_paths(env=self.env, home=self.home, cwd=self.proj)
        self.assertEqual(len(paths), 3)
        flags = [is_legacy for _, is_legacy in paths]
        self.assertEqual(flags, [False, False, True])
        # 第一项用 cwd（无 PROJECT_DIR_ENV）
        self.assertEqual(paths[0][0], self.proj / "jenkins-config.yaml")
        # 第三项用 home/.claude/
        self.assertEqual(paths[2][0], self.home / ".claude" / "jenkins-config.yaml")


if __name__ == "__main__":
    unittest.main()
