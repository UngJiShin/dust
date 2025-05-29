# run.py 
import subprocess
from dotenv import load_dotenv
from pathlib import Path

# .env 로드 
load_dotenv()

# 실행할 스크립트 목록
SCRIPTS = [
    'scripts/boot.py',
    'scripts/data_loader.py',
    'scripts/transformers.py',
    'scripts/database.py',
]

def run_all():
    root = Path(__file__).parent
    for rel in SCRIPTS:
        path = root / rel
        print(f"Running {rel} ...")
        subprocess.run(['python', str(path)], check=True)
    print("All steps completed!")

if __name__ == '__main__':
    run_all()