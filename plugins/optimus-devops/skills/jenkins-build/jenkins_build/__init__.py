"""jenkins_build 包。

main.py 以 `python main.py`（run.sh）与 `python -m jenkins_build.main` 两种方式运行：
前者 sys.path[0] 是包目录，`from jenkins_build import JenkinsBuildSkill` 命中同目录的
jenkins_build.py 模块；后者命中本包，靠这里的 re-export 给出同一个类。
"""

from jenkins_build.jenkins_build import JenkinsBuildSkill

__all__ = ["JenkinsBuildSkill"]
