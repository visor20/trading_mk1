# main.py module


# import settings for constant usage
import settings


# import module specific packages
from settings import np, pd, plt, yf, datetime, date, time, timedelta 
from data_manager import get_file_as_df, get_plot_dir_path


def get_datetime(date):
    return datetime.strptime(date[:len('xxxx-xx-xx xx:xx:xx')], '%Y-%m-%d %H:%M:%S')


def clean_up(market_df):
    market_df.reset_index(inplace=True)
   
    # drop duplicates and update the index for the coming operations
    market_df.drop_duplicates(subset=['index', 'Open', 'High', 'Low', 'Close'], keep='first', inplace=True)
    market_df.reset_index(inplace=True)

    datetime_list = []
    for index, row in market_df.iterrows():
        datetime_list.append(get_datetime(row['index']))
    
    market_df.insert(1, 'datetime', datetime_list)
  
    index = 0 
    missing_datetimes = []
    while index < (len(market_df) - 1):
        cur_datetime = market_df.loc[index, 'datetime']
        next_datetime = market_df.loc[index + 1, 'datetime']

        if (cur_datetime.time() != time(15, 59, 0) 
            and next_datetime != cur_datetime + timedelta(minutes=1)):
            # it is rarely more than one minute missing... but just in case
            temp_datetime = cur_datetime + timedelta(minutes=1)
            while temp_datetime < next_datetime:
                missing_datetimes.append(temp_datetime)
                temp_datetime += timedelta(minutes=1)
        index += 1

    # set original datetime string back to the index
    market_df.set_index(keys='index', inplace=True)
    return missing_datetimes
    

def remove_corrupted_day(df, day_of_month):
    dates_to_drop = []
    for date, row in df.iterrows():
        if day_of_month in date:
            dates_to_drop.append(date)
    df.drop(dates_to_drop, inplace=True)


def plot_momentum_bounds(cur_date, momentum_data):
    # get intersecting points 
    upper_x, upper_y = get_intersections(momentum_data['market'], momentum_data['upper_bound'])
    lower_x, lower_y = get_intersections(momentum_data['lower_bound'], momentum_data['market'])

    plt.figure(figsize=(12, 8))
    plt.plot(momentum_data['lower_bound'], label='lower bound')
    plt.plot(momentum_data['upper_bound'], label='upper bound')
    plt.plot(momentum_data['market'], label='market data')

    # points
    plt.scatter(upper_x, upper_y)
    plt.scatter(lower_x, lower_y)

    plt.title(str(cur_date))
    plt.xlabel('minutes from open')
    plt.ylabel('price (USD)')
    plt.legend()
    plt.grid(True)
    file_name = get_plot_dir_path() + '\\plot_' + str(cur_date) + '.png'
    plt.savefig(file_name)
    plt.close()


def get_moves_from_open(df):
    move_df = pd.DataFrame(columns=['datetime', 'date', 'value'])
    cur_open_value = 0

    # put market data in terms of the moves from open
    for date, row in df.iterrows():
        cur_datetime = row['datetime']
        if cur_datetime.time() == time(9, 30, 0):
            cur_open_value = row['Open']
            temp_row = pd.DataFrame({'datetime': [cur_datetime], 'date': [cur_datetime.date()], 'value': [0]})
        else:
            temp_val = abs(row['Close'] / cur_open_value - 1)
            temp_row = pd.DataFrame({'datetime': [cur_datetime], 'date': [cur_datetime.date()], 'value': [temp_val]})
        
        # add to main df
        move_df = pd.concat([move_df, temp_row], ignore_index=True)
    return move_df


def get_intersections(a_list, b_list):
    x = []
    y = []
    already_crossed = False
    for a in enumerate(a_list):
        if a[1] > b_list[a[0]]:
            if not already_crossed and a[0] != 0:
                x.append(a[0])
                y.append(a[1])
                already_crossed = True
        elif already_crossed:
            already_crossed = False
    return x, y


# VWAP = SUM_0-t_(average of High, Low, and Close * Volume at minute t) / SUM_0-t_(Volume)
#def get_vwap(cur_minute, momentum_data):
#    for time, 


def get_momentum_bounds(cur_date, date_list, time_series_data, moves_from_open):
    momentum_data = pd.DataFrame(columns=['time', 'x', 'x_day_avg', 'lower_bound', 'upper_bound', 'market'])
    
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

                if cur_move_series.size != 0:
                    pre_avg_vals[index] += cur_move_series.item()
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

        # is 'Open' Valid (Consider this in future)
        # sliced_time_series_data = time_series_data.iloc[main_index : main_index + settings.MIN_IN_TRADING_DAY]
        # print(sliced_time_series_data)
        tsl = time_series_data['Open'][main_index : main_index + settings.MIN_IN_TRADING_DAY].tolist()
       
        # assign market to dataframe as well
        momentum_data['market'] = tsl

        if settings.PLOT_TOGGLE:
            plot_momentum_bounds(cur_date, momentum_data)

    return momentum_data


def get_trade_results_row(cur_date, momentum_df, trading_results):
    # get current index 
    cur_index = trading_results.loc[trading_results['date'] == cur_date].index
    
    # vol.
    vix_coef = 1

    if settings.VOL_TOGGLE:
        vix_ticker = yf.Ticker(settings.VOL_SYM)
        vix_df = vix_ticker.history(start=cur_date, end=cur_date + timedelta(days=1), period='1d')
        vix_val = vix_df['Open'].iloc[0]
        print(vix_val)
    
        if vix_val <= 10:
            vix_coef *= 5
        elif vix_val <= 20:
            vix_coef *= 2


    # trade variables
    position = 0
    result = 0
    trade_placed = False
    trade_type = 'NA'
    trade_time = 'NA'

    if not momentum_df.empty:
        # loop through and determine trade
        for time, row in momentum_df.iterrows():
            if row['market'] > row['upper_bound'] and not trade_placed:
                position = row['market']
                trade_time = str(row['time'])
                trade_placed = True
                trade_type = 'long'
                result = momentum_df['market'].iat[-1] - position
            elif row['market'] < row['lower_bound'] and not trade_placed:
                position = row['market']
                trade_time = str(row['time'])
                trade_placed = True
                trade_type = 'short'
                result = position - momentum_df['market'].iat[-1]


    trading_results.loc[cur_index, 'result'] = result * vix_coef
    trading_results.loc[cur_index, 'trade_performed'] = trade_placed
    trading_results.loc[cur_index, 'trade_type'] = trade_type
    trading_results.loc[cur_index, 'trade_time'] = trade_time


def main():
    market_df = get_file_as_df()

    # clean up - duplicates removed inplace and missing times returned...
    missing_times = clean_up(market_df)

    move_df = get_moves_from_open(market_df)
    unique_dates = move_df['date'].unique()

    # get momentum data and the results for each day
    trading_results = pd.DataFrame(columns=['date', 'trade_performed', 'trade_type', 'trade_time', 'result'])
    trading_results['date'] = unique_dates

    for cur_date in unique_dates:
        cur_date_momentum = get_momentum_bounds(cur_date, unique_dates, market_df, move_df)
        get_trade_results_row(cur_date, cur_date_momentum, trading_results)

    if settings.TRADING_RESULTS_TOGGLE:
        print(trading_results)
        print(trading_results['result'].sum())


if __name__ == "__main__":
    main()
