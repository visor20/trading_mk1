# settings.py module


# 3rd party packages
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
import pandas_market_calendars as mcal
from datetime import datetime, date, time, timedelta
import os


# market constants
MARKET = 'NYSE'
SYM = 'SPY'

# number of days the average move from open bounds are based on
NUM_DAYS = 14
# times at which trades are allowed to be placed (10 -> 9:40, 9:50, etc).
MIN_STEP = 30
# widens the bounds... 
VM = 1.0
# will be incorporated into vol. calculations
MAX_NUM_SHARES = 1

OUTPUT_DIR = '..\\data'
PLOT_DIR = '.\\plots'
GRANULARITY = '1m'
CREATE_BACKTEST_DATA_RANGE = timedelta(days=29)
UPDATE_LOWER_BOUND = timedelta(0)
UPDATE_UPPER_BOUND = timedelta(days=7)
MIN_IN_TRADING_DAY = 390
PLOT_TOGGLE = True
VOL_TOGGLE = False
TRADING_RESULTS_TOGGLE = True
