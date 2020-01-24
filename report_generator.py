from datetime import datetime

goldenCrosses = []
today_date = datetime.today().strftime('%Y-%m-%d')
body = ''


def sendreport(golden_crosses):
    getgoldencrosses(goldenCrosses)


def getgoldencrosses(golden_crosses):
    global body
    body = 'Golden Crosses for ' + today_date + '\n'
    for golden_cross in golden_crosses:
        body += 'Ticker: ' + golden_cross["ticker"]


def sendemail():
    test = 'send email'
