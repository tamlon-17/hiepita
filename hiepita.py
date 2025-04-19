import pandas as pd
from datetime import date, timedelta
import streamlit as st
import plotly.graph_objs as go
import lxml
import averagetemplist as atl

amedas_l = ['気仙沼', '川渡', '築館', '志津川', '古川', '大衡', '鹿島台',
            '石巻', '新川', '仙台', '白石', '亘理', '米山', '塩釜', '駒ノ湯',
            '丸森', '名取', '蔵王', '女川']
city_l = ['仙台市', '青葉区', '宮城野区', '若林区', '太白区', '泉区', '白石市',
          '角田市', '蔵王町', '七ヶ宿町', '大河原町', '村田町', '柴田町', '川崎町',
          '丸森町', '名取市', '岩沼市', '亘理町', '山元町', '塩釜市', '多賀城市',
          '富谷市', '松島町', '七ヶ浜町', '利府町', '大和町', '大郷町', '大衡村',
          '大崎市', '色麻町', '加美町', '涌谷町', '美里町', '栗原市', '登米市',
          '石巻市', '東松島市', '女川町', '気仙沼市', '南三陸町']

st.set_page_config(page_title='ひえピタ', page_icon='icon.ico')
st.title('ひえピタ')
st.caption('乾田直播のノビエの葉齢進展をピタっと予測するアプリだよ(/・ω・)/')
st.text('西日本のデータを使った予測です。')
st.text('実際のほ場でノビエの葉齢を確認し、散布時期を逃さないように注意してください。')
if st.button('アプリの説明～まずは読んでみてケロ！'):
    st.switch_page('pages/readme.py')

with st.form(key='input_form'):
    st.header('入力フォーム')
    a_area = st.selectbox('アメダス地点の選択', amedas_l, index=9)
    city = st.selectbox('市町村の選択', city_l)
    begin_date = st.date_input('ノビエの葉齢確認日')
    measured_la = float(st.text_input('ノビエの葉齢 ※数字のみ、小数点第一位まで', 1.2))
    years = st.text_input('平年値とするデータの年数（直近〇か年）※数字のみ')
    submit_button = st.form_submit_button(label='予測開始')

if submit_button:
    temp_df = atl.ave_temp_list(a_area, city, begin_date, 30, int(years))
    leaf_age_kan = ((temp_df - 7.0) * 0.0237).clip(lower=0).round(2)
    leaf_age_tan = ((temp_df - 9.0) * 0.0255).clip(lower=0).round(2)
    leaf_age_ish = ((temp_df - 3.0) * 0.0143).clip(lower=0).round(2)
    df_chart = pd.concat([leaf_age_kan, leaf_age_tan, leaf_age_ish], axis=1)
    df_chart.columns = ['乾直', '湛直', '移植']
    df_chart.iloc[0] = [measured_la, measured_la, measured_la]
    df_chart = df_chart.cumsum()
    st.header('予測結果')

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['乾直'],
                             name='西日本-乾直', line=dict(color='lightgreen')))
    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['移植'],
                             name='宮城-移植', line=dict(color='orange')))
    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['湛直'],
                             name='青森-湛直', line=dict(color='pink')))
    fig.update_layout(xaxis=dict(title='年/月/日', dtick=3),
                      yaxis=dict(title='ノビエ葉齢（葉）', range=(0, 7), dtick=1),
                      legend=dict(x=0.05, y=0.95, ))
    fig.add_shape(type="line", x0=0, x1=29, y0=5, y1=5, line=dict(
        color='yellow', width=1.2), layer='below')

    fig.update_layout(hovermode='x unified')

    st.plotly_chart(fig, use_container_width=True)
    st.text('葉齢の推移')
    st.dataframe(df_chart, width=270)
