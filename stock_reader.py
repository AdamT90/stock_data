import pandas_datareader as pdr
import pandas_datareader.nasdaq_trader as nsqt
import pandas_datareader.data as web
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import plotly.express as px
import pandas
import requests_cache
import datetime
import quandl
from quandl.errors.quandl_error import ForbiddenError

EXP_PERIOD = datetime.timedelta(hours=1)
NSQ_DF_FILENAME = 'nsq_symbols.csv'
INIT_FIG = None
quandl.ApiConfig.api_key = "oPfSs9ZofJxK5eXbYQTu"


def load_nsq_symbols_df():
    return pandas.read_csv(NSQ_DF_FILENAME)


def get_nsq_symbols_df():
    df = nsqt.get_nasdaq_symbols()
    df.to_csv(NSQ_DF_FILENAME)
    return df


def get_nsq_symbols_list(df):
    return list(df['NASDAQ Symbol'].unique())


def get_stock_data(index_name, mode='pdr'):
    if mode != 'pdr':
        try:
            return quandl.get(index_name)
        except ForbiddenError:
            pass
    session = requests_cache.CachedSession(cache_name=index_name + '_cache', backend='sqlite', expire_after=EXP_PERIOD)
    return web.DataReader(index_name, 'stooq', session=session)


def init_data():
    return get_nsq_symbols_list(get_nsq_symbols_df())


def initial_figure(init_fig=None):
    if init_fig is not None:
        return init_fig
    df = get_stock_data("GOOG")
    df = df.reset_index()
    init_fig = px.line(df, x="Date", y='Close', title='GOOG stock values')
    return init_fig


NSQ_LIST = init_data()
app = dash.Dash()
app.layout = html.Div([
    html.H1(id='header', title='STOCK DISPLAY'),
    html.Div(dcc.Dropdown(id='stock-select',
                          options=[{'label': stock_name, 'value': stock_name} for stock_name in NSQ_LIST],
                          placeholder='select stocks',
                          multi=True,
                          value=None)),
    html.Div(dcc.DatePickerRange(
        id='date-picker',
        min_date_allowed=datetime.date(2016, 1, 1),
        max_date_allowed=datetime.date.today(),
        initial_visible_month=datetime.date.today(),
    )),
    html.Div(html.Button('Submit', id='click', n_clicks=0)),
    html.Div(id='debug', children="default"),
    html.Div(dcc.Graph(id='stock-graph', figure=initial_figure(INIT_FIG))),
    html.Div(dcc.Graph(id='cprod-graph', figure=initial_figure(INIT_FIG))),
    html.Div(dcc.Graph(id='daily-returns-graph', figure=initial_figure(INIT_FIG))),
    html.Div(dcc.Graph(id='daily-returns-hist', figure=initial_figure(INIT_FIG)))
])


@app.callback([Output(component_id='stock-graph', component_property='figure'),
               Output(component_id='cprod-graph', component_property='figure'),
               Output(component_id='daily-returns-graph', component_property='figure'),
               Output(component_id='daily-returns-hist', component_property='figure')],
              Input(component_id='click', component_property='n_clicks'),
              [State(component_id='stock-select', component_property='value'),
               State(component_id='date-picker', component_property='start_date'),
               State(component_id='date-picker', component_property='end_date')])
def update_graph(_, symbols_list, start_date, end_date):
    if symbols_list is None:
        return initial_figure(INIT_FIG)
    traces_s = []
    traces_c = []
    traces_d = []
    traces_h = []
    for symb in symbols_list:
        df = get_stock_data(symb).reset_index()
        df = df.loc[(df["Date"] >= start_date) & (df["Date"] < end_date)]
        traces_s.append(go.Scatter(x=df["Date"], y=df["Close"], name=symb))
        traces_c.append(go.Scatter(x=df["Date"], y=(1+df["Close"].pct_change(1)).cumprod(), name=symb))
        traces_d.append(go.Scatter(x=df["Date"], y=df["Close"].pct_change(1), name=symb))
        traces_h.append(go.Histogram(x=df["Close"].pct_change(1), name=symb))
    fig_stock = dict(data=traces_s, layout=go.Layout(title='{}'.format([symb for symb in symbols_list]), xaxis_title="Date",
                                             yaxis_title="Value[USD]"))
    fig_cp = dict(data=traces_c, layout=go.Layout(title='{}'.format([symb for symb in symbols_list]), xaxis_title="Date",
                                             yaxis_title="Cumulative Return [%]"))
    fig_dret = dict(data=traces_d, layout=go.Layout(title='DAILY{}'.format([symb for symb in symbols_list]), xaxis_title="Date",
                                             yaxis_title="Daily Return[%]"))
    fig_h = dict(data=traces_h, layout=go.Layout(title='HISTOGRAM {}'.format([symb for symb in symbols_list]),
                                             xaxis_title="Daily Return[%]"))
    return fig_stock, fig_cp, fig_dret, fig_h


if __name__ == '__main__':
    INIT_FIG = initial_figure()
    app.run_server(debug=True)
