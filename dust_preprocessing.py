import numpy as np
import pandas as pd
import math
import matplotlib.pyplot as plt

fine_df = pd.read_csv('./data/finedust.csv')
ultrafine_df = pd.read_csv('./data/ultrafinedust.csv')

ultrafine_df = ultrafine_df.drop(columns=ultrafine_df.columns[27:])  # Unnamed 컬럼 제거
fine_df = fine_df.dropna(subset=['Date'])  # 날짜 없는 행 제거

# 'Date' 열은 제외하고 수치형 데이터만 선택
fine_num_df = fine_df.drop(columns=['Date'])
ultrafine_num_df = ultrafine_df.drop(columns=['Date'])

# 각 행의 평균을 이용해 결측치 채우기
fine_filled_df = fine_num_df.T.fillna(fine_num_df.mean(axis=1)).T
ultrafine_filled_df = ultrafine_num_df.T.fillna(ultrafine_num_df.mean(axis=1)).T

# 'Date' 열 다시 합치기
fine_result_df = pd.concat([fine_df['Date'], fine_filled_df], axis=1)
ultrafine_result_df = pd.concat([ultrafine_df['Date'], ultrafine_filled_df], axis=1)

# 결과 저장 (선택)
fine_result_df.to_csv('./data/finedust_filled.csv', index=False)
ultrafine_result_df.to_csv('./data/ultrafinedust_filled.csv', index=False)

print(fine_result_df.isnull().sum().sum())  # 0이면 결측치 없음
print(ultrafine_result_df.isnull().sum().sum()) # 0이면 결측치 없음