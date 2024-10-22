# class for trading results 

from settings import pd

class CurTrades:
    def __init__(self, is_active: bool) -> None:
        self.num_trades = 0
        self.is_active = is_active
        self.types = []
        self.positions = []
        self.enter_i_vals = []
        self.exit_i_vals = []
        self.results = []

    def add_trade(self, market_val: float, type_val: str, enter_i_val: int) -> None:
        self.is_active = True
        self.num_trades += 1

        self.positions.append(market_val)
        self.types.append(type_val)
        self.enter_i_vals.append(enter_i_val)
    
    # only to be called after add trade
    def is_long(self) -> bool:
        return self.types[-1] == 'long'

    def get_cur_position(self) -> float:
        return self.positions[-1]

    def end_trade(self, result: float, exit_i_val: int):
        self.is_active = False
        self.exit_i_vals.append(exit_i_val)
        self.results.append(result)

    def check_exit(self, df: pd.DataFrame, i: int) -> None:
        if len(self.exit_i_vals) == self.num_trades - 1:
            self.exit_i_vals.append(i)
            if self.is_long():
                self.results.append(df.loc[i, 'market'] - self.get_cur_position())
            else:
                self.results.append(self.get_cur_position() - df.loc[i, 'market'])
