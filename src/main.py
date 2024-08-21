import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import yfinance as yf
import pandas_market_calendars as mcal
from datetime import datetime, date, timedelta
import os


# constants
MARKET = 'NYSE'
SYM = 'SPY'
GRANULARITY = '1m'
CREATE_BACKTEST_DATA_RANGE = timedelta(days=29)
UPDATE_LOWER_BOUND = timedelta(0)
UPDATE_UPPER_BOUND = timedelta(days=7)


def is_market_open(date, start_date, end_date):
    nyse = mcal.get_calendar(MARKET)
    open_days = nyse.valid_days(start_date, end_date)
    return date in open_days.date


def create_backtest_data(
    symbol=None,
    test_start=None,
    test_end=None,
    granularity=GRANULARITY
):
    # establish start and end if undefined
    if test_end == None:
        test_end = date.today()
    if test_start == None:
        duration = CREATE_BACKTEST_DATA_RANGE
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

    return final_df


def update_backtest_data(
    symbol=None,
    file_path=None,
    granularity=GRANULARITY
):
    final_df = pd.read_csv(file_path, index_col=0)
    ticker_obj = yf.Ticker(symbol)

    last_date_str = final_df.index[-1]
    last_date = datetime.strptime(last_date_str[:-len("-04:00")],"%Y-%m-%d %H:%M:%S").date()
    now = date.today()

    time_since_update = now - last_date
    
    if UPDATE_LOWER_BOUND < time_since_update < UPDATE_UPPER_BOUND:
        temp_df = ticker_obj.history(interval=granularity, start=last_date + timedelta(days=1), end=now + timedelta(days=1))
        final_df = pd.concat([final_df, temp_df])
        print("result: update successful")
    else: 
        print("result: time_since_update out of valid range.")

    return final_df


def main():

    # get the current dir of main.py
    src_dir = os.path.dirname(os.path.abspath(__file__))

    # check if output directory exists
    output_dir = os.path.join(src_dir, '..\\data')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_name = SYM + '.csv'
    file_path = os.path.join(output_dir, file_name)

    data = pd.DataFrame()

    # call to load data for the symbol
    if not os.path.exists(file_path):
        data = create_backtest_data(symbol=SYM)

    else:
        print("starting update ...")
        data = update_backtest_data(symbol=SYM, file_path=file_path)

    # ensure no duplicates
    data = data.drop_duplicates()

    # ensure csv finishes writing
    try:
        data.to_csv(file_path)
        print(f"file saved to {file_path}")
    except Exception as e:
        print(f"An error occured: {e}")

    # Iterate over stock time series data
    # This is where trading strategy where be called...
    minute_count = day_count = 0
    for date, row in data.iterrows():
        change = row['Close'] - row['Open']
        
        if '9:30' in str(date):
            day_count += 1

        minute_count += 1


if __name__ == "__main__":
    main()
