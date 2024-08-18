import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
import pandas_market_calendars as mcal
from datetime import datetime, date, timedelta

def is_market_open(date, start_date, end_date):
    nyse = mcal.get_calendar('NYSE')
    open_days = nyse.valid_days(start_date, end_date)
    return date in open_days.date

def load_backtest_data(
    symbol=None,
    test_start=None,
    test_end=None,
    granularity="1m"
):
    # establish start and end if undefined
    if test_end == None:
        test_end = date.today()
    if test_start == None:
        duration = timedelta(days=29)
        test_start = test_end - duration
     
    # get yfinance ticker object to :wqextract data
    ticker_obj = yf.Ticker(symbol)

    # calculate first day so we do not start with empy dataframe
    final_df = pd.DataFrame()
    cur_day = test_start

    # now increment until the end
    while cur_day < test_end:
        if is_market_open(cur_day, test_start, test_end):
            temp_df = ticker_obj.history(interval=granularity, start=cur_day, end=(cur_day + timedelta(days=1)))
            final_df = pd.concat([final_df, temp_df])
        cur_day += timedelta(days=1)

    final_df = final_df.sort_index()
    return final_df


def main(symbol):
    data = load_backtest_data(symbol=symbol)
    plt.figure()
    plt.plot(data['Close'])
    plt.show()


if __name__ == "__main__":
    main('SPY')
