# main.py module


# import settings for constant usage
import settings


# import module specific packages
from settings import np, pd, plt, yf, datetime, date, timedelta 


def remove_corrupted_day(df, day_of_month):
    dates_to_drop = []
    for date, row in df.iterrows():
        if day_of_month in date:
            dates_to_drop.append(date)
    df.drop(dates_to_drop, inplace=True)


# returns a df
def get_move_from_open(df):
    move_df = pd.DataFrame(columns=['date', 'value'])
    cur_open_value = 0
    for date, row in df.iterrows():
        if '9:30:00' in str(date):
            cur_open_value = row['Open']
            temp_row = pd.DataFrame({'date': [date], 'value': [0]})
            move_df = pd.concat([move_df, temp_row], ignore_index=True)
        else:
            cur_close = row['Close']
            temp_val = abs(cur_close / cur_open_value - 1)
            temp_row = pd.DataFrame({'date': [date], 'value': [temp_val]})
            move_df = pd.concat([move_df, temp_row], ignore_index=True)

    return move_df


def get_momentum_bounds(cur_date, time_series_data, moves_from_open):
    momentum_data = pd.DataFrame(columns=['time', '14_day_avg', 'lower_bound', 'upper_bound'])
  
    list_of_days = []
    new_date = cur_date + ' 09:30:00-04:00'
    num_rows = len(moves_from_open)
    main_index = days_from_start = 0

    # get the number of days from when data collection started
    while main_index < num_rows:
        if '09:30:00' in str(moves_from_open.loc[main_index, 'date']):
            list_of_days.append(moves_from_open.loc[main_index, 'date'][:len('xxxx-xx-xx')])
            days_from_start += 1
        if moves_from_open.loc[main_index, 'date'] == new_date:
            break
        main_index += 1
    
    # if we have at least 14 days of data + current day, we can perform momentum calculations
    if days_from_start >= 15:
        # get the days of interest for these calculations
        list_of_days = list_of_days[days_from_start-15:days_from_start-1]

        # make time column
        minutes = pd.date_range(start='09:30:00', end='15:59:00', freq=timedelta(minutes=1)).strftime('%H:%M:%S')
        momentum_data['time'] = minutes

        # need to fix so I am not modifying something I am iterating over...
        pre_avg_vals = np.zeros(minutes.size)
        for d in list_of_days:
            for index, row, in momentum_data.iterrows():
                str_key = d + ' ' + row['time'] + '-04:00'
                move_index = moves_from_open.index[moves_from_open['date'] == str_key]
                cur_move_series = moves_from_open.loc[move_index, 'value']
                if cur_move_series.size == 1:
                    cur_move_val = cur_move_series.item()
                    pre_avg_vals[index] += cur_move_val
                else: 
                    print("error at: " + str_key)
       
        avg_vals = pre_avg_vals / 14
        momentum_data['14_day_avg'] = avg_vals
       
        lower_bound_list = np.zeros(minutes.size)
        upper_bound_list = np.zeros(minutes.size)
        cur_open = time_series_data.loc[new_date, 'Open']
        prev_close = time_series_data.loc[str(list_of_days[-1]) + ' 15:59:00-04:00', 'Close']
        for index, row in momentum_data.iterrows():
            lower_bound_list[index] = min(cur_open, prev_close) * (1 - row['14_day_avg'])
            upper_bound_list[index] = max(cur_open, prev_close) * (1 + row['14_day_avg'])

        # assign to dataframe
        momentum_data['lower_bound'] = lower_bound_list
        momentum_data['upper_bound'] = upper_bound_list
        tsl = time_series_data['Open'][main_index:main_index + settings.MIN_IN_TRADING_DAY - 1].tolist()
        
        """
        plt.figure(figsize=(10, 6))  # Optional: set the size of the plot
        #plt.plot(momentum_data['14_day_avg'], label='14_day_avg')
        plt.plot(momentum_data['lower_bound'], label='lower')
        plt.plot(momentum_data['upper_bound'], label='upper')
        plt.plot(tsl, label='market')
        plt.title('bounds')
        #plt.xlabel('')
        #plt.ylabel('Y-axis Label')
        plt.legend()
        plt.grid(True)  # Optional: add grid
        plt.show()
        """


def main():
    #move_df = get_move_from_open(data)
    #get_momentum_bounds('2024-08-28', data, move_df)


if __name__ == "__main__":
    main()
