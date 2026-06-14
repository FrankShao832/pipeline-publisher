"""
快速独立启动入口 — UI 开发验证专用。

直接弹出发布器窗口，无需完整生命周期管理。
适合在开发 UI 时快速验证改动效果。

用法:
    python publisher/standalone.py
    或直接双击此文件（需配置关联Python环境）
"""

import sys
from pathlib import Path

# 将项目根目录加入 sys.path，确保可独立运行
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from publisher.main import launch


def main():
    """启动发布器窗口并进入事件循环。"""
    app, window = launch(standalone_mode=True, show=True)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
