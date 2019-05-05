# encoding: UTF-8

"""
导入MC导出的CSV历史数据到MongoDB中
"""

from vnpy.trader.app.ctaStrategy.ctaBase import MINUTE_DB_NAME
from vnpy.trader.app.ctaStrategy.ctaHistoryData import loadMcCsv


if __name__ == '__main__':
    #loadMcCsv('IF0000_1min.csv', MINUTE_DB_NAME, 'IF0000')
    #loadMcCsv('rb0000_1min.csv', MINUTE_DB_NAME, 'rb0000')
     loadMcCsv('rb1905_1119.csv', MINUTE_DB_NAME, 'rb1905')
     loadMcCsv('ma1901_1119.csv', MINUTE_DB_NAME, 'MA901')
     loadMcCsv('ma1905_1119.csv', MINUTE_DB_NAME, 'MA905')
     loadMcCsv('sm1901_1119.csv', MINUTE_DB_NAME, 'SM901')
     loadMcCsv('sm1905_1119.csv', MINUTE_DB_NAME, 'SM905')
     loadMcCsv('sr1905_1119.csv', MINUTE_DB_NAME, 'SR905')
     loadMcCsv('ta1901_1119.csv', MINUTE_DB_NAME, 'TA901')
     loadMcCsv('ta1905_1119.csv', MINUTE_DB_NAME, 'TA905')
     loadMcCsv('i1901_1119.csv', MINUTE_DB_NAME, 'i1901')
     loadMcCsv('I1905_1119.csv', MINUTE_DB_NAME, 'i1905')
     loadMcCsv('j1901_1119.csv', MINUTE_DB_NAME, 'j1901')
     loadMcCsv('j1905_1119.csv', MINUTE_DB_NAME, 'j1905')
     loadMcCsv('jm1901_1119.csv', MINUTE_DB_NAME, 'jm1901')
     loadMcCsv('jm1905_1119.csv', MINUTE_DB_NAME, 'jm1905')
     loadMcCsv('l1901_1119.csv', MINUTE_DB_NAME, 'l1901')
     loadMcCsv('l1905_1119.csv', MINUTE_DB_NAME, 'l1905')
     loadMcCsv('p1901_1119.csv', MINUTE_DB_NAME, 'p1901')
     loadMcCsv('p1905_1119.csv', MINUTE_DB_NAME, 'p1905')
     loadMcCsv('pp1901_1119.csv', MINUTE_DB_NAME, 'pp1901')
     loadMcCsv('pp1905_1119.csv', MINUTE_DB_NAME, 'pp1905')
     loadMcCsv('y1905_1119.csv', MINUTE_DB_NAME, 'y1905')
     loadMcCsv('ag1906_1119.csv', MINUTE_DB_NAME, 'ag1906')
     loadMcCsv('hc1901_1119.csv', MINUTE_DB_NAME, 'hc1901')
     loadMcCsv('hc1905_1119.csv', MINUTE_DB_NAME, 'hc1905')
     loadMcCsv('ru1901_1119.csv', MINUTE_DB_NAME, 'ru1901')
     loadMcCsv('ru1905_1119.csv', MINUTE_DB_NAME, 'ru1905')
     loadMcCsv('sn1901_1119.csv', MINUTE_DB_NAME, 'sn1901')
     loadMcCsv('sn1905_1119.csv', MINUTE_DB_NAME, 'sn1905')

