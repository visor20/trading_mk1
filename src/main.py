# main.py module


# import settings for constant usage
import settings


# import module specific packages
from settings import np, pd, plt, yf, datetime, date, time, timedelta 
from data_manager import get_file_as_df, get_plot_dir_path


def get_datetime(date):
    return datetime.strptime(date[:len('xxxx-xx-xx xx:xx:xx')], '%Y-%m-%d %H:%M:%S')


def remove_corrupted_day(df, day_of_month):
    dates_to_drop = []
    for date, row in df.iterrows():
        if day_of_month in date:
            dates_to_drop.append(date)
    df.drop(dates_to_drop, inplace=True)


def plot_momentum_bounds(cur_date, momentum_data, tsl):
    plt.figure(figsize=(10, 6))
    plt.plot(momentum_data['lower_bound'], label='lower')
    plt.plot(momentum_data['upper_bound'], label='upper')
    plt.plot(tsl, label='market')
    plt.title(str(cur_date))
    plt.legend()
    plt.grid(True)
    
    file_name = get_plot_dir_path() + '\\plot_' + str(cur_date) + '.png'
    plt.savefig(file_name)
    plt.close()


"""
def clean_up_df(df):
    index = 0
    prev_time = df.loc[index, 'datetime'] - timedelta(minutes=1)

    while index < len(df):
        cur_time = df.loc[index, 'datetime']
        if cur_time.time() != time(9, 30, 0) and cur_time != (prev_time + timedelta(minutes=1)):
            print(str(index) + ': ' + str(df.loc[index, 'datetime']))
        prev_time = cur_time
        index += 1
"""


def get_moves_from_open(df):
    move_df = pd.DataFrame(columns=['datetime', 'date', 'value'])
    cur_open_value = 0

    # put market data in terms of the moves from open
    for date, row in df.iterrows():
        cur_datetime = get_datetime(date)

        if cur_datetime.time() == time(9, 30, 0):
            cur_open_value = row['Open']
            temp_row = pd.DataFrame({'datetime': [cur_datetime], 'date': [cur_datetime.date()], 'value': [0]})
        else:
            temp_val = abs(row['Close'] / cur_open_value - 1)
            temp_row = pd.DataFrame({'datetime': [cur_datetime], 'date': [cur_datetime.date()], 'value': [temp_val]})
        
        # add to main df
        move_df = pd.concat([move_df, temp_row], ignore_index=True)

    return move_df


def get_momentum_bounds(cur_date, date_list, time_series_data, moves_from_open):
    momentum_data = pd.DataFrame(columns=['time', 'x', 'x_day_avg', 'lower_bound', 'upper_bound'])
    
    # get the number of days since data collection began
    days_from_start = np.where(date_list == cur_date)[0].item()

    # if we have at least 14 days of data + current day, we can perform momentum calculations
    if days_from_start >= settings.NUM_DAYS:
        # get the days of interest for these calculations
        updated_date_list = date_list[days_from_start-settings.NUM_DAYS:days_from_start-1]

        # make time column
        minutes = pd.date_range(start='09:30:00', end='15:59:00', freq=timedelta(minutes=1)).to_pydatetime()
        momentum_data['time'] = np.array([dt.time() for dt in minutes])

        x_vals = np.zeros(minutes.size)
        pre_avg_vals = np.zeros(minutes.size)

        for d in updated_date_list:
            for index, row, in momentum_data.iterrows():
                cur_datetime = datetime.combine(d, row['time'])
                move_index = moves_from_open.index[moves_from_open['datetime'] == cur_datetime]
                cur_move_series = moves_from_open.loc[move_index, 'value']
                if cur_move_series.size == 1:
                    cur_move_val = cur_move_series.item()
                    pre_avg_vals[index] += cur_move_val
                    x_vals[index] += 1
       
        avg_vals = pre_avg_vals / x_vals
        momentum_data['x'] = x_vals
        momentum_data['x_day_avg'] = avg_vals
       
        lower_bound_list = np.zeros(minutes.size)
        upper_bound_list = np.zeros(minutes.size)

        cur_open = time_series_data.loc[str(cur_date) + ' 09:30:00-04:00', 'Open']
        prev_close = time_series_data.loc[str(updated_date_list[-1]) + ' 15:59:00-04:00', 'Close']

        for index, row in momentum_data.iterrows():
            lower_bound_list[index] = min(cur_open, prev_close) * (1 - row['x_day_avg'])
            upper_bound_list[index] = max(cur_open, prev_close) * (1 + row['x_day_avg'])

        # assign to dataframe
        momentum_data['lower_bound'] = lower_bound_list
        momentum_data['upper_bound'] = upper_bound_list

        main_index = time_series_data.index.get_loc(str(cur_date) + ' 09:30:00-04:00')
        tsl = time_series_data['Open'][main_index:main_index + settings.MIN_IN_TRADING_DAY - 1].tolist()

        if settings.PLOT_TOGGLE:
            plot_momentum_bounds(cur_date, momentum_data, tsl)


def main():
    market_df = get_file_as_df()
    move_df = get_moves_from_open(market_df)
    unique_dates = move_df['date'].unique()

    for cur_date in unique_dates:
        get_momentum_bounds(cur_date, unique_dates, market_df, move_df)


if __name__ == "__main__":
    main()
