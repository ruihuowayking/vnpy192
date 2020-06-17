# encoding: UTF-8

"""
DualThrust交易策略 by Leon 
"""

from datetime import time
import talib
from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtConstant import EMPTY_STRING
from vnpy.trader.app.ctaStrategy.ctaTemplate import CtaTemplate, BarGenerator, ArrayManager
from vnpy.trader.app.LeonOrderLog.leonlogengine import persisttrade
from sqlalchemy.sql.expression import false
import numpy as np


########################################################################
class KeltnerCommonStrategy(CtaTemplate):
    """DualThrust交易策略"""
    className = 'KeltnerCommonStrategy'
    author = u'Leon Zhao'

    # 策略参数
    fixedSize = 1
    kUpper = 2
    kLower = 2
    
    maDays = 13
    atrDays = 20   # I may use the average of ATR to reduce the range
    initDays = 100 # original value is 10    
    kExit = 0.5


    # 策略变量
    barList = []                # K线对象的列表

    atrAvg = 0
    maHigh = 0
    maLow = 0
    longEntry = 0
    shortEntry = 0
    longExit = 0
    shortExit = 0
    rsiconfig = 50
    rsilen = 21

    #exitTime = time(hour=15, minute=20) #will not cover position when day close

    longEntered = False
    shortEntered = False

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'kUpper',
                 'kLower',
                 'maDays']    

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'atrAvg',
               'longEntry',
               'shortEntry'] 
    
    # 同步列表，保存了需要保存到数据库的变量名称
    syncList = ['pos','atrAvg','longEntry','shortEntry']    

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(KeltnerCommonStrategy, self).__init__(ctaEngine, setting) 
        
        self.bg = BarGenerator(self.onBar,onDayBar = self.ondayBar,vtSymbol =self.vtSymbol)
        self.am = ArrayManager()
        self.barList = []
        # Read Parameters from Setting files
        if 'strParams' in setting:
            self.params = setting['strParams']
            if len(self.params)>=3:
                for p in self.params:
                    if p[0] == 'unit':
                        self.fixedSize = p[1]
                    if p[0] == 'p1':
                        self.kUpper = p[1]
                    if p[0] == 'p2':
                        self.kLower = p[1]
                    if p[0] == 'p3':
                        self.maDays = p[1]
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
            self.kUpper = 2
            self.kLower = 2
            
            self.maDays = 13
            self.atrDays = 20
            self.initDays = 55 # original value is 10  
            self.rsiconfig = 50
            self.rsilen = 21
        #print(self.fixedSize,self.kUpper,self.kLower,self.maDays,self.initDays)             
        self.atrAvg = 0
        self.maHigh = 0
        self.maLow = 0
        self.longEntry = 0
        self.shortEntry = 0
        self.longExit = 0
        self.shortExit = 0
    
        #exitTime = time(hour=15, minute=20) #will not cover position when day close
    
        self.longEntered = False
        self.shortEntered = False

        self.loginterval = 15
        self.logcountdown = 0

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

    # ----------------------------------------------------------------------
    def writeKeyValue(self):
        """Update long short entry price（必须由用户继承实现）"""
        #print("write key")
        if self.logcountdown > self.loginterval:
            self.logcountdown = 0
            outstr = "Symbol("+self.vtSymbol+")Long Entry:"
            outstr = outstr + str(self.longEntry) + ", Short Entry:" + str(self.shortEntry)
            self.writeCtaLog(u'%s' %outstr )
        self.logcountdown += 1
        self.putEvent()

    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        #ignore data before real open
        if (tick.datetime.hour == 8 or tick.datetime.hour ==20):
            return
        self.bg.updateTick(tick)

    def keltner(self, n, dev, ret_array=False):
        """肯特纳通道"""
        mid = self.sma(n, ret_array)
        atr = self.atr(n, ret_array)

        up = mid + atr * dev
        down = mid - atr * dev

        return up, down
    def calcUnitNo(self,atr,fixSize):
        keltnerCap = 0.0
        defaultCap = 0.0
        unitNo = 0
        cust = []
        var_sizelist = CtaTemplate.vol_Size
        var_size = 0.0
        var_Symbol = ""
        if len(var_sizelist) == 0:
            return fixSize
        else:
            var_Symbol = var_Symbol.join(list(filter(lambda x: x.isalpha(),self.vtSymbol)))            
            var_size = float(var_sizelist[var_Symbol][0])
            if var_size -0 < 0.01:
                return fixSize
        
        var_temp = 0.0
        if len(CtaTemplate.cust_Setting) > 0:
            cust = CtaTemplate.cust_Setting
        for cs in cust:
            if cs["StrategyGroup"] == "Keltner" and cs["Status"] == 'True':
                keltnerCap = cs["CaptialAmt"]
                break
            if cs["StrategyGroup"] == "Default" and cs["Status"] == 'True':
                defaultCap = cs["CaptialAmt"]
        if keltnerCap > 0:
            self.capConfig = float(keltnerCap)
        elif defaultCap > 0 :
            self.capConfig = float(defaultCap)
        else:
            self.capConfig = 0.0
        
        unitNo = 0
        if self.capConfig -0 < 0.0001:
            unitNo = fixSize
        elif var_size - 0 < 0.001:
            unitNo = fixSize
        else:
            unitNo = int(self.capConfig * 0.0066 /(atr*var_size))
        if unitNo < 1:
            unitNo = 1
        return unitNo    
        
    #---------calcuate range for the last several days 
    def calcKPI(self):
        if self.am.count >= self.maDays :
            self.atrAvg = self.am.atr(self.atrDays,False)
            if self.atrAvg > 0 :
                self.fixedSize = self.calcUnitNo(self.atrAvg, self.fixedSize)          
            hval = self.am.highArray
            lval = self.am.lowArray
            cval = self.am.closeArray
            meanval = [(h+l+c)/3 for h , l, c in zip(hval, lval, cval)]
            sidx = len(meanval)-self.maDays
            self.emamean = np.mean(meanval[sidx:])
            #self.emamean = self.am.ema(meanval, array=False)

            tlen = len(self.am.closeArray) - self.rsilen - 2
            rsi1 = talib.RSI(self.am.closeArray[tlen:], timeperiod=self.rsilen)
            self.rsival = rsi1[-1]

            self.longEntry = self.emamean + self.atrAvg * self.kUpper
            self.shortEntry = self.emamean - self.atrAvg * self.kLower
            self.longExit = self.emamean
            self.shortExit = self.emamean

    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        if self.reduceCountdown() > 0:
            return
        # 撤销之前发出的尚未成交的委托（包括限价单和停止单）
        self.cancelAll()

        self.bg.updateBar(bar)

        barLength = 0
        barLength = max(self.atrDays,self.maDays)   + 1 
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
        #for commodity trade at night 9 also need because some day night is canncel due to holiday
        if (lastBar.datetime.hour == 15 or lastBar.datetime.hour==14)  and ((bar.datetime.hour == 21 or bar.datetime.hour == 9)  ):
        #for commodity not trade at night:
        #if (lastBar.datetime.hour == 15 or lastBar.datetime.hour==14 and lastBar.datetime.minute==59) and ((bar.datetime.hour == 9)  ):
            # 如果已经初始化
            self.range = self.calcKPI()
            self.dayOpen = bar.open
            #self.longEntered = False
            #self.shortEntered = False
        else:
            pass

        # 尚未到收盘
        if self.maHigh < 1:
            self.calcKPI()
        if (self.longEntry < self.emamean ) or (self.shortEntry > self.emamean) or (abs(self.rsival) > 100):
            #print(self.kUpper,self.kLower,self.range,"b",self.longEntry,"c",bar.open,bar.datetime)
            self.writeCtaLog(u'long Entry less than MA or vice vesa , or RSI wrong, need to check')
            return
        
        if True: # Trade Time, no matter when, just send signal
            #print("KK:", self.longEntry, self.shortEntry, self.rsival)
            if self.pos == 0:
                self.longEntered = False
                self.shortEntered = False                
                if bar.close > self.longEntry and self.rsival >= self.rsiconfig:
                    #if not self.longEntered:
                        #self.buy(self.longEntry + 2, self.fixedSize)
                        self.buy(bar.close,self.fixedSize)
                elif bar.close < self.shortEntry and self.rsival <= self.rsiconfig:
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
                if bar.close < self.longExit:
                    #self.sell(self.shortEntry -2 , self.fixedSize)
                    self.sell(bar.close,self.pos)
                    # 空头开仓单

            # 持有空头仓位
            elif self.pos < 0:
                self.shortEntered = True
                self.longEntered = False
                # 空头止损单
                if bar.close > self.longExit:
                    #self.cover(self.longEntry + 2, self.fixedSize)                
                    self.cover(bar.close,self.pos)

        # 收盘平仓 This will not execute
        else:
            if self.pos > 0:
                self.sell(bar.close * 0.99, abs(self.pos))
            elif self.pos < 0:
                self.cover(bar.close * 1.01, abs(self.pos))


        self.writeKeyValue()


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
        persisttrade(self.vtSymbol, self.className, trade)
        # 发出状态更新事件
        self.putEvent()

    #----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        pass
