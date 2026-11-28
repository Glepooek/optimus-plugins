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

# 导入必须整块放进 try：jenkins_build.jenkins_build 顶层 import requests/yaml，
# 写在模块级会让缺依赖的环境在**收集阶段**报 ImportError，skipIf 来不及生效。
try:
    import jenkins_build
    from jenkins_build.jenkins_build import JenkinsBuildSkill as _ModuleClass
except ImportError:  # 缺 requests 等运行依赖时不在本测试范围内
    jenkins_build = None
    _ModuleClass = None


@unittest.skipIf(jenkins_build is None, "缺 jenkins_build 运行依赖")
class TestPackageExports(unittest.TestCase):
    def test_package_reexports_skill_class(self):
        self.assertIs(jenkins_build.JenkinsBuildSkill, _ModuleClass)

    def test_dunder_all_lists_only_skill_class(self):
        self.assertEqual(list(jenkins_build.__all__), ["JenkinsBuildSkill"])


if __name__ == "__main__":
    unittest.main()
