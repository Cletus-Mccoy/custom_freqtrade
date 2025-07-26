import logging
from functools import reduce

import talib.abstract as ta
from pandas import DataFrame
from technical import qtpylib

from freqtrade.strategy import IStrategy

logger = logging.getLogger(__name__)

class FreqaiExampleStrategy_Classification(IStrategy):
    minimal_roi = {"0": 0.1, "240": -1}
    stoploss = -0.05
    can_short = False
    process_only_new_candles = True
    use_exit_signal = True
    startup_candle_count: int = 150

    plot_config = {
        "main_plot": {
            "ema_fast": {},
            "ema_slow": {},
        },
        "subplots": {
            "&-target_class": {"&-target_class": {"color": "green"}},
            "do_predict": {"do_predict": {"color": "orange"}},
        },
    }

    def feature_engineering_expand_all(self, dataframe: DataFrame, period: int, metadata: dict, **kwargs) -> DataFrame:
        dataframe["%-rsi-period"] = ta.RSI(dataframe, timeperiod=period)
        dataframe["%-adx-period"] = ta.ADX(dataframe, timeperiod=period)
        dataframe["%-roc-period"] = ta.ROC(dataframe, timeperiod=period)
        dataframe["%-ema-period"] = ta.EMA(dataframe, timeperiod=period)

        boll = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=period, stds=2)
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
        future_return = (
            dataframe["close"].shift(-label_period).rolling(label_period).mean() / dataframe["close"] - 1
        )

        # Classificatie-target: 1 = stijging, 0 = geen/negatief
        dataframe["&-target_class"] = (future_return > 0.002).astype(int)

        return dataframe.bfill().ffill()

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return self.freqai.start(dataframe, metadata, self)

    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        df["enter_long"] = 0
        df["enter_tag"] = ""

        entry_condition = (
            (df["do_predict"] == 1) &
            (df["&-target_class"] == 1) &
            (df["ema_fast"] > df["ema_slow"]) &
            (df["volume"] > df["volume"].rolling(20).mean())
        )

        df.loc[entry_condition, "enter_long"] = 1
        df.loc[entry_condition, "enter_tag"] = "freqai_class_entry"

        return df

    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        df["exit_long"] = 0
        df["exit_tag"] = ""

        exit_condition = (
            (df["do_predict"] == 1) &
            (df["&-target_class"] == 0)
        )

        df.loc[exit_condition, "exit_long"] = 1
        df.loc[exit_condition, "exit_tag"] = "freqai_class_exit"

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

        if side == "long" and rate > (last["close"] * 1.01):
            return False
        return True
