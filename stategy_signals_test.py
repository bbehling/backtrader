from datetime import datetime
import backtrader as bt
import backtrader.indicators as btind


class MySignal(bt.Indicator):
    lines = ('signal',)
    params = (('period', 30),)

    def __init__(self):
        self.lines.signal = self.data - bt.indicators.SMA(period=self.p.period)


cerebro = bt.Cerebro()  # create a "Cerebro" engine instance

# Create a data feed
data = bt.feeds.YahooFinanceData(dataname='AAPL',
                                 fromdate=datetime(2016, 1, 1),
                                 todate=datetime(2019, 5, 31))
cerebro.adddata(data)

cerebro.add_signal(bt.SIGNAL_LONGSHORT, MySignal)
cerebro.addwriter(bt.WriterFile, csv=True, out='test_file.csv')
result = cerebro.run()

# print(result)
cerebro.plot()
