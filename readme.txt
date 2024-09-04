Notes:

- Loads data from Yahoo Finance (using yFinance) into a local csv. 
  This allows for a lookback greater than 30 days at high granularity (i.e. time=1m). 

- When data_manager.py is executed, the csv is updated.
  It is recommended to use a powershell script to make sure data_manager.py is executed regularly.

- Matplotlib plots are saved to "trading_mk1\data\plots"

- The settings.py module allows for features to be toggled on or off. For example, the PLOT_TOGGLE boolean
  determines if the plots are written and saved.

Citations and comments:

Zarattini, Carlo and Aziz, Andrew and Barbon, Andrea, 
Beat the Market An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)
(May 10, 2024). Available at SSRN: https://ssrn.com/abstract=4824172 or http://dx.doi.org/10.2139/ssrn.4824172
