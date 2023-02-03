from blueshift.library.technicals.indicators import fibonacci_support, adx
from blueshift.finance import commission, slippage
from blueshift.api import symbol, order_target_percent, set_commission, set_slippage, schedule_function, date_rules, time_rules, get_datetime
import numpy as np
import pandas as pd
from math import sqrt

def initialize(context):
    # universe selection
    context.securities = [symbol('NIFTY-I'),symbol('BANKNIFTY-I')]
    # context.securities = [symbol('ADANIPOWER')]

    # define strategy parameters
    context.params = {'indicator_lookback':100,
                      'indicator_freq':'1d',
                      'buy_signal':1,
                      'sell_signal':-1,
                      'ROC_period_short':30,
                      'ROC_period_long':120,
                      'ADX_period':120,
                      'trade_freq':30,
                      'leverage':1}

    # variables to calculate support and resistance line and target portfolio
    context.stop_loss = dict((security,0) for security in context.securities)
    context.exit = dict((security,0) for security in context.securities)
    context.signal = dict((security,0) for security in context.securities)
    context.target_position = dict((security,0) for security in context.securities)

    # set trading cost and slippage to zero
    set_commission(commission.PerShare(cost=0.002, min_trade_cost=0.0))
    set_slippage(slippage.FixedSlippage(0.00))
    
    freq = int(context.params['trade_freq'])
    schedule_function(run_strategy, date_rules.every_day(), time_rules.every_nth_minute(freq))
    # schedule_function(run_strategy, date_rules.every_day(), time_rules.market_close(minutes=59))
    schedule_function(stop_trading, date_rules.every_day(), time_rules.market_close(minutes=30))

def before_trading_start(context, data):
    context.trade = True
    
def stop_trading(context, data):
    context.trade = False

def run_strategy(context, data):
    if not context.trade:
        return
    
    generate_signal(context,data)
    generate_target_position(context, data)
    rebalance(context, data)

def rebalance(context,data):
    for security in context.securities:
        order_target_percent(security, context.target_position[security])

def generate_target_position(context, data):
    num_secs = len(context.securities)
    weight = round(1.0/num_secs,2)*context.params['leverage']

    for security in context.securities:
        if context.signal[security] == context.params['buy_signal']:
            context.target_position[security] = weight
        elif context.signal[security] == context.params['sell_signal']:
            context.target_position[security] = 0



def is_bullish_engulfing(candles):
    present_candle = candles.iloc[-1]
    last_candle = candles.iloc[-2]
    last_to_last_candle = candles.iloc[-3]
    if (last_candle['close'] < last_candle['open']) and (last_to_last_candle['close'] > last_to_last_candle['open']) and (last_candle['close'] < last_to_last_candle['close'] and last_candle['open'] > last_to_last_candle['open']):
        # checking if the current candle is breaking the high of the previous engulfing candle
        if present_candle['high']>last_candle['close']:    
            return True
    return False

def generate_signal(context, data):
    try:
        price_data = data.history(context.securities, ['open','high','low','close'], context.params['indicator_lookback'], context.params['indicator_freq'])
    except:
        return

    for security in context.securities:
        px = price_data.xs(security)
        previous_candle = px.iloc[-2]
        present_candle=px.iloc[-1]
        # check if the candle is bulish engulfing and 
        if is_bullish_engulfing(px):
            context.signal[security] = context.params['buy_signal']
            context.stop_loss[security] = previous_candle['low']
            context.exit[security] = previous_candle.['high']+3*(previous_candle['high']-previous_candle['low'])
        elif context.stop_loss[security]>=px[-1]['close'] or context.exit[security]<=px[-1]['close']:
            context.signal[security] = context.params['sell_signal']            
        else:
            context.signal[security] =0

def is_bearish_engulfing(candles):
    present_candle = candles.iloc[-1]
    last_candle = candles.iloc[-2]
    last_to_last_candle = candles.iloc[-3]
    if (last_candle['close'] > last_candle['open']) and (last_to_last_candle['close'] < last_to_last_candle['open']) and (last_candle['close'] > last_to_last_candle['close'] and last_candle['open'] < last_to_last_candle['open']):
        return True
    return False
