import sys
from datetime import datetime

from bs4 import BeautifulSoup
import numpy
import pandas as pd
import requests

import backtrader as bt
import pprint
from dateutil import relativedelta


# https://stackoverflow.com/questions/21806496/pandas-seems-to-ignore-first-column-name-when-reading-tab-delimited-data-gives
def remove_bom(filename):
    fp = open(filename)
    fp.read(1)
    return fp


class SmaCross(bt.Strategy):
    # list of parameters which are configurable for the strategy
    params = dict(
        pfast=50,  # period for the fast moving average
        pslow=200  # period for the slow moving average
    )

    #curdate = 0

    def __init__(self):
        sma1 = bt.ind.SMA(period=self.p.pfast)  # fast moving average
        sma2 = bt.ind.SMA(period=self.p.pslow)  # slow moving average
        self.crossover = bt.ind.CrossOver(sma1, sma2)  # crossover signal
        self.curdate = 0

    def next(self):
        if not self.position:  # not in the market
            if self.crossover > 0:  # if fast crosses slow to the upside
                self.buy()  # enter long

                self.curdate = self.datetime.date(ago=0)
        # close out at 9 months. compare self.position.datetime - buy datetime
        elif self.crossover < 0:  # in the market & cross to the downside
            self.close()  # close long position


def get_day_rows_till_sell(start_index, stream):
    days_after_sell = []

    for index, row in stream[start_index:].iterrows():
        if numpy.isnan(row['sell']):
            days_after_sell.append(row)
        else:
            return days_after_sell


def get_day_rows_till_buy(start_index, stream):
    days_after_sell = []

    for index, row in stream[start_index:].iterrows():
        if numpy.isnan(row['buy']):
            days_after_sell.append(row)
        else:
            return days_after_sell


def get_day_rows_n_timespan(start_index, stream, date):
    days = []

    start_date = datetime.strptime(format_date(date), "%Y-%m-%d")

    for index, row in stream[start_index:].iterrows():

        if type(row['datetime']) == str:
            current_date = datetime.strptime(format_date(row['datetime']), "%Y-%m-%d")
            r = relativedelta.relativedelta(current_date, start_date)
            # months will be zero based
            # 5 months = 0 to 4, r.months < 5
            # 1 month = 0 to 1, r.months < 1
            # etc
            if r.months < 5:
                days.append(row)
            else:
                return days
        else:
            return days


def format_date(date):
    return date.split(" ")[0]


def get_trends_n_timespan_buy(stream):
    trends = {}
    values = []

    for index, row in stream.iterrows():
        average_price = 0
        cumulative_price = 0
        if not numpy.isnan(row['buy']):
            buy_date = row['datetime']
            buy_price = row['adjclose']
            days_after_buy = get_day_rows_n_timespan(index + 1, stream, buy_date)

            days = 0

            for day in days_after_buy:
                days += 1
                cumulative_price += day['adjclose']

            average_price = cumulative_price / days
            valid_sell = average_price > buy_price

            values.append({'valid sell': valid_sell, 'sell date': buy_date, 'average price': average_price,
                           'close price at buy': buy_price})

    trends['title'] = stream.columns[1]
    trends['values'] = values

    return trends


def get_trends_n_timespan_sell(stream):
    trends = {}
    values = []

    for index, row in stream.iterrows():
        average_price = 0
        cumulative_price = 0
        if not numpy.isnan(row['sell']):
            sell_date = row['datetime']
            sell_price = row['adjclose']
            days_after_buy = get_day_rows_n_timespan(index + 1, stream, sell_date)

            days = 0

            for day in days_after_buy:
                days += 1
                cumulative_price += day['adjclose']

            average_price = cumulative_price / days
            valid_sell = average_price < sell_price

            values.append({'valid sell': valid_sell, 'sell date': sell_date, 'average price': average_price,
                           'close price at sell': sell_price})

    trends['title'] = stream.columns[1]
    trends['values'] = values

    return trends

# get trends of stock from each buy to a sell, Golden Cross
def get_trends_next_sell(stream):
    trends = {}
    values = []

    for index, row in stream.iterrows():
        average_price = 0
        cumulative_price = 0
        if not numpy.isnan(row['buy']):
            # current_date = row['datetime']
            close_price = row['adjclose']
            days_after_buy = get_day_rows_till_sell(index + 1, stream)

            days = 0
            if days_after_buy:
                for day in days_after_buy:
                    days += 1
                    cumulative_price += day['adjclose']

                average_price = cumulative_price / days

                valid_sell = average_price > close_price
                buy_date = row['datetime']

                values.append({'valid sell': valid_sell, 'date': buy_date, 'average price': average_price,
                           'close price': close_price})

            #values.append({'valid sell': valid_sell, 'sell date': sell_date, 'close price': close_price,
             #              'average price': average_price})

    trends['title'] = stream.columns[1]
    trends['values'] = values

    return trends

# get trends of stock from each sell to next buy, Golden Cross
def get_trends_next_buy(stream):
    trends = {}
    values = []

    for index, row in stream.iterrows():
        average_price = 0
        cumulative_price = 0
        if not numpy.isnan(row['sell']):
            # current_date = row['datetime']
            close_price = row['adjclose']
            days_after_buy = get_day_rows_till_buy(index + 1, stream)

            days = 0

            if days_after_buy:
                for day in days_after_buy:
                    days += 1
                    cumulative_price += day['adjclose']

                average_price = cumulative_price / days

                valid_sell = average_price < close_price
                buy_date = row['datetime']

                values.append({'valid sell': valid_sell, 'date': buy_date, 'average price': average_price,
                           'close price': close_price})

            #values.append({'valid sell': valid_sell, 'sell date': sell_date, 'close price': close_price,
             #              'average price': average_price})

    trends['title'] = stream.columns[1]
    trends['values'] = values

    return trends



def validate_trends(trends):
    total_true = 0.0
    total_trends = len(trends['values']) + .0
    for trend in trends['values']:
        if trend['valid sell']:
            total_true += 1

    percent_correct = total_true / total_trends
    trends['percent correct'] = percent_correct


def get_overall_correct(trends):
    average_percent_correct = 0.0
    cummulative_percent = 0.0
    total_trends = len(trends['values']) + .0

    for trend in trends:
        cummulative_percent += trend['percent correct']

    average_percent_correct = cummulative_percent / total_trends

    return average_percent_correct

def get_average_days(trends):
    d1 = datetime.strptime(format_date(trends['values'][0]['date']), "%Y-%m-%d")

    cumulative_days = 0

    for trend in trends['values'][1:]:
        d2 = datetime.strptime(format_date(trend['date']), "%Y-%m-%d")
        r = relativedelta.relativedelta(d2, d1)
        cumulative_days += r.days

    average_days = cumulative_days / len(trends['values'])
    trends['average days'] = average_days

def get_sp500():
    '''
    Goes to Wikipedia to get ticker symbols, and CIK codes for S&P 500 companies
    '''
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    r = requests.get(url)
    data = r.text
    soup = BeautifulSoup(data, 'lxml')
    company_table = soup.find_all('tr')[1:506]
    company_dict = dict()

    for row in company_table:
        row = row.find_all('td')
        # slice into table to grab ticker and CIK
        company_dict[row[0].get_text()] = row[7].get_text()

    return company_dict


def run_stock(name):
    cerebro = bt.Cerebro()  # create a "Cerebro" engine instance
    # Create a data feed
    data = bt.feeds.YahooFinanceData(dataname=name,
                                     fromdate=datetime(1999, 1, 1),
                                     todate=datetime(2019, 12, 31))

    cerebro.adddata(data)  # Add the data feed

    cerebro.addstrategy(SmaCross)  # Add the trading strategy
    cerebro.addwriter(bt.WriterFile, csv=True, out='test_file.csv')

    cerebro.run()  # run it all
    df = pd.read_csv(remove_bom('test_file.csv'), header=1)

    # get golden cross trends and print results
    #trends_golden_cross = get_trends_n_timespan_buy(df)
    trends_golden_cross = get_trends_next_sell(df)
    validate_trends(trends_golden_cross)
    #get_average_days(trends_golden_cross)

    pp = pprint.PrettyPrinter(indent=1)
    print('\nGolden Cross:')
    #pp.pprint(trends_golden_cross['average days'])
    pp.pprint(trends_golden_cross)
    #pp.pprint(trends_golden_cross['title'])
    #pp.pprint(trends_golden_cross['percent correct'])
    #pp.pprint(trends_golden_cross['average days'])

    # get death cross trends and print results
    print('\nDeath Cross')
    trends_death_cross = get_trends_n_timespan_sell(df)
    #trends_death_cross = get_trends_next_buy(df)
    validate_trends(trends_death_cross)
    #get_average_days(trends_death_cross)

    pp.pprint(trends_death_cross)
    #pp.pprint(trends_death_cross['title'])
    #pp.pprint(trends_death_cross['percent correct'])
    #pp.pprint(trends_death_cross['average days'])
    cerebro.plot()  # and plot it with a single command
    return trends_golden_cross, trends_death_cross

'''
sp500_stocks = get_sp500()
stock_count = 1
cumulative_percent_correct_golden_cross = 0.0
cumulative_percent_correct_death_cross = 0.0

cumulative_days_golden_cross = 0.0 #golden cross
cumulative_days_death_cross = 0.0 #death cross

for ticker, cik in sp500_stocks.items():
    try:
        if stock_count < 600:
            trends = run_stock('{}'.format(ticker).rstrip())
            cumulative_percent_correct_golden_cross += trends[0]['percent correct']
            cumulative_percent_correct_death_cross += trends[1]['percent correct']

            cumulative_days_golden_cross += trends[0]['average days']
            cumulative_days_death_cross += trends[1]['average days']

            stock_count += 1

            print('Ticker ' + '{}'.format(ticker).rstrip() + ' done. ' + 'Count: ' + str(stock_count - 1))
        else:
            break
    except:
        print('Exception: ' + 'Ticker: ' + '{}'.format(ticker).rstrip() + '\n')

overall_golden_cross_percent_correct = cumulative_percent_correct_golden_cross / (stock_count - 1)
overall_percent_correct_death_cross = cumulative_percent_correct_death_cross / (stock_count - 1)
overall_days_golden_cross = cumulative_days_golden_cross / (stock_count - 1)
overall_days_death_cross = cumulative_days_death_cross / (stock_count - 1)

print('SP500 Percent Correct Golden Cross: ' + str(overall_golden_cross_percent_correct) + '\n')
print('SP500 Percent Correct Death Cross: ' + str(overall_percent_correct_death_cross) + '\n')

#print('SP500 Buy to Sell Average Days (Golden Cross): ' + str(overall_days_golden_cross) + '\n')
#print('SP500 Sell to Buy Average Days (Death Cross): ' + str(overall_days_death_cross) + '\n')

'''

# well perfoming
run_stock('AAPL')
'''
#run_stock('GOOGL')
run_stock('MNST')

# poor performing
run_stock('AIG')
run_stock('XRX')

# mediocre
run_stock('RF')
run_stock('IPG')

run_stock('AMZN')
run_stock('AVP')
run_stock('WU')
run_stock('M')

'''


