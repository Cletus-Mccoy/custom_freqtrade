# --- Do not remove these libs ---
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
import pandas as pd  # noqa
pd.options.mode.chained_assignment = None  # default='warn'
import technical.indicators as ftt
from functools import reduce
from datetime import datetime, timedelta
from freqtrade.strategy import merge_informative_pair
import numpy as np
from freqtrade.strategy import stoploss_from_open


class ichiV1(IStrategy):

    # NOTE: settings as of the 25th july 21
    # Buy hyperspace params:
    buy_params = {
        "buy_trend_above_senkou_level": 1,
        "buy_trend_bullish_level": 6,
        "buy_fan_magnitude_shift_value": 3,
        "buy_min_fan_magnitude_gain": 1.002 # NOTE: Good value (Win% ~70%), alot of trades
        #"buy_min_fan_magnitude_gain": 1.008 # NOTE: Very save value (Win% ~90%), only the biggest moves 1.008,
    }

    # Sell hyperspace params:
    # NOTE: was 15m but kept bailing out in dryrun
    sell_params = {
        "sell_trend_indicator": "trend_close_2h",
    }

    # ROI table:
    minimal_roi = {
        "0": 0.059,
        "10": 0.037,
        "41": 0.012,
        "114": 0
    }

    # Stoploss:
    stoploss = -0.275

    # Optimal timeframe for the strategy
    timeframe = '3m'  # Updated to match config

    startup_candle_count = 96
    process_only_new_candles = False

    trailing_stop = False
    #trailing_stop_positive = 0.002
    #trailing_stop_positive_offset = 0.025
    #trailing_only_offset_is_reached = True

    use_exit_signal = True  # Updated from use_sell_signal
    exit_profit_only = False  # Updated from sell_profit_only
    ignore_roi_if_entry_signal = False  # Updated from ignore_roi_if_buy_signal

    plot_config = {
        'main_plot': {
            # fill area between senkou_a and senkou_b
            'senkou_a': {
                'color': 'green', #optional
                'fill_to': 'senkou_b',
                'fill_label': 'Ichimoku Cloud', #optional
                'fill_color': 'rgba(255,76,46,0.2)', #optional
            },
            # plot senkou_b, too. Not only the area to it.
            'senkou_b': {},
            'trend_close_5m': {'color': '#FF5733'},
            'trend_close_15m': {'color': '#FF8333'},
            'trend_close_30m': {'color': '#FFB533'},
            'trend_close_1h': {'color': '#FFE633'},
            'trend_close_2h': {'color': '#E3FF33'},
            'trend_close_4h': {'color': '#C4FF33'},
            'trend_close_6h': {'color': '#61FF33'},
            'trend_close_8h': {'color': '#33FF7D'}
        },
        'subplots': {
            'fan_magnitude': {
                'fan_magnitude': {}
            },
            'fan_magnitude_gain': {
                'fan_magnitude_gain': {}
            }
        }
    }

    def feature_engineering_expand_all(self, dataframe: DataFrame, period: int, metadata: dict, **kwargs) -> DataFrame:
        """
        *Only functional with FreqAI enabled strategies*
        This function will automatically expand the defined features on the config defined
        `include_timeframes`, `include_shifted_candles`, and `include_corr_pairs`.
        """
        # Add Ichimoku features
        dataframe[f"%-ichimoku_tenkan_period_{period}"] = ta.SMA(dataframe["close"], timeperiod=period)
        dataframe[f"%-ichimoku_kijun_period_{period}"] = ta.SMA(dataframe["close"], timeperiod=period * 3)
        
        # Add EMA features for different periods
        dataframe[f"%-ema_{period}"] = ta.EMA(dataframe["close"], timeperiod=period)
        dataframe[f"%-ema_open_{period}"] = ta.EMA(dataframe["open"], timeperiod=period)
        
        # Add fan magnitude features
        if period >= 8:
            short_ema = ta.EMA(dataframe["close"], timeperiod=max(1, period // 8))
            long_ema = ta.EMA(dataframe["close"], timeperiod=period)
            dataframe[f"%-fan_magnitude_{period}"] = short_ema / long_ema
            dataframe[f"%-fan_magnitude_gain_{period}"] = dataframe[f"%-fan_magnitude_{period}"] / dataframe[f"%-fan_magnitude_{period}"].shift(1)
        
        # Add ATR
        dataframe[f"%-atr_{period}"] = ta.ATR(dataframe, timeperiod=period)
        
        return dataframe

    def feature_engineering_expand_basic(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        """
        *Only functional with FreqAI enabled strategies*
        This function will automatically expand the defined features on the config defined
        `include_timeframes`, `include_shifted_candles`, and `include_corr_pairs`.
        All features must be prepended with `%` to be recognized by FreqAI internals.
        """
        # Add basic Ichimoku cloud features
        dataframe["%-rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["%-mfi"] = ta.MFI(dataframe, timeperiod=14)
        dataframe["%-adx"] = ta.ADX(dataframe, timeperiod=14)
        dataframe["%-sma"] = ta.SMA(dataframe, timeperiod=14)
        dataframe["%-ema"] = ta.EMA(dataframe, timeperiod=14)
        
        # Bollinger bands
        bollinger = qtpylib.bollinger_bands(dataframe["close"], window=20, stds=2)
        dataframe["%-bb_lowerband"] = bollinger["lower"]
        dataframe["%-bb_middleband"] = bollinger["mid"]
        dataframe["%-bb_upperband"] = bollinger["upper"]
        dataframe["%-bb_percent"] = (dataframe["close"] - bollinger["lower"]) / (bollinger["upper"] - bollinger["lower"])
        dataframe["%-bb_width"] = (bollinger["upper"] - bollinger["lower"]) / bollinger["mid"]
        
        return dataframe

    def feature_engineering_standard(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        """
        *Only functional with FreqAI enabled strategies*
        This function will be called once with the dataframe of the base timeframe.
        All features must be prepended with `%` to be recognized by FreqAI internals.
        """
        # Add the original Ichimoku indicators as features
        ichimoku = ftt.ichimoku(dataframe, conversion_line_period=20, base_line_periods=60, laggin_span=120, displacement=30)
        dataframe['%-chikou_span'] = ichimoku['chikou_span']
        dataframe['%-tenkan_sen'] = ichimoku['tenkan_sen']
        dataframe['%-kijun_sen'] = ichimoku['kijun_sen']
        dataframe['%-senkou_a'] = ichimoku['senkou_span_a']
        dataframe['%-senkou_b'] = ichimoku['senkou_span_b']
        dataframe['%-leading_senkou_span_a'] = ichimoku['leading_senkou_span_a']
        dataframe['%-leading_senkou_span_b'] = ichimoku['leading_senkou_span_b']
        dataframe['%-cloud_green'] = ichimoku['cloud_green'].astype(int)
        dataframe['%-cloud_red'] = ichimoku['cloud_red'].astype(int)
        
        # Add price position relative to cloud
        dataframe['%-price_above_cloud'] = ((dataframe['close'] > dataframe['%-senkou_a']) & 
                                           (dataframe['close'] > dataframe['%-senkou_b'])).astype(int)
        
        # Add trend strength features
        dataframe['%-close_open_ratio'] = dataframe['close'] / dataframe['open']
        
        return dataframe

    def set_freqai_targets(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        """
        *Only functional with FreqAI enabled strategies*
        Required function to set the targets for the machine learning model.
        All targets must be prepended with `&` to be recognized by FreqAI internals.
        """
        # Predict future price movement (5 candles ahead)
        dataframe["&-target"] = dataframe["close"].shift(-5) / dataframe["close"] - 1
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Start FreqAI first
        dataframe = self.freqai.start(dataframe, metadata, self)

        # Apply Heikin Ashi transformation (KEEPING THE ORIGINAL)
        heikinashi = qtpylib.heikinashi(dataframe)
        dataframe['open'] = heikinashi['open']
        #dataframe['close'] = heikinashi['close']  # Keep original close for signals
        dataframe['high'] = heikinashi['high']
        dataframe['low'] = heikinashi['low']

        # Calculate ALL original trend indicators (adjusted periods for 3m timeframe)
        dataframe['trend_close_5m'] = dataframe['close']
        dataframe['trend_close_15m'] = ta.EMA(dataframe['close'], timeperiod=5)   # 15m equivalent for 3m
        dataframe['trend_close_30m'] = ta.EMA(dataframe['close'], timeperiod=10)  # 30m equivalent for 3m
        dataframe['trend_close_1h'] = ta.EMA(dataframe['close'], timeperiod=20)   # 1h equivalent for 3m
        dataframe['trend_close_2h'] = ta.EMA(dataframe['close'], timeperiod=40)   # 2h equivalent for 3m
        dataframe['trend_close_4h'] = ta.EMA(dataframe['close'], timeperiod=80)   # 4h equivalent for 3m
        dataframe['trend_close_6h'] = ta.EMA(dataframe['close'], timeperiod=120)  # 6h equivalent for 3m
        dataframe['trend_close_8h'] = ta.EMA(dataframe['close'], timeperiod=160)  # 8h equivalent for 3m

        dataframe['trend_open_5m'] = dataframe['open']
        dataframe['trend_open_15m'] = ta.EMA(dataframe['open'], timeperiod=5)
        dataframe['trend_open_30m'] = ta.EMA(dataframe['open'], timeperiod=10)
        dataframe['trend_open_1h'] = ta.EMA(dataframe['open'], timeperiod=20)
        dataframe['trend_open_2h'] = ta.EMA(dataframe['open'], timeperiod=40)
        dataframe['trend_open_4h'] = ta.EMA(dataframe['open'], timeperiod=80)
        dataframe['trend_open_6h'] = ta.EMA(dataframe['open'], timeperiod=120)
        dataframe['trend_open_8h'] = ta.EMA(dataframe['open'], timeperiod=160)

        # Calculate fan magnitude (KEEPING THE ORIGINAL)
        dataframe['fan_magnitude'] = (dataframe['trend_close_1h'] / dataframe['trend_close_8h'])
        dataframe['fan_magnitude_gain'] = dataframe['fan_magnitude'] / dataframe['fan_magnitude'].shift(1)

        # Calculate Ichimoku indicators (KEEPING THE ORIGINAL)
        ichimoku = ftt.ichimoku(dataframe, conversion_line_period=20, base_line_periods=60, laggin_span=120, displacement=30)
        dataframe['chikou_span'] = ichimoku['chikou_span']
        dataframe['tenkan_sen'] = ichimoku['tenkan_sen']
        dataframe['kijun_sen'] = ichimoku['kijun_sen']
        dataframe['senkou_a'] = ichimoku['senkou_span_a']
        dataframe['senkou_b'] = ichimoku['senkou_span_b']
        dataframe['leading_senkou_span_a'] = ichimoku['leading_senkou_span_a']
        dataframe['leading_senkou_span_b'] = ichimoku['leading_senkou_span_b']
        dataframe['cloud_green'] = ichimoku['cloud_green']
        dataframe['cloud_red'] = ichimoku['cloud_red']

        # Calculate ATR (KEEPING THE ORIGINAL)
        dataframe['atr'] = ta.ATR(dataframe)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []

        # Use FreqAI prediction as primary signal (when available)
        freqai_conditions = [
            dataframe['do_predict'] == 1,
            dataframe['&-target'] > 0.001  # Predict positive price movement (0.1%)
        ]

        # KEEP ALL ORIGINAL CONDITIONS
        # Trending market
        if self.buy_params['buy_trend_above_senkou_level'] >= 1:
            conditions.append(dataframe['trend_close_5m'] > dataframe['senkou_a'])
            conditions.append(dataframe['trend_close_5m'] > dataframe['senkou_b'])

        if self.buy_params['buy_trend_above_senkou_level'] >= 2:
            conditions.append(dataframe['trend_close_15m'] > dataframe['senkou_a'])
            conditions.append(dataframe['trend_close_15m'] > dataframe['senkou_b'])

        if self.buy_params['buy_trend_above_senkou_level'] >= 3:
            conditions.append(dataframe['trend_close_30m'] > dataframe['senkou_a'])
            conditions.append(dataframe['trend_close_30m'] > dataframe['senkou_b'])

        if self.buy_params['buy_trend_above_senkou_level'] >= 4:
            conditions.append(dataframe['trend_close_1h'] > dataframe['senkou_a'])
            conditions.append(dataframe['trend_close_1h'] > dataframe['senkou_b'])

        if self.buy_params['buy_trend_above_senkou_level'] >= 5:
            conditions.append(dataframe['trend_close_2h'] > dataframe['senkou_a'])
            conditions.append(dataframe['trend_close_2h'] > dataframe['senkou_b'])

        if self.buy_params['buy_trend_above_senkou_level'] >= 6:
            conditions.append(dataframe['trend_close_4h'] > dataframe['senkou_a'])
            conditions.append(dataframe['trend_close_4h'] > dataframe['senkou_b'])

        if self.buy_params['buy_trend_above_senkou_level'] >= 7:
            conditions.append(dataframe['trend_close_6h'] > dataframe['senkou_a'])
            conditions.append(dataframe['trend_close_6h'] > dataframe['senkou_b'])

        if self.buy_params['buy_trend_above_senkou_level'] >= 8:
            conditions.append(dataframe['trend_close_8h'] > dataframe['senkou_a'])
            conditions.append(dataframe['trend_close_8h'] > dataframe['senkou_b'])

        # Trends bullish
        if self.buy_params['buy_trend_bullish_level'] >= 1:
            conditions.append(dataframe['trend_close_5m'] > dataframe['trend_open_5m'])

        if self.buy_params['buy_trend_bullish_level'] >= 2:
            conditions.append(dataframe['trend_close_15m'] > dataframe['trend_open_15m'])

        if self.buy_params['buy_trend_bullish_level'] >= 3:
            conditions.append(dataframe['trend_close_30m'] > dataframe['trend_open_30m'])

        if self.buy_params['buy_trend_bullish_level'] >= 4:
            conditions.append(dataframe['trend_close_1h'] > dataframe['trend_open_1h'])

        if self.buy_params['buy_trend_bullish_level'] >= 5:
            conditions.append(dataframe['trend_close_2h'] > dataframe['trend_open_2h'])

        if self.buy_params['buy_trend_bullish_level'] >= 6:
            conditions.append(dataframe['trend_close_4h'] > dataframe['trend_open_4h'])

        if self.buy_params['buy_trend_bullish_level'] >= 7:
            conditions.append(dataframe['trend_close_6h'] > dataframe['trend_open_6h'])

        if self.buy_params['buy_trend_bullish_level'] >= 8:
            conditions.append(dataframe['trend_close_8h'] > dataframe['trend_open_8h'])

        # Trends magnitude (KEEPING THE ORIGINAL)
        conditions.append(dataframe['fan_magnitude_gain'] >= self.buy_params['buy_min_fan_magnitude_gain'])
        conditions.append(dataframe['fan_magnitude'] > 1)

        for x in range(self.buy_params['buy_fan_magnitude_shift_value']):
            conditions.append(dataframe['fan_magnitude'].shift(x+1) < dataframe['fan_magnitude'])

        # Combine FreqAI with original conditions
        if conditions:
            # Use FreqAI when available, otherwise fall back to original logic
            dataframe.loc[
                (reduce(lambda x, y: x & y, freqai_conditions) & reduce(lambda x, y: x & y, conditions)) |
                (reduce(lambda x, y: x & y, conditions) & (dataframe['do_predict'] != 1)),
                'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []

        # Use FreqAI prediction when available
        freqai_exit = (dataframe['do_predict'] == 1) & (dataframe['&-target'] < -0.001)  # Predict negative movement

        # Keep original exit condition
        original_exit = qtpylib.crossed_below(dataframe['trend_close_5m'], dataframe[self.sell_params['sell_trend_indicator']])

        # Combine both conditions
        dataframe.loc[freqai_exit | original_exit, 'exit_long'] = 1

        return dataframe