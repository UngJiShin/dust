# scripts/boot.py

import sys
from pathlib import Path

def find_project_root(marker: str = "config/data_paths.yaml") -> Path:
    """
    1) __file__가 있으면(=스크립트 실행) __file__ 기준으로,
    2) NameError(=Notebook 실행) 발생하면 cwd 기준으로,
    상위 디렉터리 중 marker 파일(config/data_paths.yaml)이 있는 폴더를 프로젝트 루트로 간주합니다.
    """
    try:
        # 스크립트로 실행될 때는 __file__ 존재
        current = Path(__file__).resolve()
    except NameError:
        # Jupyter Notebook 등에서 실행될 때는 __file__ 미존재 → cwd 사용
        current = Path().resolve()

    for parent in [current] + list(current.parents):
        if (parent / marker).exists():
            return parent

    raise FileNotFoundError(f"Project root with marker '{marker}' not found.")


def init_project_path(verbose: bool = False) -> None:
    """
    find_project_root()로 프로젝트 루트를 찾아서 sys.path 최상단에 등록합니다.
    - verbose=True면 콘솔에 경로를 출력합니다.
    """
    project_root = find_project_root()
    project_root_str = str(project_root)

    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
        if verbose:
            print(f" 프로젝트 루트 등록: {project_root_str}")
    else:
        if verbose:
            print(f"(이미 등록됨) 프로젝트 루트: {project_root_str}")


# 파일이 import되거나 실행될 때 자동으로 프로젝트 루트를 등록
init_project_path()