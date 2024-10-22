# data_manager.py module


# import settings for constant usage
from pandas import DataFrame
import settings


# for module specific packages
from settings import pd, yf, mcal, datetime, date, timedelta, os


def get_plot_dir_path() -> str:
    src_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(src_dir, settings.OUTPUT_DIR)
    plot_dir = os.path.join(output_dir, settings.PLOT_DIR)
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
    return plot_dir


def get_file_path() -> str:
    src_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(src_dir, settings.OUTPUT_DIR)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_name = settings.SYM + '.csv'
    return os.path.join(output_dir, file_name)


# function for use in main.py module
def get_file_as_df() -> DataFrame:
    file_path = get_file_path()
    return pd.read_csv(file_path, index_col=0)


def is_market_open(date: datetime, start_date: datetime, end_date: datetime):
    nyse = mcal.get_calendar(settings.MARKET)
    open_days = nyse.valid_days(start_date, end_date)
    return date in open_days.date


def create_backtest_data(
    symbol=None,
    test_start=None,
    test_end=None,
    granularity=settings.GRANULARITY
) -> DataFrame:
    # establish start and end if undefined
    if test_end == None:
        test_end = date.today()
    if test_start == None:
        duration = settings.CREATE_BACKTEST_DATA_RANGE
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
        symbol: str,
        file_path: str,
        granularity: int=int(settings.GRANULARITY)
):
    ticker_obj = yf.Ticker(symbol)
    final_df = pd.read_csv(file_path, index_col=0)

    last_date_str = final_df.index[-1]
    last_date = datetime.strptime(last_date_str[:-len("-04:00")],"%Y-%m-%d %H:%M:%S")
    now = datetime.now()

    time_since_update = now - last_date

    if settings.UPDATE_LOWER_BOUND < time_since_update < settings.UPDATE_UPPER_BOUND:
        temp_df = ticker_obj.history(interval=granularity, start=last_date, end=now + timedelta(days=1))
        final_df = pd.concat([final_df, temp_df])
        print("result: update successful")
    else: 
        print("result: time_since_update out of valid range.")

    return final_df


def data_manager() -> None:
    data = pd.DataFrame()
    
    file_path = get_file_path()

    # call to load data for the symbol
    if not os.path.exists(file_path):
        data = create_backtest_data(symbol=settings.SYM)
    else:
        data = update_backtest_data(symbol=settings.SYM, file_path=file_path)

    # ensure csv finishes writing
    try:
        data.to_csv(file_path)
    except Exception as e:
        print(f"An error occured: {e}")


# executes functions to update the csv
if __name__ == "__main__":
    data_manager()


