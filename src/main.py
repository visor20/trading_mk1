# main.py module


# import settings for constant usage
import settings


# import module specific packages
from settings import np, pd, plt, yf, datetime, date, time, timedelta 
from data_manager import get_file_as_df, get_plot_dir_path
from volatility import get_annualized_volatility, get_avg_return, get_unique_dates
from trade import CurTrades

def get_datetime(date):
    return datetime.strptime(date[:len('xxxx-xx-xx xx:xx:xx')], '%Y-%m-%d %H:%M:%S')


def clean_up(market_df):
    market_df.reset_index(inplace=True)
    market_df.drop_duplicates(subset=['index'], keep='first', inplace=True)
    market_df.reset_index(inplace=True)

    datetime_list = []
    for index, row in market_df.iterrows():
        datetime_list.append(get_datetime(row['index']))
    market_df.insert(1, 'datetime', datetime_list)
  
    old_index, new_index = 0, 0
    new_df = pd.DataFrame(columns=['datetime', 'valid', 'Open', 'High', 'Low', 'Close', 'Volume'])
    while old_index < (len(market_df) - 1):
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


def plot_momentum_bounds(cur_date, momentum_data, cur_trades):
    plt.figure(figsize=(12, 8))
    plt.plot(momentum_data['lower_bound'], label='lower bound')
    plt.plot(momentum_data['upper_bound'], label='upper bound')
    plt.plot(momentum_data['market'], label='market data')
    plt.plot(momentum_data['vwap'], label='vwap')

    # plot enter and exits only if they exist 
    for enter_val in cur_trades.enter_i_vals:
        plt.axvline(x=enter_val, color='g', linestyle='--', linewidth=1)
    for exit_val in cur_trades.exit_i_vals:
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


"""
VWAP = SUM_0-t_(average of High, Low, and Close * Volume at minute t) / SUM_0-t_(Volume)
det_hlc simply returns the numerator to be used within get_vwap().
"""
def get_hlc(row):
    hlc_avg = (row['High'] + row['Low'] + row['Close']) / 3
    return hlc_avg * row['Volume']


def get_vwap(stsd, md):
    hlc_sum, volume_sum, cur_vwap, prev_vwap = 0, 0, 0, 0
    for i, r in stsd.iterrows():
        if r['valid']:
            hlc_sum += get_hlc(r)
            volume_sum += r['Volume']
            cur_vwap = hlc_sum / volume_sum
            md.loc[i, 'vwap'] = cur_vwap
        else:
            md.loc[i, 'vwap'] = prev_vwap
        prev_vwap = cur_vwap


def get_momentum_bounds(cur_date, date_list, time_series_data, moves_from_open):
    momentum_data = pd.DataFrame(
        columns=['time', 'x', 'x_day_avg', 'lower_bound', 'upper_bound', 'market', 'valid', 'vwap'])

    # get the number of days since data collection began
    days_from_start = np.where(np.array(date_list) == cur_date)[0].item()

    if days_from_start >= settings.NUM_DAYS:
        updated_date_list = date_list[days_from_start-settings.NUM_DAYS : days_from_start]
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
            lower_bound_list[index] = min(cur_open, prev_close) * (1 - row['x_day_avg'])
            upper_bound_list[index] = max(cur_open, prev_close) * (1 + row['x_day_avg'])

        # assign to dataframe
        momentum_data['lower_bound'] = lower_bound_list
        momentum_data['upper_bound'] = upper_bound_list
        momentum_data['market'] = sliced_time_series_data['Open'].to_list()
        momentum_data['valid'] = sliced_time_series_data['valid'].to_list()

        # vwap can be used as another bound to improve exit timing...
        get_vwap(sliced_time_series_data, momentum_data)
    return momentum_data


def get_trade_results_row(cur_date, momentum_df, time_series_df, trading_results):
    cur_index = trading_results.loc[trading_results['date'] == cur_date].index
    
    volatility_coef = 1
    if settings.VOL_TOGGLE:
        volatility = get_annualized_volatility(cur_date, time_series_df, settings.NUM_DAYS)
        trading_results.loc[cur_index, 'volatility'] = volatility

        if volatility <= 15.0:
            volatility_coef = settings.MAX_NUM_SHARES
        elif volatility <= 20.0:
            volatility_coef = settings.MAX_NUM_SHARES / 2

    trades = CurTrades(is_active=False)
    if not momentum_df.empty:
        for i, r in momentum_df.iterrows():
            if r['valid']:
                if not trades.is_active:
                    if i % settings.MIN_STEP == 0:
                        if r['market'] > r['upper_bound']:
                            trades.add_trade(r['market'], 'long', i)
                        elif r['market'] < r['lower_bound']: 
                            trades.add_trade(r['market'], 'short', i)
                elif trades.num_trades > 0:
                    if trades.is_long():
                        if r['market'] <= r['upper_bound'] or r['market'] <= r['vwap']:
                            result = r['market'] - trades.get_cur_position()
                            trades.end_trade(result, i)
                    else:
                        if r['market'] >= r['lower_bound'] or r['market'] >= r['vwap']:
                            result = trades.get_cur_position() - r['market']
                            trades.end_trade(result, i)

    # if exit is at close, we need to add this to results...
    trades.check_exit(momentum_df, i)
    trading_results.loc[cur_index, 'results'] = sum(trades.results) * volatility_coef
    trading_results.loc[cur_index, 'num_trades'] = trades.num_trades

    return trades


def main():
    market_df = get_file_as_df()

    # duplicates removed and missing times marked as invalid
    clean_market_df = clean_up(market_df)
    move_df = get_moves_from_open(clean_market_df)
    unique_dates = get_unique_dates(move_df)

    # get momentum data and the results for each day
    trading_results = pd.DataFrame(columns=['date', 'volatility', 'num_trades', 'results'])
    trading_results['date'] = unique_dates

    for index, cur_date in enumerate(unique_dates):
        # + 1 days accounts for the volatility calculation
        if index >= settings.NUM_DAYS + 1:
            cur_date_momentum = get_momentum_bounds(cur_date, unique_dates, clean_market_df, move_df)
            cur_trades = get_trade_results_row(cur_date, cur_date_momentum, clean_market_df, trading_results)

            if settings.PLOT_TOGGLE:
                plot_momentum_bounds(cur_date, cur_date_momentum, cur_trades)

    if settings.TRADING_RESULTS_TOGGLE:
        # again, the + 1 accounts for the extra day needed for volatility
        sliced_trading_results = trading_results[settings.NUM_DAYS + 1:]
        print(sliced_trading_results)
        print(sliced_trading_results['results'].sum())


if __name__ == "__main__":
    main()
