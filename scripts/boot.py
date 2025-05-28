# scripts/boot.py

import sys
from pathlib import Path

def init_project_path():
    # 이 파일(boot.py)의 절대 위치
    script_path = Path(__file__).resolve()
    # scripts/의 상위 폴더 → 프로젝트 루트
    project_root = script_path.parents[1]
    # PYTHONPATH 최상단에 추가
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))