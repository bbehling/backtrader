import sys
from datetime import datetime

from bs4 import BeautifulSoup
import requests
import backtrader as bt
from dateutil import relativedelta
import pymongo

golden_crosses = []
today_date = datetime.today()
client = pymongo.MongoClient("3.135.248.216", 27017)
db = client.strategies


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
        global db

        r = relativedelta.relativedelta(self.datetime.date(ago=0), self.buy_date)

        if not self.position:  # not in the market

            if self.crossover > 0:  # if fast crosses slow to the upside
                self.buy()  # enter long

                self.buy_date = self.datetime.date(ago=0)
                r = relativedelta.relativedelta(today_date, self.datetime.date(ago=0))

                # if golden cross has happened within 2 days, record it
                # TODO - if backtrader can get golden cross the same day, then change conditional to equal today's date
                if r.years == 0 and r.months == 0 and r.days <= 2:
                    db.golden_crosses.insert_one(
                        {'ticker': next(iter(self.positionsbyname)), "buyDate": str(self.buy_date)})

        # close out at 9 months
        elif r.months == 9:
            self.close()  # close long position


def format_date(date):
    return date.split(" ")[0]


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


def run_strategy(name):
    cerebro = bt.Cerebro()  # create a "Cerebro" engine instance
    # Create a data feed
    data = bt.feeds.YahooFinanceData(dataname=name,
                                     fromdate=datetime(1999, 1, 1),
                                     todate=datetime(2019, 12, 31))

    cerebro.adddata(data)  # Add the data feed

    cerebro.addstrategy(SmaCross)  # Add the trading strategy
    cerebro.addwriter(bt.WriterFile, csv=True, out='test_file.csv')

    cerebro.run()  # run it all


db.strategy_logs.insert_one({'status': 'Started Run', 'date': str(datetime.today())})

# get all stock tickers in sp500
sp500_stocks = get_sp500()
stock_count = 1

# for all tickers, run strategy
for ticker, cik in sp500_stocks.items():
    try:
        if stock_count < 600:  # for debugger purposes
            run_strategy('{}'.format(ticker).rstrip())

            stock_count += 1
            db.logs.insert_one(
                {'status': 'Ticker ' + '{}'.format(ticker).rstrip() + ' done. ', 'date': str(datetime.today())})
        else:
            break
    except Exception as e:
        db.logs.insert_one({'error': 'Exception: ' + 'Ticker: ' + '{}'.format(ticker).rstrip() + ' ' + str(e),
                                     'date': str(datetime.today())})

db.strategy_logs.insert_one({'status': 'Completed Run', 'date': str(datetime.today())})
