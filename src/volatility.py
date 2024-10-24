# module for volatility calculations

# import settings for constant usage
from pandas import DataFrame
import settings


# import module specific packages
from settings import np, pd, datetime, time

def get_unique_dates(df: pd.DataFrame) -> list[datetime]:
    return sorted(set(dt.date() for dt in df['datetime']))


def get_simple_return(n: int, d: int) -> float:
    return ((float(n) / d) - 1)


def get_log_return(n: int, d: int) -> float:
    return np.log(float(n) / d)


# gets the 'num_days' average NOT INCLUDING cur_day
# time_series contains a 'datetime' column
def get_avg_return(cur_day: datetime, df: DataFrame, num_days: int) -> list[float]:
    unique_dates = np.array(get_unique_dates(df))
    days_from_start = np.where(unique_dates == cur_day)[0].item()
    days_of_interest = unique_dates[days_from_start - (num_days + 1) : days_from_start]

    return_vals = []
    for i, d in enumerate(days_of_interest[1:], start=1):
        close_dt = datetime.combine(d, time(15, 59, 0))
        p_close_dt = datetime.combine(days_of_interest[i-1], time(15, 59, 0))
        close_today = df.loc[df['datetime'] == close_dt, 'Close'].values[0]
        close_yesterday = df.loc[df['datetime'] == p_close_dt, 'Close'].values[0]

        cur_return = float(get_log_return(close_today, close_yesterday))
        return_vals.append(cur_return)

    # avg_return = np.mean(return_vals)
    return return_vals


def get_volatility(cur_day: datetime, df: DataFrame, num_days: int):
    return_vals = get_avg_return(cur_day, df, num_days)
    return np.std(return_vals, ddof = 1)


# wrapper for get_volatility...
def get_annualized_volatility(cur_day: datetime, df: DataFrame, num_days: int) -> float:
    return get_volatility(cur_day, df, num_days) * np.sqrt(settings.DAYS_IN_TRADING_YEAR) * 100


