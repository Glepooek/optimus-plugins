"""
Jenkins Build CLI
用法：
  python main.py                        # 触发默认 job
  python main.py zk-api                 # 触发指定 job
  python main.py zk-api BRANCH=main     # 触发带参数的 job
"""

import os
import sys
from pathlib import Path
import yaml
from jenkins_build import JenkinsBuildSkill

# 将 skill 根目录的 scripts/ 加入路径，以便导入 jenkins_config_paths / optimus_dirs
_SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SKILL_ROOT / "scripts"))

from jenkins_config_paths import config_search_paths, find_config  # noqa: E402
import optimus_dirs  # noqa: E402


def load_config() -> dict:
    result = find_config()
    if result is not None:
        config_path, is_legacy = result
        print(f"[i] 使用配置文件：{config_path}")
        if is_legacy:
            dirs = optimus_dirs.skill_dirs("jenkins-build")
            new_path = Path(dirs["config_dir"]) / "jenkins-config.yaml"
            print(f"[!] 正在读取旧配置位置 {config_path}；请迁移到 {new_path}，旧位置今后只读不写")
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    print("[✗] 未找到配置文件，请在以下任一位置创建 jenkins-config.yaml：")
    for path, _ in config_search_paths():
        print(f"    {path}")
    print("    参考：jenkins_build/jenkins-config.yaml.example")
    sys.exit(1)


def parse_args(args):
    """解析命令行参数，返回 (job_name, params)"""
    job_name = None
    params = {}
    for arg in args:
        if "=" in arg:
            k, v = arg.split("=", 1)
            params[k] = v
        elif job_name is None:
            job_name = arg
    return job_name, params


def main():
    config = load_config()
    jenkins_cfg = config["jenkins"]
    jobs = config.get("jobs", {})

    skill = JenkinsBuildSkill(
        jenkins_url=jenkins_cfg["url"],
        username=jenkins_cfg["username"],
        api_token=jenkins_cfg.get("api_token"),
        password=jenkins_cfg.get("password"),
    )

    job_name, params = parse_args(sys.argv[1:])

    if job_name is None:
        job_name = next(iter(jobs))

    if job_name not in jobs:
        print(f"[✗] 未找到 job '{job_name}'，可用 job：{list(jobs.keys())}")
        sys.exit(1)

    job_path = jobs[job_name]["path"]
    default_params = jobs[job_name].get("default_params", {})
    merged_params = {**default_params, **params}
    print(f"[→] 触发 job: {job_name}  path: {job_path}")
    if merged_params:
        print(f"    参数: {merged_params}")

    result, commits = skill.run(job_path, params=merged_params or None)

    if commits:
        print(f"[i] 本次构建涉及 {len(commits)} 条提交：")
        for msg in commits:
            print(f"    - {msg}")

    sys.exit(0 if result == "SUCCESS" else 1)


if __name__ == "__main__":
    main()
