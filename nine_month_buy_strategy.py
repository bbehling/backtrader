import sys
from datetime import datetime

from bs4 import BeautifulSoup
import numpy
import pandas as pd
import requests

import backtrader as bt
import pprint
from dateutil import relativedelta

golden_crosses = []
has_golden_cross = False

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

    def __init__(self):
        sma1 = bt.ind.SMA(period=self.p.pfast)  # fast moving average
        sma2 = bt.ind.SMA(period=self.p.pslow)  # slow moving average
        self.crossover = bt.ind.CrossOver(sma1, sma2)  # crossover signal
        self.buy_date = 0

    def next(self):
        global golden_crosses
        global has_golden_cross
        r = relativedelta.relativedelta(self.datetime.date(ago=0), self.buy_date)

        if not self.position:  # not in the market
            if self.crossover > 0:  # if fast crosses slow to the upside
                self.buy()  # enter long

                self.buy_date = self.datetime.date(ago=0)

                golden_crosses.append({"year": self.buy_date.year})
                has_golden_cross = True

        # close out at 9 months
        elif r.months == 9:
            self.close()  # close long position


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
            if r.months < 9:
                days.append(row)
            else:
                return days
        else:
            return days


def format_date(date):
    return date.split(" ")[0]


# At 9 months, look at the stock price. Is it more than the previous buy price? If so, its a valid buy
def calc_valid_buy(stream):
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

            price_at_9_months = days_after_buy[len(days_after_buy) - 1]['adjclose']
            valid_sell = price_at_9_months > buy_price

            values.append({'valid sell': valid_sell, 'buy date': buy_date,
                           'close price at buy': buy_price, 'price at 9 months': price_at_9_months, '9 month date': days_after_buy[len(days_after_buy) - 1]['datetime']})

    trends['title'] = stream.columns[1]
    trends['values'] = values

    return trends

# count how many golden crosses per year
def aggregate_golden_crosses():
    global golden_crosses
    years = {}
    for golden_cross in golden_crosses:

        if golden_cross["year"] in years.keys():
            years[golden_cross["year"]] += 1
        else:
            years[golden_cross["year"]] = 1

    return years


def validate_trends(trends):
    total_true = 0.0
    total_trends = len(trends['values']) + .0
    for trend in trends['values']:
        if trend['valid sell']:
            total_true += 1

    percent_correct = total_true / total_trends
    trends['percent correct'] = percent_correct


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
    trends_golden_cross = calc_valid_buy(df)

    validate_trends(trends_golden_cross)


    pp = pprint.PrettyPrinter(indent=1)
    print('\n9 Month buy strategy:')

    pp.pprint(trends_golden_cross)
    pp.pprint(trends_golden_cross['title'])
    pp.pprint(trends_golden_cross['percent correct'])

    global has_golden_cross

    #if has_golden_cross:
        #cerebro.plot()  # and plot it with a single command

    return trends_golden_cross

'''
sp500_stocks = get_sp500()
stock_count = 1
cumulative_percent_correct_golden_cross = 0.0

for ticker, cik in sp500_stocks.items():
    try:
        if stock_count < 600:
            trends = run_stock('{}'.format(ticker).rstrip())
            cumulative_percent_correct_golden_cross += trends['percent correct']

            stock_count += 1

            print('Ticker ' + '{}'.format(ticker).rstrip() + ' done. ' + 'Count: ' + str(stock_count - 1))
        else:
            break
    except Exception as e:
        print('Exception: ' + 'Ticker: ' + '{}'.format(ticker).rstrip() + '\n')
        print(e)

overall_golden_cross_percent_correct = cumulative_percent_correct_golden_cross / (stock_count - 1)


print('SP500 Percent Correct Golden Cross: ' + str(overall_golden_cross_percent_correct) + '\n')
year_aggregate = aggregate_golden_crosses()
print('Total golden crosses: ' + '\n')
print(year_aggregate)
'''


# well perfoming
run_stock('AAPL')

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
run_stock('SBUX')




