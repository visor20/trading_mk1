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
    for enter_val in enter_loc:
        plt.axvline(x=enter_val, color='g', linestyle='--', linewidth=1)
    for exit_val in exit_loc:
        plt.axvline(x=exit_val, color='m', linestyle='--', linewidth=1)

    plt.title(str(cur_date))
    plt.xlabel('minutes from open')
    plt.ylabel('price (USD)')
    plt.legend()
    plt.grid(visible=True, alpha=0.25)
    file_name = get_plot_dir_path() + '\\plot_' + str(cur_date) + '.png'
    plt.savefig(file_name)
    plt.close()


def get_moves_from_open(df):
    move_df = pd.DataFrame()
    cur_open_value = 0

    for i, r in df.iterrows():
        cur_datetime = r['datetime']
        if r['valid']:
            if cur_datetime.time() == time(9, 30, 0):
                cur_open_value = r['Open']
                temp_row = pd.DataFrame({'datetime': [cur_datetime], 'valid': [True], 'value': [0]})
            else:
                temp_val = abs(r['Close'] / cur_open_value - 1)
                temp_row = pd.DataFrame({'datetime': [cur_datetime], 'valid': [True], 'value': [temp_val]})
        else:
            temp_row = pd.DataFrame({'datetime': [cur_datetime], 'valid': [False], 'value': [0]})
        
        # ensures pd.concat is not used on an empty df (which is depreciated by pd)
        if i == 0:
            move_df = temp_row
        else:
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
    position_list = []
    result_list = []
    trade_type_list = []
    enter_index_list = []
    exit_index_list = []
    trade_active = False

    if not momentum_df.empty:
        for i, r in momentum_df.iterrows():
            if (not trade_active 
                and i % settings.MIN_STEP == 0
                and r['valid']):
                if r['market'] > r['upper_bound']:
                    position_list.append(r['market'])
                    trade_type_list.append('long')
                    enter_index_list.append(i)
                    trade_active = True
                elif r['market'] < r['lower_bound']: 
                    position_list.append(r['market'])
                    trade_type_list.append('short')
                    enter_index_list.append(i)
                    trade_active = True
            elif (trade_active 
                  and trade_type_list[-1] == 'long'
                  and r['valid']
                  and r['market'] <= r['upper_bound']):
                    result_list.append(r['market'] - position_list[-1])
                    exit_index_list.append(i)
                    trade_active = False
            elif (trade_active
                  and trade_type_list[-1] == 'short'
                  and r['valid']
                  and r['market'] >= r['lower_bound']):
                    result_list.append(position_list[-1] - r['market'])
                    exit_index_list.append(i)
                    trade_active = False


    # if exit is at close
    if len(exit_index_list) == len(enter_index_list) - 1:
        exit_index_list.append(i)
        if trade_type_list[-1] == 'long':
            result_list.append(momentum_df.loc[i, 'market'] - position_list[-1])
        else:
            result_list.append(position_list[-1] - momentum_df.loc[i, 'market'])

    trading_results.loc[cur_index, 'results'] = sum(result_list) * volatility_coef
    trading_results.loc[cur_index, 'num_trades'] = len(position_list)

    return enter_index_list, exit_index_list


def main():
    market_df = get_file_as_df()

    # duplicates removed and missing times marked as invalid
    clean_market_df = clean_up(market_df)

    move_df = get_moves_from_open(clean_market_df)
    unique_dates = sorted(set(dt.date() for dt in move_df['datetime']))

    # get momentum data and the results for each day
    trading_results = pd.DataFrame(columns=['date', 'num_trades', 'results'])
    trading_results['date'] = unique_dates

    for cur_date in unique_dates:
        cur_date_momentum = get_momentum_bounds(cur_date, unique_dates, clean_market_df, move_df)
        enter_loc, exit_loc = get_trade_results_row(cur_date, cur_date_momentum, trading_results)

        if settings.PLOT_TOGGLE:
            plot_momentum_bounds(cur_date, cur_date_momentum, enter_loc, exit_loc)

    if settings.TRADING_RESULTS_TOGGLE:
        print(trading_results)
        print(trading_results['results'].sum())


if __name__ == "__main__":
    main()
