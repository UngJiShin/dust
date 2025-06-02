# src/utils/project_setup.py

import sys
from pathlib import Path

CONFIG_MARKER = "config/data_paths.yaml"

def find_project_root(marker: str = CONFIG_MARKER) -> Path:
    """
    - __file__ 기준 실행(스크립트) 시: 해당 파일 위치에서 위로 올라가며 탐색
    - NameError 발생 시(Notebook 등): CWD(현재 작업 디렉터리)에서 위로 올라가며 탐색
    """
    try:
        current = Path(__file__).resolve()
    except NameError:
        current = Path().resolve()

    for parent in [current] + list(current.parents):
        if (parent / marker).exists():
            return parent

    raise FileNotFoundError(f"Project root with marker '{marker}' not found.")

def add_to_sys_path(path: Path) -> None:
    """
    path(=프로젝트 루트)를 sys.path 최상단에 추가합니다.
    """
    s = str(path)
    if s not in sys.path:
        sys.path.insert(0, s)

def init(verbose: bool = True) -> Path:
    """
    Jupyter Notebook 등 어디서든 이 함수를 한 번 실행하면,
    1) find_project_root()로 루트를 찾아
    2) add_to_sys_path()로 sys.path에 등록하고
    3) (verbose=True인 경우) 등록된 경로를 출력합니다.
    """
    root = find_project_root()
    add_to_sys_path(root)
    if verbose:
        print(f"프로젝트 루트: {root}")
        print(f"sys.path 맨 앞에 추가됨: {sys.path[0]}")
    return root