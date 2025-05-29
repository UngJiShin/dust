# scripts/transformers.py

import pandas as pd

def clean_date(df: pd.DataFrame) -> pd.DataFrame:
    """
    date_map(raw) → date_dim(clean)
    raw 컬럼: '연월'(예: '2023-01'), 'year', 'month'...
    """
    df = df.copy()
    # 컬럼명 strip
    df.columns = df.columns.str.strip()
    # rename
    df = df.rename(columns={
        '연월':    'date_id',
        'year':   'year',
        'month':  'month',
        'quarter':'quarter',
        'season': 'season'
    })
    # date_id 포맷팅 ('2023-01' → '202301')
    df['date_id'] = (
        df['year'].astype(int).astype(str).str.zfill(4)
    + df['month'].astype(int).astype(str).str.zfill(2)
    )
    return df[['date_id','year','month','quarter','season']]

def clean_region(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.str.strip()
    df = df.rename(columns={
        '시군구코드': 'region_id',
        '시도명':     'province',
        '시군구명':   'region_name'
    })
    return df[['region_id','province','region_name']]


def clean_age(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.str.strip()
    df = df.rename(columns={
        '구분': 'age_group',
        '나이': 'age_desc'
    })
    return df[['age_group','age_desc']]

def clean_avgcode(df: pd.DataFrame) -> pd.DataFrame:
    """
    reference_regional_avgcode_mapping.xlsx → avgcode_dim
    raw 컬럼: 'avg_code', 'province_name'
    """
    df = df.copy()
    df.columns = df.columns.str.strip()
    return df[['avg_code','province_name']]


def clean_pm10(df: pd.DataFrame, df_date: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.str.strip()

    # 날짜 처리
    df = df.rename(columns={'구분': 'raw_date'})
    df['raw_date'] = df['raw_date'].astype(str).str.replace(r'\s*월$', '', regex=True)
    df['date_id'] = df['raw_date'].str.replace('.', '', regex=False)

    # wide → long 변환
    id_vars = ['date_id', 'raw_date']
    value_vars = [col for col in df.columns if col not in id_vars]
    df_long = df.melt(id_vars=id_vars, value_vars=value_vars,
                      var_name='region_name', value_name='pm10')

    # 숫자로 변환 (공백/문자 → NaN)
    df_long['pm10'] = pd.to_numeric(df_long['pm10'], errors='coerce')

    # NaN 제거
    df_long = df_long.dropna(subset=['pm10'])

    # 계절 매핑
    df_long = df_long.merge(df_date[['date_id', 'season']], on='date_id', how='left')

    # 컬럼 정리
    return df_long[['date_id', 'region_name', 'pm10', 'season']]

def clean_pm25(df: pd.DataFrame, df_date: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.str.strip()

    # 날짜 처리
    df = df.rename(columns={'구분': 'raw_date'})
    df['raw_date'] = df['raw_date'].astype(str).str.replace(r'\s*월$', '', regex=True)
    df['date_id'] = df['raw_date'].str.replace('.', '', regex=False)

    # wide → long 변환
    id_vars = ['date_id', 'raw_date']
    value_vars = [col for col in df.columns if col not in id_vars]
    df_long = df.melt(id_vars=id_vars, value_vars=value_vars,
                      var_name='region_name', value_name='pm25')

    # 숫자로 변환 (공백/문자 → NaN)
    df_long['pm25'] = pd.to_numeric(df_long['pm25'], errors='coerce')

    # NaN 제거
    df_long = df_long.dropna(subset=['pm25'])

    # 계절 매핑
    df_long = df_long.merge(df_date[['date_id', 'season']], on='date_id', how='left')

    # 컬럼 정리
    return df_long[['date_id', 'region_name', 'pm25', 'season']]


def clean_asthma(df: pd.DataFrame, df_region: pd.DataFrame, df_date: pd.DataFrame) -> pd.DataFrame:
    """
    asthma(raw) → asthma_fact(clean)
    raw 컬럼: '요양개시연월','시도명','시군구코드','성별','연령군','진료에피소드 건수'
    """
    df = df.copy()
    df.columns = df.columns.str.strip()
    df = df.rename(columns={
        '요양개시연월':       'date_id',        
        '시도명':            'region_name',
        '시군구명':         'district_name',
        '시군구코드':        'region_id',
        '성별':              'gender',
        '연령군':            'age_group',
        '진료에피소드 건수':  'episode_count'
    })
    df['date_id'] = pd.to_datetime(df['date_id']).dt.strftime('%Y%m')
    return df[['date_id', 'region_id', 'region_name', 'district_name', 'gender', 'age_group', 'episode_count']]


def clean_rhinitis(df: pd.DataFrame, df_region: pd.DataFrame, df_date: pd.DataFrame) -> pd.DataFrame:
    """
    rhinitis(raw) → rhinitis_fact(clean)
    raw 컬럼: '요양개시연월','시도명','시군구코드','성별','연령군','진료에피소드 건수'
    """
    df = df.copy()
    df.columns = df.columns.str.strip()
    df = df.rename(columns={
        '요양개시연월':       'date_id',
        '시도명':            'region_name',
        '시군구명':         'district_name',
        '시군구코드':        'region_id',
        '성별':              'gender',
        '연령군':            'age_group',
        '진료에피소드 건수':  'episode_count'
    })
    df['date_id'] = pd.to_datetime(df['date_id']).dt.strftime('%Y%m')
    return df[['date_id', 'region_id', 'region_name', 'district_name', 'gender', 'age_group', 'episode_count']]