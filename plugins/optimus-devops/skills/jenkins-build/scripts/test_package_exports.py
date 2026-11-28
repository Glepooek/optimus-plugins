"""jenkins_build 包导出契约的回归测试。

`main.py` 支持两种启动方式，它们解析 `from jenkins_build import JenkinsBuildSkill`
的落点不同：`python main.py` 落在包目录下的 jenkins_build.py 模块；`python -m
jenkins_build.main` 落在包本身。包 `__init__.py` 必须 re-export，否则后者报
ImportError。CI 的 gates-tests 不装 requests，故导入失败时跳过。
"""
import pathlib
import sys
import unittest

_SKILL_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SKILL_ROOT))

try:
    import jenkins_build
except ImportError:  # 缺 requests 等运行依赖时不在本测试范围内
    jenkins_build = None

from jenkins_build.jenkins_build import JenkinsBuildSkill as ModuleClass  # noqa: E402


@unittest.skipIf(jenkins_build is None, "缺 jenkins_build 运行依赖")
class TestPackageExports(unittest.TestCase):
    def test_package_reexports_skill_class(self):
        self.assertIs(jenkins_build.JenkinsBuildSkill, ModuleClass)

    def test_dunder_all_lists_only_skill_class(self):
        self.assertEqual(list(jenkins_build.__all__), ["JenkinsBuildSkill"])


if __name__ == "__main__":
    unittest.main()
