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


def plot_momentum_bounds(cur_date, momentum_data, enter_loc, exit_loc):
    plt.figure(figsize=(12, 8))
    plt.plot(momentum_data['lower_bound'], label='lower bound')
    plt.plot(momentum_data['upper_bound'], label='upper bound')
    plt.plot(momentum_data['market'], label='market data')
    plt.plot(momentum_data['vwap'], label='vwap')

    # plot enter and exits only if they exist 
    if enter_loc != 0:
        plt.axvline(x=enter_loc, color='g', linestyle='--', linewidth=2, label='position entrance')
    if exit_loc != 0:
        plt.axvline(x=exit_loc, color='m', linestyle='--', linewidth=2, label='position exit')

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


def slice_time_series(index, market_df, missing_datetimes):
    new_df = pd.DataFrame(columns=['datetime', 'valid', 'Open', 'High', 'Low', 'Close', 'Volume'])
    start_datetime = market_df['datetime'].iat[index]
    end_datetime = start_datetime + timedelta(minutes=settings.MIN_IN_TRADING_DAY)
    
    temp = start_datetime
    row_index = 0
    while temp < end_datetime:
        if temp in missing_datetimes:
            new_df.loc[row_index, 'datetime'] = temp
            new_df.loc[row_index, 'valid'] = False
        else:
            new_df.loc[row_index, 'datetime'] = temp
            new_df.loc[row_index, 'valid'] = True
            new_df.loc[row_index, 'Open'] = market_df['Open'].iat[index]
            new_df.loc[row_index, 'High'] = market_df['High'].iat[index]
            new_df.loc[row_index, 'Low'] = market_df['Low'].iat[index]
            new_df.loc[row_index, 'Close'] = market_df['Close'].iat[index]
            new_df.loc[row_index, 'Volume'] = market_df['Volume'].iat[index]
            index += 1
        row_index += 1
        temp += timedelta(minutes=1)

    return new_df


# VWAP = SUM_0-t_(average of High, Low, and Close * Volume at minute t) / SUM_0-t_(Volume)
# this function calulates the numerator... 
def get_hlc(row):
    hlc_avg = (row['High'] + row['Low'] + row['Close']) / 3
    return hlc_avg * row['Volume']


def get_momentum_bounds(cur_date, date_list, missing_datetimes, time_series_data, moves_from_open):
    momentum_data = pd.DataFrame(
        columns=['time', 'x', 'x_day_avg', 'lower_bound', 'upper_bound', 'market', 'valid', 'vwap'])
    
    # get the number of days since data collection began
    days_from_start = np.where(date_list == cur_date)[0].item()

    if days_from_start >= settings.NUM_DAYS:
        # get the days of interest for these calculations
        updated_date_list = date_list[days_from_start-settings.NUM_DAYS : days_from_start]

        # make time column
        minutes = pd.date_range(start='09:30:00', end='15:59:00', freq=timedelta(minutes=1)).to_pydatetime()
        momentum_data['time'] = np.array([dt.time() for dt in minutes])

        x_vals = np.zeros(minutes.size)
        pre_avg_vals = np.zeros(minutes.size)

        for d in updated_date_list:
            for index, row, in momentum_data.iterrows():
                cur_datetime = datetime.combine(d, row['time'])
                if cur_datetime not in missing_datetimes:
                    move_index = moves_from_open.index[moves_from_open['datetime'] == cur_datetime]
                    pre_avg_vals[index] += moves_from_open.loc[move_index, 'value'].item()
                    x_vals[index] += 1
       
        avg_vals = pre_avg_vals / x_vals
        momentum_data['x'] = x_vals
        momentum_data['x_day_avg'] = avg_vals
       
        lower_bound_list = np.zeros(minutes.size)
        upper_bound_list = np.zeros(minutes.size)

        cur_open = time_series_data.loc[str(cur_date) + ' 09:30:00-04:00', 'Open']
        prev_close = time_series_data.loc[str(updated_date_list[-1]) + ' 15:59:00-04:00', 'Close']
        
        for index, row in momentum_data.iterrows():
            lower_bound_list[index] = min(cur_open, prev_close) * (1 - settings.VM * row['x_day_avg'])
            upper_bound_list[index] = max(cur_open, prev_close) * (1 + settings.VM * row['x_day_avg'])

        # assign to dataframe
        momentum_data['lower_bound'] = lower_bound_list
        momentum_data['upper_bound'] = upper_bound_list

        main_index = time_series_data.index.get_loc(str(cur_date) + ' 09:30:00-04:00')
        sliced_time_series_data = slice_time_series(main_index, time_series_data, missing_datetimes)

        # assign market to dataframe as well
        momentum_data['market'] = sliced_time_series_data['Open'].to_list()
        momentum_data['valid'] = sliced_time_series_data['valid'].to_list()

        # vwap bounds to improve the results
        hlc_sum = volume_sum = cur_vwap = prev_vwap = 0
        for i, r in sliced_time_series_data.iterrows():
            if r['valid']:
                hlc_sum += get_hlc(r)
                volume_sum += r['Volume']
                cur_vwap = hlc_sum / volume_sum
                momentum_data.loc[i, 'vwap'] = cur_vwap
            else:
                momentum_data.loc[i, 'vwap'] = prev_vwap
            prev_vwap = cur_vwap

    return momentum_data

def get_exit_val(time, trade_type, position, momentum_df):
    for i, r in momentum_df.iterrows():
        if r['time'] > time and r['valid']:
            if ((trade_type == 'short' and r['market'] >= r['lower_bound'])
                or (trade_type == 'long' and r['market'] <= r['upper_bound'])):
                return i, r['market']
    # return close only if market never reverts back to boundaries
    return i, momentum_df['market'].iat[-1]
                

def get_trade_results_row(cur_date, momentum_df, trading_results):
    cur_index = trading_results.loc[trading_results['date'] == cur_date].index
    
    volatility_coef = settings.MAX_NUM_SHARES
    #if settings.VOL_TOGGLE:

    # trade variables
    position = result = enter_time = exit_time = 0
    trade_placed = False
    trade_type = 'NA'
    trade_time = 'NA'

    if not momentum_df.empty:
        for time, row in momentum_df.iterrows():
            if not trade_placed:
                if row['market'] > row['upper_bound'] and time % settings.MIN_STEP == 0:
                    position = row['market']
                    trade_time = row['time']
                    trade_placed = True
                    trade_type = 'long'
                    enter_time = time
                elif row['market'] < row['lower_bound'] and time % settings.MIN_STEP == 0:
                    position = row['market']
                    trade_time = row['time']
                    trade_placed = True
                    trade_type = 'short'
                    enter_time = time
   
        if trade_placed:
            exit_time, exit_val = get_exit_val(trade_time, trade_type, position, momentum_df)
            if trade_type == 'long':
                result = exit_val - position
            elif trade_type == 'short':
                result = position - exit_val

    trading_results.loc[cur_index, 'result'] = result * volatility_coef
    trading_results.loc[cur_index, 'trade_performed'] = trade_placed
    trading_results.loc[cur_index, 'trade_type'] = trade_type
    trading_results.loc[cur_index, 'trade_time'] = trade_time
    return enter_time, exit_time


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
        cur_date_momentum = get_momentum_bounds(cur_date, unique_dates, missing_times, market_df, move_df)
        enter_loc, exit_loc = get_trade_results_row(cur_date, cur_date_momentum, trading_results)

        if settings.PLOT_TOGGLE:
            plot_momentum_bounds(cur_date, cur_date_momentum, enter_loc, exit_loc)

    if settings.TRADING_RESULTS_TOGGLE:
        print(trading_results)
        print(trading_results['result'].sum())


if __name__ == "__main__":
    main()
