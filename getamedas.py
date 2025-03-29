"""アメダスから気象データを取得するモジュール

地点、期間、年数を入れると、指定期間のうち年数分遡った気象データの平均値を、データフレームで返す。
日別と半旬別の2種類の関数がある。
気象データは、平均気温、最高気温、最低気温、降水量、日照時間を取得
"""

from datetime import date, timedelta
from io import BytesIO
import numpy as np
import pandas as pd
import lxml


def amedas_area(area):
    """URLに入力するアメダス地点のコードとキーを取得

    Args:
        area (str):アメダス地点
    Returns:
       (tuple):
        - code (int): URLに入れる地点コード
        - key (str): 仙台、石巻だけsを入れる
    """
    dic = dict(気仙沼="0242", 川渡="0243", 築館="0244", 志津川="0246",
               古川="0247", 大衡="0248", 鹿島台="0249", 石巻="47592",
               新川="0251", 仙台="47590", 白石="0256", 亘理="0257", 米山="1029",
               塩釜="1030", 駒ノ湯="1126", 丸森="1220", 名取="1464",
               蔵王="1564", 女川="1626")
    code = dic[area]
    key = "s" if area in ["仙台", "石巻"] else "a"
    return code, key


def date_adjust(b_date, e_date, is_daily):
    """期間が1年以上の場合に、365日後に修正する関数

    Args:
        b_date (date):開始年月日
        e_date (date):終了年月日
        is_daily (bool):日別か半旬か
    Returns:
        date: 修正後の終了年月日
    """
    e_date = e_date if e_date < date.today() else (date.today() -
                                                   timedelta(days=1))
    b_date = b_date if b_date < e_date else e_date - timedelta(days=1)
    e_date = e_date if (e_date - b_date) < timedelta(days=367) \
        else (b_date + timedelta(days=364))
    if not is_daily and date.today() - e_date < timedelta(days=5):
        d_days = date.today().day % 5 if date.today().day % 5 != 0 else 5
        e_date = date.today() - timedelta(days=d_days)
        b_date = b_date if b_date < e_date else e_date - timedelta(days=1)
    return b_date, e_date


def scrape_amedas(a_code, year, month, key, is_daily):
    """気象庁HPから日別の気象データをスクレイピングする関数

    Args:
        a_code (int): アメダス地点から取得したコード
        year (int):取得年
        month (int):取得月
        key (str):仙台と石巻だけ違うURL
        is_daily (bool):日別（Ture）か半旬別（False）か
    Returns:
        (pd.DataFrame): アメダスからスクレイプしたデータフレーム
    """
    d = 'daily' if is_daily else 'mb5daily'
    url = (
        f"https://www.data.jma.go.jp/stats/etrn/view/{d}_{key}1.php?prec_no"
        f"=34&block_no={a_code}&year={year}&month={month}&day=&view=p1"
    )
    df = pd.read_html(url)
    return df[0]


# スクレイピングしたDFから不要なカラムを削除
def extract_col(df, key, is_daily):
    """取得DFから必要なカラムを整理して気象情報だけにする関数
    
    Args:
        df (pd.DataFrame): スクレイピングしたデータフレーム
        key (str): 仙台、石巻の区別（s）
        is_daily (bool): 日別（Ture）か半旬別（False）か
    Returns:
        (pd.DataFrame): 5つの気象データだけに整理したデータフレーム
    """
    list1 = [6, 7, 8, 3, 16]
    list2 = [4, 5, 6, 1, 15]
    list3 = [9, 10, 11, 5, 21]
    list4 = [7, 8, 9, 3, 19]
    if is_daily:
        col = list1 if key == 's' else list2
    else:
        col = list3 if key == 's' else list4
    return df.iloc[:, col]


# クリーンアップの関数
def clean_df(df):
    """アメダスDFの数値以外のデータを数値に修正する関数

    Args:
        df (pd.DataFrame):生データのデータフレーム
    Returns:
        (pd.DataFrame): 要素がすべて数値になったデータフレーム
    """
    df = df.replace(["//", "#"], np.nan)
    df = df.replace("--", 0.0)
    df = df.replace([r"\)", r" \]"], "", regex=True)
    try:
        df = df.apply(pd.to_numeric, errors="coerce")  # 非数値は自動的にNaNに変換
    except Exception as e:
        print(f"Error during conversion: {e}")
    return df


def get_1month_df(a_code, year, month, key):
    """日別の1か月分のDFを取得する関数

    2月だけ、うるう年でも28日までのデータに限定する条件分岐が入ってる
    Args:
        a_code (int):アメダス地点のコード
        year (int):取得年
        month (int):取得月
        key (str):仙台と石巻だけs
    Returns:
        pd.DataFrame:1か月分の気象データのデータフレーム
    """
    df = scrape_amedas(a_code, year, month, key, is_daily=True)
    df = extract_col(df, key, is_daily=True)
    df = clean_df(df)
    if month == 2:
        df = df.drop(index=[28], errors="ignore")
    return df


def get_months_df(a_code, b_date, e_date, year, key):
    """日別の開始月から終了月までのデータを取得して、1つのdfにまとめる

    Args:
        a_code (int):アメダス地点のコード
        b_date (date):開始日
        e_date (date):終了日
        year (int):開始年
        key (str):仙台石巻だけs
    Returns:
        pd.DataFrame:指定範囲月の気象データのデータフレーム
    """
    if b_date.year == e_date.year:
        df_l = [get_1month_df(a_code, year, m, key) for m in range(
            b_date.month, e_date.month + 1)]
    else:
        df_l1 = [get_1month_df(a_code, year, m, key) for m in range(
            b_date.month, 13)]
        df_l2 = [get_1month_df(a_code, year + 1, m, key) for m in range(
            1, e_date.month + 1)]
        df_l = df_l1 + df_l2
    columns = ['平均気温', '最高気温', '最低気温', '降水量', '日照時間']
    df = pd.concat(df_l).set_axis(columns, axis=1)
    days = e_date - b_date
    df = df.iloc[b_date.day - 1: b_date.day + days.days]
    return df


def hanjun(day: int) -> int:
    """日付から半旬を取得

    Args:
        day (int):日付
    Returns:
        int: 第〇半旬
    """
    return (day - 1) // 5 + 1 if day <= 30 else 6


# 半旬別の1or2年のDFを連結して取得して指定半旬で切り取って整形
def get_harf_df(a_code, b_date: date, e_date: date, year, key):
    """半旬別の指定期間のデータ取得関数

    Args:
        a_code (int): アメダス地点のコード
        b_date (date): 開始日
        e_date (date): 終了日
        year (int): 取得開始年
        key (str): 仙台、石巻はs
    Returns:
        pd.DataFrame:半旬別の指定期間の気象データのデータフレーム
    """
    df = scrape_amedas(a_code, year, 1, key, False)
    if b_date.year != e_date.year:
        df1 = scrape_amedas(a_code, year + 1, 1, key, False)
        df = pd.concat([df, df1], ignore_index=True)
    df = extract_col(df, key, False)
    df = clean_df(df)
    df = df.iloc[(b_date.month - 1) * 6 + hanjun(b_date.day) - 1:
                 len(df) - (13 - e_date.month) * 6 + hanjun(e_date.day), :]
    columns = ['平均気温', '最高気温', '最低気温', '降水量', '日照時間']
    return df.reset_index(drop=True).set_axis(columns, axis=1)


# DFのリストからnp.array経由で平均値のDFを取得
def mean_df(dfl):
    """DFリストからnp.arrayを使って平均値のDFを取得

    Args:
        dfl (list):複数年の気象データのリスト
    Returns:
        pd.DataFrame:平年値のDF
    """
    arrays = [df.to_numpy() for df in dfl]
    array_3d = np.stack(arrays)
    mean_np = np.round(np.nanmean(array_3d, axis=0), decimals=1)
    columns = ['平均気温', '最高気温', '最低気温', '降水量', '日照時間']
    return pd.DataFrame(mean_np, columns=columns)


def date_index(b_date, e_date):
    """日別のデータフレームの日付indexを取得する関数

    Args:
        b_date (date):開始日
        e_date (date):終了日
    Returns:
        list: 日付のindexリスト
    """
    date_list = []
    current_date = b_date
    while current_date <= e_date:
        date_list.append(current_date.strftime("%m/%d"))
        current_date += timedelta(days=1)
    return date_list


def harf_index(b_date, e_date):
    index_list = []





def get_amedas_data(area, b_date: date, e_date: date, years, is_daily):
    """指定期間のアメダスデータを取得する関数

    Args:
        area (str):アメダス地点名
        b_date (date):取得開始日
        e_date (date):取得終了日
        years (int): 取得年数（取得開始年から何年遡るか）
        is_daily (bool): 日別(Ture）か半旬別(False）か
    Returns:
        pd.DataFrame:アメダスデータのデータフレーム
    """
    a_code, key = amedas_area(area)
    b_date, e_date = date_adjust(b_date, e_date, is_daily)
    if is_daily:
        df_l = [get_months_df(a_code, b_date, e_date, y, key) for y in range(
            b_date.year + 1 - years, b_date.year + 1)]
        df = mean_df(df_l)
        df.index = date_index(b_date, e_date)
    else:
        df_l = [get_harf_df(a_code, b_date, e_date, y, key) for y in range(
            b_date.year + 1 - years, b_date.year + 1)]
        df = mean_df(df_l)
    return df


def convert_to_excel(df):
    """データフレームをエクセルに変換する関数

    Args:
        df (pd.DataFrame):参照するデータフレーム
    Returns:
        bytes:よくわかんね
    """
    output = BytesIO()  # メモリバッファを作成
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Sheet1')
    return output.getvalue()


def main():
    df = get_amedas_data('石巻', date(2025, 1, 31), date(2025, 2, 1), 1, True)
    print(df)
    df2 = get_amedas_data('古川', date(2025, 2, 2), date(2025, 3, 3), 5, False)
    print(df2)


if __name__ == "__main__":
    main()
