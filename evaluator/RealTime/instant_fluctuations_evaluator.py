import time

from evaluator.RealTime.realtime_evaluator import RealTimeTAEvaluator

from config.cst import *


class InstantFluctuationsEvaluator(RealTimeTAEvaluator):
    def __init__(self, exchange, symbol):
        super().__init__(exchange, symbol)
        self.enabled = True
        self.something_is_happening = False
        self.refresh_time = 0

        self.average_price = 0
        self.last_price = 0

        # Volume
        self.volume_updated = 0
        self.average_volume = 0
        self.last_volume = 0

        # Constants
        self.MIN_EVAL_NOTE = 0.5
        self.VOLUME_HAPPENING_THRESHOLD = 3
        self.PRICE_HAPPENING_THRESHOLD = 1.005

    def refresh_data(self):
        self.update()

    def eval_impl(self):
        self.evaluate_volume_fluctuations()
        if self.something_is_happening:
            self.notify_evaluator_threads(self.__class__.__name__)
            self.something_is_happening = False
        else:
            self.eval_note = START_PENDING_EVAL_NOTE

    def evaluate_volume_fluctuations(self):
        # check volume fluctuation
        if self.last_volume > self.VOLUME_HAPPENING_THRESHOLD * self.average_volume:
            # TEMP
            self.eval_note = self.MIN_EVAL_NOTE if self.last_price > self.average_price else -self.MIN_EVAL_NOTE
            self.something_is_happening = True

        # check price fluctuation
        if self.last_price > self.PRICE_HAPPENING_THRESHOLD * self.average_price:
            self.eval_note = self.MIN_EVAL_NOTE
            self.something_is_happening = True

        elif self.last_price < (1 - self.PRICE_HAPPENING_THRESHOLD) * self.average_price:
            self.eval_note = -self.MIN_EVAL_NOTE
            self.something_is_happening = True

    def update(self, force=False):
        self.volume_updated += 1

        if (self.refresh_time * self.volume_updated) > TimeFramesMinutes[self.specific_config[CONFIG_TIME_FRAME]] or force:
            volume_data = self.exchange.get_symbol_prices(self.symbol, self.specific_config[CONFIG_TIME_FRAME], 10)
            self.average_volume = volume_data[PriceStrings.STR_PRICE_VOL.value].mean()
            self.average_price = volume_data[PriceStrings.STR_PRICE_CLOSE.value].mean()
            self.volume_updated = 0

        else:
            volume_data = self.exchange.get_symbol_prices(self.symbol, self.specific_config[CONFIG_TIME_FRAME], 1)

        self.last_volume = volume_data[PriceStrings.STR_PRICE_VOL.value].tail(1).values[0]
        self.last_price = volume_data[PriceStrings.STR_PRICE_CLOSE.value].tail(1).values[0]

    def set_default_config(self):
        self.specific_config = {
            CONFIG_REFRESH_RATE: 10,
            CONFIG_TIME_FRAME: TimeFrames.ONE_MINUTE
        }

    def run(self):
        self.refresh_time = self.valid_refresh_time(self.specific_config[CONFIG_REFRESH_RATE])

        self.update(force=True)

        while self.keep_running:
            self.refresh_data()
            self.eval()
            time.sleep(self.refresh_time)
