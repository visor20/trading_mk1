# class for trading results 

from settings import np, pd

class CurTrades:
    def __init__(self, is_active):
        self.num_trades = 0
        self.is_active = is_active
        self.types = []
        self.positions = []
        self.enter_i_vals = []
        self.exit_i_vals = []
        self.results = []

    def add_trade(self, market_val, type_val, enter_i_val):
        self.is_active = True
        self.num_trades += 1

        self.positions.append(market_val)
        self.types.append(type_val)
        self.enter_i_vals.append(enter_i_val)
    
    # only to be called after add trade
    def is_long(self):
        return self.types[-1] == 'long'

    def get_cur_position(self):
        return self.positions[-1]

    def end_trade(self, result, exit_i_val):
        self.is_active = False
        self.exit_i_vals.append(exit_i_val)
        self.results.append(result)

    def check_exit(self, df, i):
        if len(self.exit_i_vals) == self.num_trades - 1:
            self.exit_i_vals.append(i)
            if self.is_long():
                self.results.append(df.loc[i, 'market'] - self.get_cur_position())
            else:
                self.results.append(self.get_cur_position() - df.loc[i, 'market'])
