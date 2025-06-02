# DUST/setup.py

from setuptools import setup, find_packages
import pathlib

setup(
    name="dust_project",                          # 패키지 이름 (임의 지정)
    version="0.1.0",
    author="Your Name",                           # 작성자 정보
    author_email="your.email@example.com",
    description="미세먼지 데이터 분석 및 예측 프로젝트 패키지",

    # find_packages()가 자동으로 __init__.py가 있는 디렉터리들을 찾아서 패키지로 등록
    packages=find_packages(
        exclude=[
            "notebook*",  # notebook 폴더는 제외
            "docs*",      # docs 폴더 제외
            "data*",      # data 폴더 제외
            "database*",  # database 폴더 제외
            "tests*"      # tests 폴더가 있으면 제외
        ]
    ),

    install_requires=[
        "pandas>=1.3.0",
        "numpy>=1.21.0",
        "sqlalchemy>=1.4.0",
        "PyMySQL>=1.0.2",
        "streamlit>=1.0.0",
        "scikit-learn>=1.0.0",     
    ],

    python_requires=">=3.8",   
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)