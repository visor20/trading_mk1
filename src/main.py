# main.py module


# import settings for constant usage
import settings


# import module specific packages
from settings import np, pd, plt, yf, datetime, date, time, timedelta 
from data_manager import get_file_as_df, get_plot_dir_path


def get_datetime(date):
    return datetime.strptime(date[:len('xxxx-xx-xx xx:xx:xx')], '%Y-%m-%d %H:%M:%S')


def clean_up(market_df):
    # reset index so date string is now a column
    market_df.reset_index(inplace=True)
   
    # drop duplicates and update the index for the coming operations
    market_df.drop_duplicates(subset=['index'], keep='first', inplace=True)
    market_df.reset_index(inplace=True)

    datetime_list = []
    for index, row in market_df.iterrows():
        datetime_list.append(get_datetime(row['index']))
    market_df.insert(1, 'datetime', datetime_list)
  
    old_index = new_index = 0 
    new_df = pd.DataFrame(columns=['datetime', 'valid', 'Open', 'High', 'Low', 'Close', 'Volume'])
    while old_index < len(market_df) - 1:
        cur_datetime = market_df.loc[old_index, 'datetime']
        next_datetime = market_df.loc[old_index + 1, 'datetime']

        new_df.loc[new_index, 'datetime'] = cur_datetime
        new_df.loc[new_index, 'valid'] = True
        new_df.loc[new_index, 'Open'] = market_df.loc[old_index, 'Open']
        new_df.loc[new_index, 'High'] = market_df.loc[old_index, 'High']
        new_df.loc[new_index, 'Low'] = market_df.loc[old_index, 'Low']
        new_df.loc[new_index, 'Close'] = market_df.loc[old_index, 'Close']
        new_df.loc[new_index, 'Volume'] = market_df.loc[old_index, 'Volume']
        
        temp_datetime = cur_datetime + timedelta(minutes=1)
        while (cur_datetime.time() != time(15, 59, 0) 
                and temp_datetime < next_datetime):
            new_index += 1
            new_df.loc[new_index, 'datetime'] = temp_datetime
            new_df.loc[new_index, 'valid'] = False
            temp_datetime += timedelta(minutes=1)

        new_index += 1
        old_index += 1

    # we are going to assume the last value is correct...
    new_df.loc[new_index] = market_df.loc[old_index]
    new_df.loc[new_index, 'valid'] = True
    return new_df


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
    move_df = pd.DataFrame(columns=['datetime', 'valid', 'value'])
    cur_open_value = 0

    # put market data in terms of the moves from open
    for index, row in df.iterrows():
        cur_datetime = row['datetime']
        if row['valid']:
            if cur_datetime.time() == time(9, 30, 0):
                cur_open_value = row['Open']
                temp_row = pd.DataFrame({'datetime': [cur_datetime], 'valid': [True], 'value': [0]})
            else:
                temp_val = abs(row['Close'] / cur_open_value - 1)
                temp_row = pd.DataFrame({'datetime': [cur_datetime], 'valid': [True], 'value': [temp_val]})
        else:
            temp_row = pd.DataFrame({'datetime': [cur_datetime], 'valid': [False], 'value': [0]})

        move_df = pd.concat([move_df, temp_row], ignore_index=True)
    return move_df


# VWAP = SUM_0-t_(average of High, Low, and Close * Volume at minute t) / SUM_0-t_(Volume)
def get_hlc(row):
    hlc_avg = (row['High'] + row['Low'] + row['Close']) / 3
    return hlc_avg * row['Volume']


def get_momentum_bounds(cur_date, date_list, time_series_data, moves_from_open):
    momentum_data = pd.DataFrame(
        columns=['time', 'x', 'x_day_avg', 'lower_bound', 'upper_bound', 'market', 'valid', 'vwap'])
    
    # get the number of days since data collection began
    days_from_start = np.where(np.array(date_list) == cur_date)[0].item()

    if days_from_start >= settings.NUM_DAYS:
        # get the days of interest for these calculations
        updated_date_list = date_list[days_from_start-settings.NUM_DAYS : days_from_start]

        # all columns (first np.arrays) are based on minutes size
        minutes = pd.date_range(start='09:30:00', end='15:59:00', freq=timedelta(minutes=1)).to_pydatetime()
        momentum_data['time'] = np.array([dt.time() for dt in minutes])
        x_vals = np.zeros(minutes.size)
        pre_avg_vals = np.zeros(minutes.size)
        lower_bound_list = np.zeros(minutes.size)
        upper_bound_list = np.zeros(minutes.size)

        for d in updated_date_list:
            for index, row, in momentum_data.iterrows():
                move_index = moves_from_open.index[moves_from_open['datetime'] == datetime.combine(d, row['time'])]
                if moves_from_open.loc[move_index, 'valid'].item():
                    pre_avg_vals[index] += moves_from_open.loc[move_index, 'value'].item()
                    x_vals[index] += 1
       
        momentum_data['x'] = x_vals
        momentum_data['x_day_avg'] = pre_avg_vals / x_vals

        main_index = time_series_data.index[time_series_data['datetime'] == datetime.combine(cur_date, time(9, 30, 0))].item()
        cur_open = time_series_data.loc[main_index, 'Open']
        prev_close = time_series_data.loc[main_index - 1, 'Close']
        sliced_time_series_data = time_series_data[main_index : main_index + settings.MIN_IN_TRADING_DAY] 
        sliced_time_series_data.reset_index(inplace=True)

        for index, row in momentum_data.iterrows():
            lower_bound_list[index] = min(cur_open, prev_close) * (1 - settings.VM * row['x_day_avg'])
            upper_bound_list[index] = max(cur_open, prev_close) * (1 + settings.VM * row['x_day_avg'])

        # assign to dataframe
        momentum_data['lower_bound'] = lower_bound_list
        momentum_data['upper_bound'] = upper_bound_list
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

    # duplicates removed and missing times marked as invalid
    clean_market_df = clean_up(market_df)

    move_df = get_moves_from_open(clean_market_df)
    unique_dates = sorted(set(dt.date() for dt in move_df['datetime']))

    # get momentum data and the results for each day
    trading_results = pd.DataFrame(columns=['date', 'trade_performed', 'trade_type', 'trade_time', 'result'])
    trading_results['date'] = unique_dates

    for cur_date in unique_dates:
        cur_date_momentum = get_momentum_bounds(cur_date, unique_dates, clean_market_df, move_df)
        enter_loc, exit_loc = get_trade_results_row(cur_date, cur_date_momentum, trading_results)

        if settings.PLOT_TOGGLE:
            plot_momentum_bounds(cur_date, cur_date_momentum, enter_loc, exit_loc)

    if settings.TRADING_RESULTS_TOGGLE:
        print(trading_results)
        print(trading_results['result'].sum())


if __name__ == "__main__":
    main()
