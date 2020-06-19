# encoding: UTF-8

"""
DualThrust交易策略 by Leon
"""

from datetime import time
import talib
from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtConstant import EMPTY_STRING
from vnpy.trader.app.ctaStrategy.ctaTemplate import CtaTemplate, BarGenerator, ArrayManager
from sqlalchemy.sql.expression import false
from vnpy.trader.app.LeonOrderLog.leonlogengine import persisttrade


########################################################################
class DT_IntraDayLongStrategy(CtaTemplate):
    """DualThrust交易策略"""
    className = 'DT_IntraDayLongStrategy'
    author = u'Leon Zhao'

    # 策略参数
    fixedSize = 1
    k1 = 0.4
    k2 = 0.4

    rangeDays = 4
    initDays = 30  # original value is 10
    atrDays = 20

    # 策略变量
    barList = []  # K线对象的列表

    dayOpen = 0
    rangeHigh = 0
    rangeLow = 0
    rangeHighClose = 0
    rangeLowClose = 0
    range1 = 0
    range2 = 0
    rsiconfig = 50
    rsilen = 21

    range = 0
    longEntry = 0
    shortEntry = 0
    exitTime = time(hour=15, minute=20)  # will not cover position when day close

    longEntered = False
    shortEntered = False

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'k1',
                 'k2']

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'range',
               'longEntry',
               'shortEntry',
               'exitTime']
    longEntry1 = 0
    shortEntry1 = 0
    # 同步列表，保存了需要保存到数据库的变量名称
    syncList = ['pos', 'range', 'longEntry1', 'shortEntry1']

    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(DT_IntraDayLongStrategy, self).__init__(ctaEngine, setting)

        self.bg = BarGenerator(self.onBar, onDayBar=self.ondayBar, vtSymbol=self.vtSymbol)
        self.am = ArrayManager()
        self.barList = []
        self.longEntry1 = 0
        self.shortEntry1 = 0
        # Read Parameters from Setting files
        if 'strParams' in setting:
            self.params = setting['strParams']
            if len(self.params) >= 3:
                for p in self.params:
                    if p[0] == 'unit':
                        self.fixedSize = p[1]
                    if p[0] == 'p1':
                        self.k1 = p[1]
                    if p[0] == 'p2':
                        self.k2 = p[1]
                    if p[0] == 'p3':
                        self.rangeDays = p[1]
                    if p[0] == 'p4':
                        self.atrDays = p[1]
                    if p[0] == 'p5':
                        self.initDays = p[1]
                    if p[0] == 'p6':
                        self.rsilen = p[1]
                    if p[0] == 'p7':
                        self.rsiconfig = p[1]


        else:
            # 策略参数
            self.fixedSize = 1
            self.k1 = 0.4
            self.k2 = 0.4

            self.rangeDays = 4
            self.atrDays = 20
            self.initDays = 55  # original value is 10
            self.rsiconfig = 50
            self.rsilen = 21
        # print(self.fixedSize,self.k1,self.k2,self.rangeDays,self.initDays)
        self.dayOpen = 0
        self.rangeHigh = 0
        self.rangeLow = 0
        self.rangeHighClose = 0
        self.rangeLowClose = 0
        self.range1 = 0
        self.range2 = 0
        self.atrValue = 0

        self.range = 0
        self.longEntry = 0
        self.shortEntry = 0
        self.exitTime = time(hour=15, minute=20)  # will not cover position when day close
        self.longEntered = False
        self.shortEntered = False
        self.rsival = 1000

        self.loginterval = 15
        self.logcountdown = 0


    # ----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' % self.name)

        # 载入历史数据，并采用回放计算的方式初始化策略数值
        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)

        self.putEvent()

    # ----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略启动' % self.name)
        self.putEvent()

    # ----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略停止' % self.name)
        self.putEvent()

    # ----------------------------------------------------------------------
    def writeKeyValue(self):
        """Update long short entry price（必须由用户继承实现）"""
        #print("write key")
        if self.logcountdown > self.loginterval:
            self.logcountdown = 0
            outstr = "Symbol("+self.vtSymbol+")Long Entry:"
            outstr = outstr + str(round(self.longEntry,2)) + ", Short Entry:" + str(round(self.shortEntry,2))
            self.writeCtaLog(u'%s' %outstr )
        self.logcountdown += 1
        self.putEvent()

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        # ignore data before real open
        if (tick.datetime.hour == 8 or tick.datetime.hour == 20):
            return
        self.bg.updateTick(tick)

    def calcUnitNo(self, atr, fixSize):
        dtCap = 0.0
        defaultCap = 0.0
        unitNo = 0
        cust = []
        var_sizelist = CtaTemplate.vol_Size
        var_size = 0.0
        var_Symbol = ""
        if len(var_sizelist) == 0:
            return fixSize
        else:
            var_Symbol = var_Symbol.join(list(filter(lambda x: x.isalpha(), self.vtSymbol)))
            var_size = float(var_sizelist[var_Symbol][0])
            if var_size - 0 < 0.01:
                return fixSize

        var_temp = 0.0
        if len(CtaTemplate.cust_Setting) > 0:
            cust = CtaTemplate.cust_Setting
        for cs in cust:
            if cs["StrategyGroup"] == "DT" and cs["Status"] == 'True':
                dtCap = cs["CaptialAmt"]
                break
            if cs["StrategyGroup"] == "Default" and cs["Status"] == 'True':
                defaultCap = cs["CaptialAmt"]
        if dtCap > 0:
            self.capConfig = float(dtCap)
        elif defaultCap > 0:
            self.capConfig = float(defaultCap)
        else:
            self.capConfig = 0.0

        unitNo = 0
        if self.capConfig - 0 < 0.0001:
            unitNo = fixSize
        elif var_size - 0 < 0.001:
            unitNo = fixSize
        else:
            unitNo = int(self.capConfig * 0.0088 / (atr * var_size))
        if unitNo < 1:
            unitNo = 1
        return unitNo

        # ---------calcuate range for the last several days

    def calcRange(self):
        if self.am.count >= self.atrDays + 1:
            self.atrValue = self.am.atr(self.atrDays, False)
            if self.atrValue > 0:
                self.fixedSize = self.calcUnitNo(self.atrValue, self.fixedSize)
            self.rangeHigh = talib.MAX(self.am.high, self.rangeDays)[-1]
            self.rangeLow = talib.MIN(self.am.low, self.rangeDays)[-1]
            self.rangeHighClose = talib.MAX(self.am.close, self.rangeDays)[-1]
            self.rangeLowClose = talib.MIN(self.am.close, self.rangeDays)[-1]
            self.range1 = self.rangeHigh - self.rangeLowClose
            self.range2 = self.rangeHighClose - self.rangeLow
            #self.rsival = self.am.rsi(self.rsilen, array=False)

            tlen = len(self.am.closeArray)-self.rsilen-2
            rsi1 = talib.RSI(self.am.closeArray[tlen:], timeperiod=self.rsilen)
            self.rsival = rsi1[-1]
            #print("rsi array", rsi1)

            #print("\n\rthe rsi is:", rsi1[-1])

            # print(self.rangeHigh,self.rangeLow)
            if (self.range1 > self.range2):
                calcRange = self.range1
            else:
                calcRange = self.range2
        else:
            calcRange = 0
        return calcRange

        # ----------------------------------------------------------------------

    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        if self.reduceCountdown() > 0:
            return
        # 撤销之前发出的尚未成交的委托（包括限价单和停止单）
        self.cancelAll()

        self.bg.updateBar(bar)
        barLength = 0
        barLength = max(self.atrDays, self.rangeDays) + 1
        if self.am.count < barLength:
            return
            # 计算指标数值
        self.barList.append(bar)

        if len(self.barList) <= 2:
            return
        else:
            self.barList.pop(0)
        lastBar = self.barList[-2]

        # 新的一天
        # for commodity trade at night 9 also need because some day night is canncel due to holiday
        if (lastBar.datetime.hour == 15 or lastBar.datetime.hour == 14) and (
        (bar.datetime.hour == 21 or bar.datetime.hour == 9)):
            # for commodity not trade at night:
            # if (lastBar.datetime.hour == 15 or lastBar.datetime.hour==14 and lastBar.datetime.minute==59) and ((bar.datetime.hour == 9)  ):
            # 如果已经初始化
            self.range = self.calcRange()
            # old logic, use current open
            #self.dayOpen = bar.open
            # New logic, use yesterday close, since I skip first two minutes, cause differ from back test
            self.dayOpen = self.am.close
            if self.range:
                self.longEntry = bar.open + self.k1 * self.range
                self.shortEntry = bar.open - self.k2 * self.range

                # self.longEntered = False
            # self.shortEntered = False
        else:
            pass

        # 尚未到收盘
        if not self.range:
            self.range = self.calcRange()
            self.dayOpen = bar.open
            if self.range:
                self.longEntry = bar.open + self.k1 * self.range
                self.shortEntry = bar.open - self.k2 * self.range

        if (self.range == 0):
            # print(self.k1,self.k2,self.range,"b",self.longEntry,"c",bar.open,bar.datetime)
            self.writeCtaLog(u'Range eq 0 , need to check')
        if abs(self.rsival) > 100:
            self.writeCtaLog(u'RSI large than 100, need to check')

        if True:  # Trade Time, no matter when, just send signal
            #print("DT Long:", self.longEntry, self.shortEntry, self.rsival)
            if self.pos == 0:
                self.longEntered = False
                self.shortEntered = False
                if bar.close > self.longEntry and self.rsival >= self.rsiconfig:
                    # if not self.longEntered:
                    # self.buy(self.longEntry + 2, self.fixedSize)
                    self.buy(bar.close, self.fixedSize)
                else:
                    pass
            # 持有多头仓位
            elif self.pos > 0:
                self.longEntered = True
                self.shortEntered = False
                # 多头止损单
                if bar.close < self.shortEntry:
                    # self.sell(self.shortEntry -2 , self.fixedSize)
                    self.sell(bar.close, abs(self.pos))

            # 持有空头仓位
            elif self.pos < 0:
                print("somethong wrong, there should have no short position!")
            else:
                pass

        # 收盘平仓 This will not execute
        else:
            pass

        self.writeKeyValue()

        # 发出状态更新事件
        self.putEvent()

    # update day chart
    def ondayBar(self, dayBar):
        """收到日线推送（必须由用户继承实现）"""
        self.am.updateBar(dayBar)
        self.range = None
        self.dayOpen = 0
        # 发出状态更新事件
        self.putEvent()
        # ----------------------------------------------------------------------

    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    # ----------------------------------------------------------------------
    def onTrade(self, trade):
        # 发出状态更新事件
        persisttrade(self.vtSymbol, self.className, trade)
        self.putEvent()

    # ----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        pass
