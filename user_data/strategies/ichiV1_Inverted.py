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

    # Buy hyperspace params:
    buy_params = {
        "buy_trend_above_senkou_level": 1,
        "buy_trend_bullish_level": 6,
        "buy_fan_magnitude_shift_value": 3,
        "buy_min_fan_magnitude_gain": 1.002
    }

    # Sell hyperspace params:
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

    stoploss = -0.275
    timeframe = '5m'  
    startup_candle_count = 200
    process_only_new_candles = True

    trailing_stop = False
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    plot_config = {
        'main_plot': {
            'senkou_a': {
                'color': 'green',
                'fill_to': 'senkou_b',
                'fill_label': 'Ichimoku Cloud',
                'fill_color': 'rgba(255,76,46,0.2)',
            },
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

    # ------------- Feature Engineering (unchanged) -------------
    def feature_engineering_expand_all(self, dataframe: DataFrame, period: int, metadata: dict, **kwargs) -> DataFrame:
        safe_period = max(3, period) if period is not None else 14
        safe_kijun_period = max(9, safe_period * 3)
        dataframe[f"%-ichimoku_tenkan_period_{period}"] = ta.SMA(dataframe["close"], timeperiod=safe_period)
        dataframe[f"%-ichimoku_kijun_period_{period}"] = ta.SMA(dataframe["close"], timeperiod=safe_kijun_period)
        dataframe[f"%-ema_{period}"] = ta.EMA(dataframe["close"], timeperiod=safe_period)
        dataframe[f"%-ema_open_{period}"] = ta.EMA(dataframe["open"], timeperiod=safe_period)
        if period is None or not isinstance(period, int) or period <= 0:
            period = 8  
        if period >= 8:
            short_timeperiod = max(3, period // 8)
            long_timeperiod = max(5, period)
            short_ema = ta.EMA(dataframe["close"], timeperiod=short_timeperiod)
            long_ema = ta.EMA(dataframe["close"], timeperiod=long_timeperiod)
            with np.errstate(divide='ignore', invalid='ignore'):
                fan_magnitude = short_ema / long_ema
                fan_magnitude = np.where(np.isfinite(fan_magnitude), fan_magnitude, 1.0)
                dataframe[f"%-fan_magnitude_{period}"] = fan_magnitude
                fan_magnitude_shifted = dataframe[f"%-fan_magnitude_{period}"].shift(1)
                fan_magnitude_gain = dataframe[f"%-fan_magnitude_{period}"] / fan_magnitude_shifted
                fan_magnitude_gain = np.where(np.isfinite(fan_magnitude_gain), fan_magnitude_gain, 1.0)
                dataframe[f"%-fan_magnitude_gain_{period}"] = fan_magnitude_gain
        atr_period = max(3, period)
        dataframe[f"%-atr_{atr_period}"] = ta.ATR(dataframe, timeperiod=atr_period)
        return dataframe

    def feature_engineering_expand_basic(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        dataframe["%-rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["%-mfi"] = ta.MFI(dataframe, timeperiod=14)
        dataframe["%-adx"] = ta.ADX(dataframe, timeperiod=14)
        dataframe["%-sma"] = ta.SMA(dataframe, timeperiod=14)
        dataframe["%-ema"] = ta.EMA(dataframe, timeperiod=14)
        bollinger = qtpylib.bollinger_bands(dataframe["close"], window=20, stds=2)
        dataframe["%-bb_lowerband"] = bollinger["lower"]
        dataframe["%-bb_middleband"] = bollinger["mid"]
        dataframe["%-bb_upperband"] = bollinger["upper"]
        bb_range = bollinger["upper"] - bollinger["lower"]
        with np.errstate(divide='ignore', invalid='ignore'):
            bb_percent = (dataframe["close"] - bollinger["lower"]) / bb_range
            bb_width = bb_range / bollinger["mid"]
            dataframe["%-bb_percent"] = np.where(np.isfinite(bb_percent), bb_percent, 0.5)
            dataframe["%-bb_width"] = np.where(np.isfinite(bb_width), bb_width, 0.1)
        return dataframe

    def feature_engineering_standard(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        ichimoku = ftt.ichimoku(dataframe, conversion_line_period=20, base_line_periods=60, laggin_span=120, displacement=30)
        dataframe['%-chikou_span'] = ichimoku['chikou_span'].ffill().bfill()
        dataframe['%-tenkan_sen'] = ichimoku['tenkan_sen'].ffill().bfill()
        dataframe['%-kijun_sen'] = ichimoku['kijun_sen'].ffill().bfill()
        dataframe['%-senkou_a'] = ichimoku['senkou_span_a'].ffill().bfill()
        dataframe['%-senkou_b'] = ichimoku['senkou_span_b'].ffill().bfill()
        dataframe['%-leading_senkou_span_a'] = ichimoku['leading_senkou_span_a'].ffill().bfill()
        dataframe['%-leading_senkou_span_b'] = ichimoku['leading_senkou_span_b'].ffill().bfill()
        dataframe['%-cloud_green'] = ichimoku['cloud_green'].fillna(0).astype(int)
        dataframe['%-cloud_red'] = ichimoku['cloud_red'].fillna(0).astype(int)
        cloud_comparison = ((dataframe['close'] > dataframe['%-senkou_a']) & 
                           (dataframe['close'] > dataframe['%-senkou_b']))
        dataframe['%-price_above_cloud'] = cloud_comparison.fillna(False).astype(int)
        with np.errstate(divide='ignore', invalid='ignore'):
            close_open_ratio = dataframe['close'] / dataframe['open']
            dataframe['%-close_open_ratio'] = np.where(np.isfinite(close_open_ratio), close_open_ratio, 1.0)
        return dataframe

    def set_freqai_targets(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        future_close = dataframe["close"].shift(-5)
        current_close = dataframe["close"]
        with np.errstate(divide='ignore', invalid='ignore'):
            price_change = future_close / current_close - 1
            dataframe["&-target"] = np.where(np.isfinite(price_change), price_change, 0.0)
        return dataframe

    # ------------- Indicators (unchanged) -------------
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = self.freqai.start(dataframe, metadata, self)
        heikinashi = qtpylib.heikinashi(dataframe)
        dataframe['open'] = heikinashi['open']
        dataframe['high'] = heikinashi['high']
        dataframe['low'] = heikinashi['low']
        dataframe['trend_close_5m'] = dataframe['close']
        dataframe['trend_close_15m'] = ta.EMA(dataframe['close'], timeperiod=5)
        dataframe['trend_close_30m'] = ta.EMA(dataframe['close'], timeperiod=10)
        dataframe['trend_close_1h'] = ta.EMA(dataframe['close'], timeperiod=20)
        dataframe['trend_close_2h'] = ta.EMA(dataframe['close'], timeperiod=40)
        dataframe['trend_close_4h'] = ta.EMA(dataframe['close'], timeperiod=80)
        dataframe['trend_close_6h'] = ta.EMA(dataframe['close'], timeperiod=120)
        dataframe['trend_close_8h'] = ta.EMA(dataframe['close'], timeperiod=160)
        dataframe['trend_open_5m'] = dataframe['open']
        dataframe['trend_open_15m'] = ta.EMA(dataframe['open'], timeperiod=5)
        dataframe['trend_open_30m'] = ta.EMA(dataframe['open'], timeperiod=10)
        dataframe['trend_open_1h'] = ta.EMA(dataframe['open'], timeperiod=20)
        dataframe['trend_open_2h'] = ta.EMA(dataframe['open'], timeperiod=40)
        dataframe['trend_open_4h'] = ta.EMA(dataframe['open'], timeperiod=80)
        dataframe['trend_open_6h'] = ta.EMA(dataframe['open'], timeperiod=120)
        dataframe['trend_open_8h'] = ta.EMA(dataframe['open'], timeperiod=160)
        with np.errstate(divide='ignore', invalid='ignore'):
            fan_magnitude = dataframe['trend_close_1h'] / dataframe['trend_close_8h']
            dataframe['fan_magnitude'] = np.where(np.isfinite(fan_magnitude), fan_magnitude, 1.0)
            fan_magnitude_shifted = dataframe['fan_magnitude'].shift(1)
            fan_magnitude_gain = dataframe['fan_magnitude'] / fan_magnitude_shifted
            dataframe['fan_magnitude_gain'] = np.where(np.isfinite(fan_magnitude_gain), fan_magnitude_gain, 1.0)
        ichimoku = ftt.ichimoku(dataframe, conversion_line_period=20, base_line_periods=60, laggin_span=120, displacement=30)
        dataframe['chikou_span'] = ichimoku['chikou_span'].ffill().bfill()
        dataframe['tenkan_sen'] = ichimoku['tenkan_sen'].ffill().bfill()
        dataframe['kijun_sen'] = ichimoku['kijun_sen'].ffill().bfill()
        dataframe['senkou_a'] = ichimoku['senkou_span_a'].ffill().bfill()
        dataframe['senkou_b'] = ichimoku['senkou_span_b'].ffill().bfill()
        dataframe['leading_senkou_span_a'] = ichimoku['leading_senkou_span_a'].ffill().bfill()
        dataframe['leading_senkou_span_b'] = ichimoku['leading_senkou_span_b'].ffill().bfill()
        dataframe['cloud_green'] = ichimoku['cloud_green'].fillna(0)
        dataframe['cloud_red'] = ichimoku['cloud_red'].fillna(0)
        dataframe['atr'] = ta.ATR(dataframe)
        return dataframe

    # ------------- Inverted Trading Logic -------------
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Inverted: Buy when the old sell condition would trigger
        freqai_exit = (dataframe['do_predict'] == 1) & (dataframe['&-target'] < -0.001)
        original_exit = qtpylib.crossed_below(dataframe['trend_close_5m'], dataframe[self.sell_params['sell_trend_indicator']])
        dataframe.loc[freqai_exit | original_exit, 'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Inverted: Sell when the old buy condition would trigger
        freqai_conditions = [
            dataframe['do_predict'] == 1,
            dataframe['&-target'] > 0.001
        ]
        conditions = []

        if self.buy_params['buy_trend_above_senkou_level'] >= 1:
            conditions.append(dataframe['trend_close_5m'] > dataframe['senkou_a'])
            conditions.append(dataframe['trend_close_5m'] > dataframe['senkou_b'])
        if self.buy_params['buy_trend_above_senkou_level'] >= 6:
            conditions.append(dataframe['trend_close_4h'] > dataframe['senkou_a'])
            conditions.append(dataframe['trend_close_4h'] > dataframe['senkou_b'])
        if self.buy_params['buy_trend_bullish_level'] >= 6:
            conditions.append(dataframe['trend_close_4h'] > dataframe['trend_open_4h'])

        conditions.append(dataframe['fan_magnitude_gain'] >= self.buy_params['buy_min_fan_magnitude_gain'])
        conditions.append(dataframe['fan_magnitude'] > 1)
        for x in range(self.buy_params['buy_fan_magnitude_shift_value']):
            conditions.append(dataframe['fan_magnitude'].shift(x+1) < dataframe['fan_magnitude'])

        dataframe.loc[
            (reduce(lambda x, y: x & y, freqai_conditions) & reduce(lambda x, y: x & y, conditions)) |
            (reduce(lambda x, y: x & y, conditions) & (dataframe['do_predict'] != 1)),
            'exit_long'
        ] = 1
        return dataframe
