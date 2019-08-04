# encoding: UTF-8

"""
Turtle Strategy by Leon 
"""

from datetime import time,datetime
import talib
from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtConstant import EMPTY_STRING
from vnpy.trader.vtConstant import (DIRECTION_LONG, DIRECTION_SHORT,
                                    OFFSET_OPEN, OFFSET_CLOSE,
                                    STATUS_ALLTRADED, STATUS_CANCELLED, STATUS_REJECTED) 
from vnpy.trader.app.ctaStrategy.ctaTemplate import CtaTemplate, BarGenerator , ArrayManager
from vnpy.trader.language.chinese.constant import OFFSET_CLOSETODAY
from bokeh.themes import default



########################################################################
class TurtleUseCloseStrategy(CtaTemplate):
    """Turtle交易策略"""
    className = 'TurtleUseCloseStrategy'
    author = u'Leon Zhao'

    # 策略参数

    fixedSize = 1
    longDays = 20
    shortDays = 20
    longExitDays = 10
    shortExitDays = 10
    initDays = 35    
    atrDays = 20
    exitAtr = 2

    # 策略变量
    barList = []                # K线对象的列表

    newTradeDay = False
    lastLongEntry = 0
    lastLongTime = 0
    lastShortEntry = 0
    lastShortTime = 0
    upperChannel = 0
    lowerChannel = 0
    longEntry = 0
    shortEntry = 0
    entryPrice = 0
    entryDirection = 0 
    entryUsage = 'Turtle'
    entryUnitNo = 0
    longExit = 0
    shortExit = 0
    longAtrExit = 0
    shortAtrExit = 0
    longChannelExit = 0
    shortChannelExit = 0
    atrValue = 0
    entryAtr = 0
    rangeLow = 0
    exitTime = time(hour=15, minute=20) #will not cover position when day close

    longEntered = False
    shortEntered = False
    
    capConfig = 0.0
    onTradeCnt = 0
    previousTrade = 0
    bookTime = datetime.now()
    

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'longDays',
                 'shortDays']    

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'longEntry',
               'shortEntry',
               'exitTime',
               'upperChannel',
               'lowerChannel'] 
    
    # 同步列表，保存了需要保存到数据库的变量名称
    syncList = ['pos','entryPrice','entryDirection','entryUsage','entryUnitNo','lastLongEntry','lastShortEntry','entryAtr']    

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(TurtleUseCloseStrategy, self).__init__(ctaEngine, setting) 
        
        self.bg = BarGenerator(self.onBar,onDayBar = self.ondayBar,vtSymbol=self.vtSymbol)
        #self.am = ArrayManager(max(self.longDays,self.shortDays,self.atrDays)+1)
        self.barList = []
        if 'strParams' in setting:
            self.params = setting['strParams']
            if len(self.params)>=3:
                for p in self.params:
                    if p[0] == 'unit':
                        self.fixedSize = p[1]
                    if p[0] == 'p1':
                        self.longDays = p[1]
                    if p[0] == 'p2':
                        self.shortDays= p[1]
                    if p[0] == 'p3':
                        self.longExitDays = p[1]
                    if p[0] == 'p4':
                        self.shortExitDays = p[1]                        
                    if p[0] == 'p5':
                        self.initDays = p[1]  
        else:
            # 策略参数
            self.fixedSize = 1
            self.longDays = 20
            self.shortDays = 20
            self.longExitDays = 10
            self.shortExitDays = 10
            self.initDays = 35             
  
        #print("ma debug:",self.fixedSize,self.longDays,self.shortDays,self.longExitDays,self.shortExitDays,self.initDays)             
        # Use class variant should be OK, however, to be save just instance them.
        self.newTradeDay = False
        self.lastLongEntry = 0
        self.lastLongTime = 0
        self.lastShortEntry = 0
        self.lastShortTime = 0
        self.upperChannel = 0
        self.lowerChannel = 0
        self.longEntry = 0
        self.shortEntry = 0
        self.entryPrice = 0
        self.entryDirection = 0 
        self.entryUsage = 'Turtle'
        self.entryUnitNo = 0
        self.longExit = 0
        self.shortExit = 0
        self.longAtrExit = 0
        self.shortAtrExit = 0
        self.longChannelExit = 0
        self.shortChannelExit = 0
        self.atrValue = 0
        self.entryAtr = 0
        self.rangeLow = 0
        self.exitTime = time(hour=15, minute=20) #will not cover position when day close
    
        self.longEntered = False
        self.shortEntered = False
        
        self.capConfig = 0.0
        self.onTradeCnt = 0
        self.bookTime = datetime.now()
        self.am = ArrayManager(max(self.longDays,self.shortDays,self.atrDays)+1)        
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
        # No need to add calculation of the Turtle Channel on Start, it may not change over days.
        #self.calcPrepare()
        self.readLastTrade()
        self.putEvent()

    def readLastTrade(self):
        #read last trade data from database
        #In fact no need after I persist those two values.
        if self.pos > 0 :
            self.lastLongEntry = self.entryPrice
            self.lastShortEntry = 0
        elif self.pos < 0 :
            self.lastShortEntry = self.entryPrice    
            self.lastLongEntry = 0
        pass
    def calcUnitNo(self,atr,fixSize):
        turtleCap = 0.0
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
            if cs["StrategyGroup"] == "Turtle" and cs["Status"] == 'True':
                turtleCap = cs["CaptialAmt"]
                break
            if cs["StrategyGroup"] == "Default" and cs["Status"] == 'True':
                defaultCap = cs["CaptialAmt"]
        if turtleCap > 0:
            self.capConfig = float(turtleCap)
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
            unitNo = int(self.capConfig * 0.005 /(atr*var_size))
            
        if unitNo < 1:
            unitNo = 1    
        return unitNo    
            
    def calcPrepare(self):
        #calculate initials of the strategy
        barLength = 0 
        barLength = max(self.longDays,self.shortDays,self.atrDays) 
        if self.am.count < barLength + 1:
            return   
        #self.atrValue = talib.ATR(self.am.high, self.am.low, self.am.close,self.atrDays)[-1] 
        self.atrValue = self.am.atr(self.atrDays,False)
        # = atrLine[-1]
        if self.atrValue > 0 :
            self.fixedSize = self.calcUnitNo(self.atrValue, self.fixedSize)
            #call method to calc unit
        self.upperChannel = talib.MAX(self.am.close,self.longDays)[-1]
        self.lowerChannel = talib.MIN(self.am.close,self.shortDays)[-1]
        self.longChannelExit = talib.MIN(self.am.close,self.longExitDays)[-1]
        self.shortChannelExit = talib.MAX(self.am.close,self.shortExitDays)[-1]

    def calcKPI(self):    
        if self.pos>0:
                self.longAtrExit = int(self.lastLongEntry - 2*self.entryAtr)
                if self.longAtrExit > self.longChannelExit:
                    self.longExit = self.longAtrExit
                else:
                    self.longExit = self.longChannelExit
                                 
                if self.entryUnitNo == 1:
                    self.longEntry = int(self.lastLongEntry + self.entryAtr)
                elif self.entryUnitNo == 2:
                    self.longEntry = int(self.lastLongEntry +0.5*self.entryAtr)
                else:
                    self.longEntry = 0
        elif self.pos == 0:
                self.longEntry = self.upperChannel
                self.shortEntry = self.lowerChannel
        else:
            self.shortAtrExit = int(self.lastShortEntry + 2*self.entryAtr)
            if self.shortAtrExit < self.shortChannelExit:
                self.shortExit = self.shortAtrExit
            else:
                self.shortExit = self.shortChannelExit
            if self.entryUnitNo == 1:
                self.shortEntry = int(self.lastShortEntry-self.entryAtr)
            elif self.entryUnitNo == 2:
                self.shortEntry = int(self.lastShortEntry-0.5*self.entryAtr)
            else:
                self.shortEntry = 0
             
          
    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略停止' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        self.bg.updateTick(tick)          
        
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        # 撤销之前发出的尚未成交的委托（包括限价单和停止单）
        self.cancelAll()

        self.bg.updateBar(bar)
              
        barLength = 0 
        barLength = max(self.longDays,self.shortDays,self.atrDays) 

        if self.am.count < barLength + 1:
            return              
        # 计算指标数值
        self.barList.append(bar)
        
        if len(self.barList) <= 2:
            return
        else:
            self.barList.pop(0)
        lastBar = self.barList[-2]
        
        # 新的一天
        if (lastBar.datetime.hour == 15 or lastBar.datetime.hour==14 ) and ((bar.datetime.hour == 21) or (bar.datetime.hour == 9)):
            # 如果已经初始化
            if not self.upperChannel :
                #do things:
                self.calcPrepare()
            else:
                pass
            
        if self.pos == 0:
            self.lastLongTime = 0
            self.lastShortTime = 0
            self.entryUnitNo = 0
            self.entryAtr = self.atrValue
        self.calcKPI()
        
        if self.pos > 0:
            #self.sell(self.longExit,self.fixedSize,stop)
            if  bar.close < self.longExit:
                self.sell(bar.close,abs(self.pos))
            elif bar.close > self.longEntry and self.longEntry > 0 :
                self.onTradeCnt = 0
                self.buy(bar.close,self.fixedSize)
                #self.bookTime = datetime.now()
                
            else:
                pass
        elif self.pos == 0:
            #self.entryUnitNo = 0
            if bar.close > self.longEntry and self.longEntry > 0 :
                self.onTradeCnt = 0
                self.buy(bar.close,self.fixedSize)
                #self.bookTime = datetime.now()
                #self.onTradeCnt = 0                
            elif bar.close < self.shortEntry and self.shortEntry > 0:
                self.onTradeCnt = 0
                self.short(bar.close , self.fixedSize)
                #self.bookTime = datetime.now()
                #self.onTradeCnt = 0                
            else:
                pass
        else:
            if bar.close < self.shortEntry and self.shortEntry > 0 :
                self.onTradeCnt = 0
                self.short(bar.close,self.fixedSize)
                #self.bookTime = datetime.now()
                #self.onTradeCnt = 0                
            elif bar.close > self.shortExit:
                self.cover(bar.close,abs(self.pos))
            else:
                pass                        

        # 发出状态更新事件
        self.putEvent()
    #update day chart
    def ondayBar(self, dayBar):
        """收到日线推送（必须由用户继承实现）"""
        self.am.updateBar(dayBar)
        self.calcPrepare()
        # 发出状态更新事件
        self.putEvent() 
    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        #if order.status == STATUS_ALLTRADED and self.pos != 0:
            # How do I know the last trade is open or exit?
        #    self.entryUnitNo = self.entryUnitNo + 1

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        # 发出状态更新事件
        if trade.direction == DIRECTION_LONG and trade.offset == OFFSET_OPEN:
            if (trade.volume + self.onTradeCnt) == self.fixedSize:
                self.entryUnitNo = self.entryUnitNo + 1
            else:
                self.onTradeCnt = trade.volume + self.onTradeCnt
                self.writeCtaLog(u'%s: 部分成交， 进场次数未累加，注意！' %self.name)
                    
            self.lastLongEntry = trade.price
            self.entryPrice = trade.price
            self.entryDirection = DIRECTION_LONG     
            self.entryAtr = self.atrValue       
        elif trade.direction == DIRECTION_SHORT and trade.offset == OFFSET_OPEN:
            if  (trade.volume + self.onTradeCnt) == self.fixedSize:            
                self.entryUnitNo = self.entryUnitNo + 1
            else:
                self.onTradeCnt = trade.volume + self.onTradeCnt
                self.writeCtaLog(u'%s: 部分成交， 进场次数未累加，注意！' %self.name)                
            self.lastShortEntry = trade.price  
            self.entryPrice = trade.price
            self.entryDirection = DIRECTION_SHORT 
            self.entryAtr = self.atrValue                       
        elif (trade.offset == OFFSET_CLOSE or trade.offset == OFFSET_CLOSETODAY ):
            #print(self.pos)
            self.entryUnitNo = 0
            self.lastLongEntry = 0
            self.lastShortEntry = 0
            self.entryPrice = 0
            self.entryDirection = OFFSET_CLOSE            
        else:
            pass
        self.putEvent()

    #----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        pass
