import plotly.graph_objs as go
from flask import Flask, render_template
import hashlib
from flask import Flask, render_template, request, redirect, url_for, session, abort, flash
from flask import Response, json, jsonify, send_file, render_template_string
from flask_mysqldb import MySQL
# plot
import plotly
import plotly.express as px
import plotly.figure_factory as ff
import pandas as pd
from plotly.subplots import make_subplots

import numpy as np
import pandas as pd

app = Flask(__name__)
app.secret_key = 'Duong Nam'

# app.config['MYSQL_HOST'] = 'localhost'
# app.config['MYSQL_PORT'] = 3333
# app.config['MYSQL_USER'] = 'root'
# app.config['MYSQL_PASSWORD'] = '1234abC@'
# app.config['MYSQL_DB'] = 'stock_db'
# app.config['MYSQL_DATABASE_AUTH_PLUGIN'] = 'mysql_native_password'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_PORT'] = 3308
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'stock_db'
app.config['MYSQL_DATABASE_AUTH_PLUGIN'] = 'mysql_native_password'
mysql = MySQL(app)

#D1
# @app.route("/")
@app.route('/cand/<timeframe>/<ticker>', methods=['GET', 'POST'])
def create_cand_chart(timeframe="d1", ticker="TCH"):
    cur = mysql.connection.cursor()

    if timeframe == "m1":
        table_name = "m1"
    elif timeframe == "m15":
        table_name = "m15"
    elif timeframe == "m30":
        table_name = "m30"
    elif timeframe == "h1":
        table_name = "h1"
    elif timeframe == "d1":
        table_name = "d1"
    else:
        return "Khung giờ không hợp lệ"

    # Truy vấn SQL để lấy giá mở cửa, giá đóng cửa, giá cao nhất, giá thấp nhất và khối lượng giao dịch của ngày mới nhất
    cur.execute(f"SELECT open, close, high, low, volume FROM {table_name} WHERE ticker = %s ORDER BY time_stamp DESC LIMIT 1", (ticker,))
    latest_data = cur.fetchone()

    if latest_data:
        open_price, close_price, high_price, low_price, volume = latest_data
    else:
        open_price, close_price, high_price, low_price, volume = None, None, None, None, None

    cur.execute(f"SELECT * FROM {table_name} WHERE ticker = %s ORDER BY time_stamp DESC LIMIT 100", (ticker,))
    records = cur.fetchall()

    columnName = ['ticker', 'time_stamp', 'open', 'low', 'high', 'close', 'volume', 'sum_price']
    df = pd.DataFrame.from_records(records, columns=columnName)
    df['time_stamp'] = pd.to_datetime(df['time_stamp'], unit='s')
    df['time'] = df['time_stamp'].dt.tz_localize('UTC').dt.tz_convert('Asia/Ho_Chi_Minh')
    df = df.sort_values(by='time', ascending=True).reset_index(drop=True)

    fig = go.Figure(data=[go.Candlestick(
        x=df['time'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close']
    )])

    fig.update_layout(
        xaxis_title='Thời gian',
        yaxis_title='Giá',
        plot_bgcolor='#363636',
        xaxis_gridcolor='gray',
        yaxis_gridcolor='gray',
        xaxis_rangeslider_visible=True
    )

    plot_html = fig.to_html(full_html=False)

    cur.execute("SELECT DISTINCT ticker FROM d1")
    stock_codes = [code[0] for code in cur.fetchall()]

    return render_template("/chart/cand/cand.html", plot_cand=plot_html, ticker=ticker, stock_codes=stock_codes, selected_timeframe=timeframe, open_price=open_price, close_price=close_price, high_price=high_price, low_price=low_price, volume=volume)
# @app.route("/")
@app.route("/analyst/d1/<ticker>", methods=['GET', 'POST'])
def analyst(ticker = "TCH"):
    cur = mysql.connection.cursor()
    
    # Truy vấn dữ liệu từ SQL
    cur.execute(f"SELECT * FROM d1 WHERE ticker = %s ORDER BY time_stamp DESC LIMIT 100", (ticker,))
    records = cur.fetchall()
    columnName = ['ticker', 'time_stamp', 'open', 'low', 'high', 'close', 'volume', 'sum_price']
    df = pd.DataFrame.from_records(records, columns=columnName)
    df['time_stamp'] = pd.to_datetime(df['time_stamp'], unit='s')
    df['time'] = df['time_stamp'].dt.tz_localize('UTC').dt.tz_convert('Asia/Ho_Chi_Minh')
    df = df.sort_values(by='time', ascending=True).reset_index(drop=True)
    # Tính trung bình trượt 20 ngày
    df['20_day_sma'] = df['close'].rolling(window=20).mean()

    # Tính độ lệch chuẩn 20 ngày
    df['20_day_std'] = df['close'].rolling(window=20).std()

    # Tính Bollinger Bands
    df['upper_band'] = df['20_day_sma'] + (df['20_day_std'] * 2)
    df['lower_band'] = df['20_day_sma'] - (df['20_day_std'] * 2)

    # Tạo biểu đồ Bollinger Bands sử dụng Plotly
    fig_bb = go.Figure()

    # Hiển thị dữ liệu Giá và Bollinger Bands
    fig_bb.add_trace(go.Scatter(x=df['time'], y=df['close'], mode='lines', name='Giá đóng cửa', line=dict(color='#00F4B0', width=5)))
    fig_bb.add_trace(go.Scatter(x=df['time'], y=df['20_day_sma'], mode='lines', name='Trung bình 20 ngày',line=dict(color='#FBAC20',  dash='dot',  width=3)))
    fig_bb.add_trace(go.Scatter(x=df['time'], y=df['upper_band'], mode='lines', name='Dải trên Bollinger Bands', line=dict(color='#555555',  width=4)))
    fig_bb.add_trace(go.Scatter(x=df['time'], y=df['lower_band'],fill='tonexty', mode='lines', name='Dải dưới Bollinger Bands', line=dict(color='#555555',  width=3)))

    # Cài đặt thuộc tính cho biểu đồ, đặt màu nền trắng và ẩn các đường kẻ dọc
    fig_bb.update_layout(
                    xaxis=dict(title='Thời gian', showgrid=False),  # Ẩn đường kẻ dọc trên trục x
                    yaxis=dict(title='Giá'),  # Ẩn đường kẻ dọc trên trục y
                    xaxis_rangeslider_visible=True,
                    plot_bgcolor='#363636',  # Màu nền của biểu đồ
                    paper_bgcolor='white',  # Màu nền của toàn bộ khung biểu đồ
                    xaxis_gridcolor='gray',  # Màu của đường kẻ ngang
                    yaxis_gridcolor='gray',
                    legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1)) # Màu của đường kẻ ngang
    # Chuyển biểu đồ Plotly thành HTML
    plot_bb = fig_bb.to_html(full_html=False)
     # Tính trung bình trượt 5 ngày và 20 ngày
    df['5_day_sma'] = df['close'].rolling(window=5).mean()
    df['20_day_sma_2'] = df['close'].rolling(window=20).mean()

    # Tạo biểu đồ tương tác
    fig_ma = go.Figure()

    # Hiển thị dữ liệu Giá cổ phiếu và MA(5) và MA(20)
    fig_ma.add_trace(go.Scatter(x=df['time'], y=df['close'], mode='lines', name='Giá đóng cửa', line=dict(color='#00F4B0', width=5)))
    fig_ma.add_trace(go.Scatter(x=df['time'], y=df['5_day_sma'], mode='lines', name='MA(5)', line=dict(color='#FBAC20',  dash='dot',width=3)))
    fig_ma.add_trace(go.Scatter(x=df['time'], y=df['20_day_sma_2'], mode='lines', name='MA(20)', line=dict(color='#64BAFF',  dash='dot', width=3)))

    # Cài đặt thuộc tính cho biểu đồ, đặt màu nền trắng
    fig_ma.update_layout(title='Biểu đồ Giá cổ phiếu và MA(5) và MA(20)',
                    xaxis=dict(title='Thời gian',  showgrid=False),
                    yaxis=dict(title='Giá'),
                    xaxis_rangeslider_visible=True,
                    plot_bgcolor='#363636',  # Màu nền của biểu đồ
                    paper_bgcolor='white',  # Màu nền của toàn bộ khung biểu đồ
                    xaxis_gridcolor='gray',  # Màu của đường kẻ ngang
                    yaxis_gridcolor='gray',
                    legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1))# Màu của đường kẻ ngang
    plot_ma = fig_ma.to_html(full_html=False)
    
        # Tính đường MACD (Moving Average Convergence Divergence)
    short_term = df['close'].ewm(span=12).mean()
    long_term = df['close'].ewm(span=26).mean()
    df['MACD'] = short_term - long_term

    # Tính đường Tín hiệu (Signal Line)
    df['Signal_Line'] = df['MACD'].ewm(span=9).mean()

    # Tính MACD Histogram
    df['MACD_Histogram'] = df['MACD'] - df['Signal_Line']

    # Tạo biểu đồ MACD sử dụng Plotly
    fig_macd = go.Figure()

    # Hiển thị dữ liệu MACD và Signal Line
    fig_macd.add_trace(go.Scatter(x=df['time'], y=df['MACD'], mode='lines', name='MACD', line=dict(color='#FF3747', width=5)))
    fig_macd.add_trace(go.Scatter(x=df['time'], y=df['Signal_Line'], mode='lines', name='Signal Line', line=dict(color='#64BAFF', width=5)))

    # Tạo biểu đồ Histogram
    fig_macd.add_trace(go.Bar(x=df['time'], y=df['MACD_Histogram'], name='MACD Histogram', marker=dict(color='#64BAFF')))

    # Cài đặt thuộc tính cho biểu đồ
    fig_macd.update_layout(
                    xaxis=dict(title='Thời gian', showgrid=False),
                    yaxis=dict(title='Giá trị'),
                    xaxis_rangeslider_visible=True,
                    plot_bgcolor='#363636',  # Màu nền của biểu đồ
                    paper_bgcolor='white',  # Màu nền của toàn bộ khung biểu đồ
                    xaxis_gridcolor='gray',  # Màu của đường kẻ ngang
                    yaxis_gridcolor='gray',
                    legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1))# Màu của đường kẻ ngang đồ

    plot_macd = fig_macd.to_html(full_html=False)
    
     # Tính %K và %D
    period = 14  # Kỳ giao dịch
    smooth = 3   # Độ trơn
    df['low_min'] = df['low'].rolling(window=period).min()
    df['high_max'] = df['high'].rolling(window=period).max()
    df['%K'] = 100 * (df['close'] - df['low_min']) / (df['high_max'] - df['low_min'])
    df['%D'] = df['%K'].rolling(window=smooth).mean()

    # Tạo biểu đồ Stochastic Oscillator sử dụng Plotly
    fig_stoch = go.Figure()

    # Hiển thị dữ liệu %K và %D
    fig_stoch.add_trace(go.Scatter(x=df['time'], y=df['%K'], mode='lines', name='%K (màu xanh)', line=dict(color='#64BAFF', width=5)))
    fig_stoch.add_trace(go.Scatter(x=df['time'], y=df['%D'], mode='lines', name='%D (màu đỏ)', line=dict(color='#FF3747', width=5)))

    # Vẽ đường giới hạn 20 và 80
    fig_stoch.add_shape(
        go.layout.Shape(
            type="line",
            x0=df['time'].min(),
            x1=df['time'].max(),
            y0=20,
            y1=20,
            line=dict(color="white", dash="dash", width = 3),
        )
    )
    fig_stoch.add_shape(
        go.layout.Shape(
            type="line",
            x0=df['time'].min(),
            x1=df['time'].max(),
            y0=80,
            y1=80,
            line=dict(color="white", dash="dash", width = 3),
        )
    )
    # Cài đặt thuộc tính cho biểu đồ
    fig_stoch.update_layout(
                    xaxis=dict(title='Thời gian', showgrid=False),
                    yaxis=dict(title='%'),
                    xaxis_rangeslider_visible=True,
                    yaxis_range=[0, 100],
                    plot_bgcolor='#363636',  # Màu nền của biểu đồ
                    paper_bgcolor='white',  # Màu nền của toàn bộ khung biểu đồ
                    xaxis_gridcolor='gray',  # Màu của đường kẻ ngang
                    yaxis_gridcolor='gray',
                    legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1))# Màu của đường kẻ ngang đồ
    plot_stoch = fig_stoch.to_html(full_html=False)
    
    # Tính chỉ số RSI(14)
    delta = df['close'].diff(1)
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    print(rsi.head(20))

    # Tạo biểu đồ RSI(14) với đường giới hạn 30 và 70
    fig_rsi = go.Figure()

    # Hiển thị dữ liệu RSI(14)
    fig_rsi.add_trace(go.Scatter(x=df['time'], y=rsi, mode='lines', name='RSI(14)', line=dict(color='#FBAC20', width = 5)))

    # Thêm đường giới hạn 30 và 70
    fig_rsi.add_shape(
        go.layout.Shape(
            type="line",
            x0=df['time'].min(),
            x1=df['time'].max(),
            y0=30,
            y1=30,
            line=dict(color="white", dash="dash", width = 3),
        )
    )
    fig_rsi.add_shape(
        go.layout.Shape(
            type="line",
            x0=df['time'].min(),
            x1=df['time'].max(),
            y0=70,
            y1=70,
            line=dict(color="white", dash="dash", width = 2),
        )
    )

    # Đặt các thuộc tính cho biểu đồ
    fig_rsi.update_layout(title='RSI(14) với Đường Giới Hạn 30 và 70',
                    xaxis=dict(title='Thời gian', showgrid=False),
                    yaxis=dict(title='RSI'),
                    xaxis_rangeslider_visible=True,
                    plot_bgcolor='#363636',  # Màu nền của biểu đồ
                    paper_bgcolor='white',  # Màu nền của toàn bộ khung biểu đồ
                    xaxis_gridcolor='gray',  # Màu của đường kẻ ngang
                    yaxis_gridcolor='gray',
                    legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1))# Màu của đường kẻ ngang đồ
    plot_rsi = fig_rsi.to_html(full_html=False)
    
    cur.execute("SELECT DISTINCT ticker FROM d1")
    stock_codes = [code[0] for code in cur.fetchall()]

    return render_template("/chart/analyst/analyst.html", plot_bb=plot_bb, plot_ma = plot_ma, plot_macd = plot_macd, plot_stoch = plot_stoch, plot_rsi = plot_rsi, ticker=ticker, stock_codes=stock_codes)

# @app.route("/")
@app.route('/analyst/mcdx/<timeframe>/<ticker>', methods=['GET', 'POST'])
def create_mcdx_chart(timeframe="m15", ticker="TCH"):
    cur = mysql.connection.cursor()

    if timeframe == "m1":
        table_name = "m1_intraday_table"
    elif timeframe == "m15":
        table_name = "m15_intraday_table"
    elif timeframe == "h1":
        table_name = "h1_intraday_table"
    elif timeframe == "d1":
        table_name = "d1_intraday_table"
    else:
        return "Khung giờ không hợp lệ"


    cur.execute(f"SELECT * FROM {table_name} WHERE ticker = %s", (ticker,))
    records = cur.fetchall()

    columnName = ['ticker', 'time_stamp', 'percent_sheep_buy', 'percent_shark_sell', 'percent_shark_buy', 'percent_wolf_sell', 'percent_wolf_buy', 'percent_sheep_sell', "avg_price", "sum_vol", "order_count"]
    df = pd.DataFrame.from_records(records, columns=columnName)
    df['time_stamp'] = pd.to_datetime(df['time_stamp'], unit='s')
    df['time'] = df['time_stamp'].dt.tz_localize('UTC')

    df["Sharks"] = (df["percent_shark_sell"] + df["percent_shark_buy"]) * 20
    df["Wolfs"] = (df["percent_wolf_sell"] + df["percent_wolf_buy"]) * 20
    df["Sheeps"] = (df["percent_sheep_sell"] + df["percent_sheep_buy"]) * 20


    df['5_day_sma'] = df['Sharks'].rolling(window=5).mean()

    # Tạo biểu đồ cột thanh miền
    fig = px.bar(df, x='time', y=["Sharks", "Wolfs", "Sheeps"],
                labels={'variable': 'Class', 'value': 'Value'},
                title='Biểu đồ cột thanh miền',
                barmode='relative',
                color_discrete_sequence=['#ef5350','#fdff06', '#42ad39'])
    fig.add_trace(go.Scatter(x=df['time'], y=df['5_day_sma'], mode='lines', name='MA(5)', line=dict(color='#2196f3',  width = 3)))
    fig.update_xaxes(type='category',
                    showticklabels=False)

    plot_html = fig.to_html(full_html=False)

    cur.execute("SELECT DISTINCT ticker FROM d1")
    stock_codes = [code[0] for code in cur.fetchall()]

    return render_template("/chart/analyst/mcdx.html", plot_mcdx=plot_html, ticker=ticker, stock_codes=stock_codes, selected_timeframe=timeframe)

@app.route("/")
@app.route('/analyst/<timeframe>', methods=['GET', 'POST'])
def create_treemap(timeframe="daylyArray"):
    cur = mysql.connection.cursor()
    cur.execute("""
    SELECT DISTINCT d1.time_stamp FROM d1;
    """)
    records = cur.fetchall()
    columnName = ['timestamp']
    timestamp_table = pd.DataFrame.from_records(records, columns=columnName)['timestamp'].values
    timestamp_table = np.sort(timestamp_table)

    # #day
    # daylyArray = timestamp_table[-2:]
    # #week
    # weekArray = timestamp_table[-8:]
    # #month
    # monthArray = timestamp_table[-31:]

    if timeframe == "daylyArray":
        selected_timeframe = timestamp_table[-2:]
    elif timeframe == "weekArray":
        selected_timeframe = timestamp_table[-8:]
    elif timeframe == "monthArray":
        selected_timeframe = timestamp_table[-31:]
    else:
        return "Khung giờ không hợp lệ"
    if request.method == 'POST':
        selected_timeframe = request.form.get('timeframe')
        if selected_timeframe == "daylyArray":
            return redirect('/analyst/daylyArray')
        elif selected_timeframe == "weekArray":
            return redirect('/analyst/weekArray')
        elif selected_timeframe == "monthArray":
            return redirect('/analyst/monthArray')
        else:
            return "Khung giờ không hợp lệ"
    cur.execute("""SELECT * 
    FROM d1
    WHERE d1.time_stamp = %s;
    """, (int(selected_timeframe[0]),))
    records = cur.fetchall()
    columnName = ['ticker', 'time_stamp_pr', 'open_pr', 'low_pr', 'high_pr', 'close_pr', 'volume_pr', 'sum_price_pr']
    df_price_previous = pd.DataFrame.from_records(records, columns=columnName)
    
    #target
    # Truy vấn dữ liệu từ SQL
    cur.execute("""SELECT * 
    FROM d1
    WHERE d1.time_stamp = %s;
    """, (int(selected_timeframe[-1]),))
    records = cur.fetchall()
    columnName = ['ticker', 'time_stamp', 'open', 'low', 'high', 'close', 'volume', 'sum_price']
    df_price = pd.DataFrame.from_records(records, columns=columnName)
    df_price = df_price.set_index('ticker').join(df_price_previous.set_index('ticker'), on='ticker', validate='1:1').reset_index()
    df_price = df_price[['ticker', 'time_stamp', 'open', 'low', 'high', 'close', 'volume', 'close_pr']]
    #append infomation
    cur.execute("""SELECT ct.ticker, ct.comGroupCode, ct.organName, ct.organShortName, it.industry_name 
    FROM company_table ct
    JOIN company_subgroup cs ON ct.ticker = cs.id_company
    JOIN group_subgroup gs ON gs.id_subgroup = cs.id_subgroup
    JOIN industry_group ig ON ig.id_group = gs.id_group
    JOIN industry_table it ON it.id_industry = ig.id_industry
    """)
    records = cur.fetchall()
    columnName = ['ticker', 'comGroupCode', 'organName', 'organShortName', 'industry_name']
    df = pd.DataFrame.from_records(records, columns=columnName)

    data_result = df_price.set_index('ticker').join(df.set_index('ticker'), on='ticker', validate='1:1').reset_index()
    data_result['percent'] = pd.to_numeric((data_result['close'] - data_result['close_pr'])/data_result['close_pr'])
    data_result = data_result.fillna(0)
    def checkTypeUpdown(x):
        if x == 0:
            return '0'
        if x < 0:
            return '-1'
        return '1'
    data_result['type'] = data_result['percent'].apply(checkTypeUpdown)

    fig = px.treemap(data_result, 
                    path=['industry_name','ticker'],
                    values='volume',
                    labels='ticker',
                    color='type',
                    color_discrete_map={'0':'#cd8e1e', '1':'#04c584', '2':'#bc6dd0', '-1':'#d0303d', '-2':'#5499d0','(?)':'#333333'},
                    hover_data=['percent','organName'],
                    )

    fig.data[0].customdata[:,0] = np.where(fig.data[0].customdata[:,0] != '(?)', fig.data[0].customdata[:,0]*100, '(?)')
    fig.data[0].texttemplate = "%{label}<br>%{customdata[0]:.2f}%"

    plot = fig.to_html(full_html=False)
    
    fig_vn30 = px.treemap(data_result, path=['comGroupCode','ticker'],
                 color='type',
                 color_discrete_map={'0':'#cd8e1e', '1':'#04c584', '2':'#bc6dd0', '-1':'#d0303d', '-2':'#5499d0','(?)':'#333333'},
                 hover_data=['percent','organName'],
                 values='volume',
                #  width=2000,
                #  height=1000
                 )
    fig_vn30.data[0].customdata[:,0] = np.where(fig_vn30.data[0].customdata[:,0] != '(?)', fig_vn30.data[0].customdata[:,0]*100, '(?)')
    fig_vn30.data[0].texttemplate = "%{label}<br>%{customdata[0]:.2f}%"
    
    plot_vn30 = fig_vn30.to_html(full_html=False)
    return render_template("/chart/analyst/treemap.html", treemap=plot, plot_vn30 = plot_vn30,selected_timeframe=timeframe)
    
    
if __name__ == "__main__":
    app.run()
