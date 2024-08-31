# settings.py module


# 3rd party packages
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
import pandas_market_calendars as mcal
from datetime import datetime, date, time, timedelta
import os


# constants
MARKET = 'NYSE'
SYM = 'SPY'
NUM_DAYS = 14
OUTPUT_DIR = '..\\data'
PLOT_DIR = '.\\plots'
GRANULARITY = '1m'
CREATE_BACKTEST_DATA_RANGE = timedelta(days=29)
UPDATE_LOWER_BOUND = timedelta(0)
UPDATE_UPPER_BOUND = timedelta(days=7)
MIN_IN_TRADING_DAY = 390
PLOT_TOGGLE = True
