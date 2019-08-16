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
class JDualThrust_IntraDayStrategy(CtaTemplate):
    """DualThrust交易策略"""
    className = 'JDualThrust_IntraDayStrategy'
    author = u'Leon Zhao'

    # 策略参数
    fixedSize = 1
    k1 = 0.4
    k2 = 0.4

    initDays = 30 # original value is 10
    rangeDays = 5

    # 策略变量
    barList = []                # K线对象的列表

    dayOpen = 0
    rangeHigh = 0
    rangeLow = 0
    rangeHighClose = 0
    rangeLowClose = 0
    range1 = 0
    range2 = 0
    
    range = 0
    longEntry = 0
    shortEntry = 0
    exitTime = time(hour=15, minute=20) #will not cover position when day close

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
    
    # 同步列表，保存了需要保存到数据库的变量名称
    syncList = ['pos']    

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(JDualThrust_IntraDayStrategy, self).__init__(ctaEngine, setting) 
        
        self.bg = BarGenerator(self.onBar,onDayBar = self.ondayBar)
        self.am = ArrayManager()
        self.barList = []

    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' %self.name)
    
        # 载入历史数据，并采用回放计算的方式初始化策略数值
        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)

        self.putEvent()

    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略启动' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略停止' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        self.bg.updateTick(tick)
    #---------calcuate range for the last several days 
    def calcRange(self):
        if self.am.count >= self.rangeDays :
            self.rangeHigh = talib.MAX(self.am.high,self.rangeDays)[-1]
            self.rangeLow =  talib.MIN(self.am.low,self.rangeDays)[-1]
            self.rangeHighClose = talib.MAX(self.am.close,self.rangeDays)[-1]
            self.rangeLowClose  = talib.MIN(self.am.close,self.rangeDays)[-1]
            self.range1 = self.rangeHigh-self.rangeLowClose
            self.range2 = self.rangeHighClose -self.rangeLow
            if (self.range1 > self.range2) :
                calcRange = self.range1
            else:
                calcRange = self.range2
        else:
            calcRange = 0
        return calcRange            
        
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        # 撤销之前发出的尚未成交的委托（包括限价单和停止单）
        self.cancelAll()

        self.bg.updateBar(bar)

        if self.am.count < self.rangeDays:
            return        
        # 计算指标数值
        self.barList.append(bar)
        
        if len(self.barList) <= 2:
            return
        else:
            self.barList.pop(0)
        lastBar = self.barList[-2]
        
        # 新的一天
        #for commodity trade at night 9 also need because some day night is canncel due to holiday
        if (lastBar.datetime.hour == 15 or lastBar.datetime.hour==14 ) and ((bar.datetime.hour == 21 or bar.datetime.hour == 9)  ):
        #for commodity not trade at night:
        #if (lastBar.datetime.hour == 15 or lastBar.datetime.hour==14 and lastBar.datetime.minute==59) and ((bar.datetime.hour == 9)  ):
            # 如果已经初始化
            self.range = self.calcRange()
            self.dayOpen = bar.open
            if self.range:
                self.longEntry = bar.open + self.k1 * self.range
                self.shortEntry = bar.open - self.k2 * self.range           

            #self.longEntered = False
            #self.shortEntered = False
        else:
            pass

        # 尚未到收盘
        if not self.range:
            self.range = self.calcRange()
            self.dayOpen = bar.open
            if self.range:
                self.longEntry = bar.open + self.k1 * self.range
                self.shortEntry = bar.open - self.k2 * self.range  

        if True: # Trade Time, no matter when, just send signal
            if self.pos == 0:
                self.longEntered = False
                self.shortEntered = False                
                if bar.close > self.longEntry :
                    #if not self.longEntered:
                        #self.buy(self.longEntry + 2, self.fixedSize)
                        self.buy(bar.close,self.fixedSize)
                elif bar.close < self.shortEntry:
                    #if not self.shortEntered:
                        #self.short(self.shortEntry - 2, self.fixedSize)
                        self.short(bar.close,self.fixedSize)
                else:
                    pass
                
    
            # 持有多头仓位
            elif self.pos > 0:
                self.longEntered = True
                self.shortEntered = False
                # 多头止损单
                if bar.close < self.shortEntry:
                    #self.sell(self.shortEntry -2 , self.fixedSize)
                    self.sell(bar.close,self.fixedSize)
                    # 空头开仓单
                    if not self.shortEntered:
                        #self.short(self.shortEntry -2 , self.fixedSize)
                        self.short(bar.close,self.fixedSize)
            # 持有空头仓位
            elif self.pos < 0:
                self.shortEntered = True
                self.longEntered = False
                # 空头止损单
                if bar.close > self.longEntry:
                    #self.cover(self.longEntry + 2, self.fixedSize)                
                    self.cover(bar.close,self.fixedSize)
                     # 多头开仓单
                    if not self.longEntered:
                        #self.buy(self.longEntry + 2, self.fixedSize)
                        self.buy(bar.close,self.fixedSize)
        # 收盘平仓 This will not execute
        else:
            if self.pos > 0:
                self.sell(bar.close * 0.99, abs(self.pos))
            elif self.pos < 0:
                self.cover(bar.close * 1.01, abs(self.pos))
 
        # 发出状态更新事件
        self.putEvent()
    #update day chart
    def ondayBar(self, dayBar):
        """收到日线推送（必须由用户继承实现）"""
        self.am.updateBar(dayBar)
        # 发出状态更新事件
        self.putEvent() 
    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        # 发出状态更新事件
        persisttrade(self.vtSymbol,self.className ,trade)        
        self.putEvent()

    #----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        pass
