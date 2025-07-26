import logging
from functools import reduce

import talib.abstract as ta
from pandas import DataFrame
from technical import qtpylib

from freqtrade.strategy import IStrategy

logger = logging.getLogger(__name__)

class FreqaiExampleStrategy_FilterEMA(IStrategy):
    minimal_roi = {"0": 0.1, "240": -1}
    stoploss = -0.05
    can_short = False
    process_only_new_candles = True
    use_exit_signal = True
    startup_candle_count: int = 136

    plot_config = {
        "main_plot": {
            "ema_fast": {},
            "ema_slow": {},
        },
        "subplots": {
            "&-s_close": {"&-s_close": {"color": "blue"}},
            "do_predict": {"do_predict": {"color": "orange"}},
        },
    }

    def feature_engineering_expand_all(self, dataframe: DataFrame, period: int, metadata: dict, **kwargs) -> DataFrame:
        dataframe["%-rsi-period"] = ta.RSI(dataframe, timeperiod=period)
        dataframe["%-mfi-period"] = ta.MFI(dataframe, timeperiod=period)
        dataframe["%-adx-period"] = ta.ADX(dataframe, timeperiod=period)
        dataframe["%-ema-period"] = ta.EMA(dataframe, timeperiod=period)
        dataframe["%-roc-period"] = ta.ROC(dataframe, timeperiod=period)

        boll = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=period, stds=2)
        dataframe["bb_upper"] = boll["upper"]
        dataframe["bb_lower"] = boll["lower"]
        dataframe["%-bb_width"] = (boll["upper"] - boll["lower"]) / dataframe["close"]
        dataframe["%-rel_volume"] = dataframe["volume"] / dataframe["volume"].rolling(period).mean()
        return dataframe.bfill().ffill()

    def feature_engineering_expand_basic(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        dataframe["%-pct-change"] = dataframe["close"].pct_change()
        dataframe["%-raw_price"] = dataframe["close"]
        dataframe["%-raw_volume"] = dataframe["volume"]
        return dataframe.bfill().ffill()

    def feature_engineering_standard(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        dataframe["%-day_of_week"] = dataframe["date"].dt.dayofweek
        dataframe["%-hour_of_day"] = dataframe["date"].dt.hour
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=9)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=21)
        return dataframe.bfill().ffill()

    def set_freqai_targets(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        label_period = self.freqai_info["feature_parameters"]["label_period_candles"]
        dataframe["&-s_close"] = (
            dataframe["close"].shift(-label_period).rolling(label_period).mean() / dataframe["close"] - 1
        )
        return dataframe.bfill().ffill()

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return self.freqai.start(dataframe, metadata, self)

    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        df["enter_long"] = 0
        df["enter_tag"] = ""

        entry_conditions = [
            df["do_predict"] == 1,
            df["&-s_close"] > 0.003,  # Sterk positief signaal
            df["ema_fast"] > df["ema_slow"],  # Uptrend
            df["volume"] > df["volume"].rolling(20).mean(),  # Boven gemiddeld volume
        ]

        entry_signal = reduce(lambda x, y: x & y, entry_conditions)

        df.loc[entry_signal, "enter_long"] = 1
        df.loc[entry_signal, "enter_tag"] = "freqai_entry"

        return df

    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        df["exit_long"] = 0
        df["exit_tag"] = ""

        exit_conditions = [
            df["do_predict"] == 1,
            df["&-s_close"] < -0.002,  # Negatief vooruitzicht
        ]

        exit_signal = reduce(lambda x, y: x & y, exit_conditions)
        df.loc[exit_signal, "exit_long"] = 1
        df.loc[exit_signal, "exit_tag"] = "freqai_exit"

        return df

    def confirm_trade_entry(
        self,
        pair: str,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time,
        entry_tag,
        side: str,
        **kwargs,
    ) -> bool:
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last = df.iloc[-1]

        if side == "long" and rate > (last["close"] * 1.01):  # Niet te ver boven laatste candle kopen
            return False
        return True
