from datetime import date, timedelta
import pandas as pd
import getamedas
import requests
from bs4 import BeautifulSoup

amedas_dic = dict(気仙沼=1, 川渡=2, 築館=3, 志津川=4, 古川=5, 大衡=6, 鹿島台=7,
                  石巻=8, 新川=9, 仙台=10, 白石=11, 亘理=12, 米山=14, 塩釜=15,
                  駒ノ湯=16, 丸森=17, 名取=20, 蔵王=23, 女川=24)

# 西部の市町村をリスト化
east_city = ['泉区', '白石市', '蔵王町', '七ヶ宿町', '川崎町', '大和町',
             '大衡村', '色麻町', '加美町']
# 市町村と気象協会のコードの辞書
city_dic = dict(仙台市=4100, 青葉区=4101, 宮城野区=4102, 若林区=4103,
                太白区=4104, 泉区=4105, 白石市=4206, 角田市=4208, 蔵王町=4301,
                七ヶ宿町=4302, 大河原町=4321, 村田町=4322, 柴田町=4323,
                川崎町=4324, 丸森町=4341, 名取市=4207, 岩沼市=4211, 亘理町=4361,
                山元町=4362, 塩釜市=4203, 多賀城市=4209, 富谷市=4216,
                松島町=4401, 七ヶ浜町=4404, 利府町=4406, 大和町=4421,
                大郷町=4422, 大衡村=4424, 大崎市=4215, 色麻町=4444, 加美町=4445,
                涌谷町=4501, 美里町=4505, 栗原市=4213, 登米市=4212, 石巻市=4202,
                東松島市=4214, 女川町=4581, 気仙沼市=4205, 南三陸町=4606)


def past_temp_list(area, b_date, e_date):
    """当年の過去の平均気温のリストを取得する関数
    
    getamedasモジュールで指定期間単年度の日別のデータを取得し、平均気温のカラムを切り取る
    Args:
        area (str): アメダス地点名
        b_date (date): 取得開始日
        e_date (date): 取得最終日
    Returns:
        list:平均気温のリスト
    """
    df = getamedas.get_amedas_data(area, b_date, e_date, 1, True)
    temp_list = list(df['平均気温'])
    return temp_list


def forecast_temp_list(city, b_day, e_day):
    """気象協会の天気予報から2週間先までの平均気温を予測する関数

    Args:
        city (str):予測する市町村名
        b_day (int):取得開始日
        e_day (int):取得終了日
    Returns:
        list:平均気温のリスト
    """
    ew_num = 3420 if city in east_city else 3410
    city_num = city_dic[city]
    url = f'http://tenki.jp/forecast/2/7/{ew_num}/{city_num}/10days.html'
    res = requests.get(url)
    soup = BeautifulSoup(res.text, 'html.parser')

    def get_tmp(clas_name):
        tp = soup.find_all('span', class_=clas_name)
        tlt = [t.text for t in tp]
        tl = [int(te[:-1]) for te in tlt]
        return tl

    max_tmp_l = get_tmp('high-temp')
    min_tmp_l = get_tmp('low-temp')
    # 最高気温と最低気温の平均を平均気温とみなす
    ftl = [(t1 + t2) / 2 for (t1, t2) in zip(max_tmp_l, min_tmp_l)]
    ftl = ftl[b_day-1: e_day]
    return ftl


def normal_temp_list(area, b_date, e_date, years):
    b_date = date(b_date.year - 1, b_date.month, b_date.day)
    e_date = date(e_date.year - 1, e_date.month, e_date.day)
    df = getamedas.get_amedas_data(area, b_date, e_date, years, True)
    temp_list = list(df['平均気温'])
    return temp_list


def ave_temp_list(area, city, b_date, length, n_years):
    """平均気温のデータフレームを返す関数

    Args:
        area (str):アメダス地点名
        city (str): 市町村名
        b_date (date): 平均気温の取得開始日
        length (int): 平均気温の取得日数(〇日間）
        n_years (int): 平年値の設定年数(直近〇か年）
    Returns:
        pd.Series:平均気温のデータフレーム
    """
    e_date = b_date + timedelta(days=length - 1)
    y_date = date.today() - timedelta(days=1)
    tw_date = date.today() + timedelta(days=13)
    tw1_date = date.today() + timedelta(days=14)
    d_by = (b_date-y_date).days
    d_ey = (e_date-y_date).days
    if e_date <= y_date:
        temp_list = past_temp_list(area, b_date, e_date)
    elif b_date <= y_date and e_date <= tw_date:
        temp_list = past_temp_list(area, b_date, y_date) + \
            forecast_temp_list(city, 1, d_ey)
    elif b_date <= y_date and e_date > tw_date:
        temp_list = past_temp_list(area, b_date, y_date) + \
            forecast_temp_list(city, 1, 14) + \
            normal_temp_list(area, tw1_date, e_date, n_years)
    elif y_date < b_date <= tw_date and e_date <= tw_date:
        temp_list = forecast_temp_list(city, d_by, d_ey)
    elif y_date < b_date <= tw_date < e_date:
        temp_list = forecast_temp_list(city, d_by, 14) + \
            normal_temp_list(area, tw1_date, e_date, n_years)
    else:
        temp_list = normal_temp_list(area, b_date, e_date, n_years)

    # 日付リストを作成 (スラッシュ区切りフォーマット)
    date_list = [(b_date + timedelta(days=i)).strftime('%Y/%m/%d') for i in
                 range(length)]
    temp_df = pd.Series(temp_list, index=date_list)
    return temp_df


# 動作確認用
def main():
    area = '石巻'
    city = '石巻市'
    b_date = date(2025, 4, 10)
    length = 18
    n_years = 1
    temp_df = ave_temp_list(area, city, b_date, length, n_years)
    print(temp_df)


if __name__ == '__main__':
    main()
