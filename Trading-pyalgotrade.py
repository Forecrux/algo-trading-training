""" aaa
Strategy
    Long entry
        [over Fibonacci number] AND [rsi below 50] AND [price increase with volume high]
        OR
        [candle stick (try bullish engulfing first)] AND [rsi below 50] AND [price increase with volume high]

    Long exit
        [highest price decrease 10%  (e.g. buy at $100, increase to $200, sell if $180)]
        OR
        [price increase with rsi divergence and low volume]
        OR
        [price increase with rsi rearching 80 and low volume]
        OR
        [fill the gap (if Gap Up exist before)]
        OR
        [price keep higher but volume keep lower]

    Stop Long loss when
        [buying price decrease 10%  (e.g. buy at $100, sell if $90)]
    
    
Prerequisite
1. pip install pyalgotrade
2. https://mrjbq7.github.io/ta-lib/install.html
    
"""

from pyalgotrade import strategy
from pyalgotrade.barfeed import yahoofeed
from pyalgotrade.technical import ma
from pyalgotrade.tools import yahoofinance
from pyalgotrade.talibext import indicator
from pyalgotrade.technical import rsi
import numpy
import talib
import decimal


class MyStrategy(strategy.BacktestingStrategy):
    def __init__(self, feed, instrument, smaPeriod):
        strategy.BacktestingStrategy.__init__(self, feed, 1000)
        self.__position = None
        self.__instrument = instrument
        self.setUseAdjustedValues(True)
        self.__rsi = rsi.RSI(feed[instrument].getCloseDataSeries(), 14)
        self.stoplossprice=0
        self.longprice=0
        self.profit=0
        self.win=0
        self.loss=0  

    def onEnterOk(self, position):
        execInfo = position.getEntryOrder().getExecutionInfo()
        self.info("BUY at $%.2f" % (execInfo.getPrice()))

    def onEnterCanceled(self, position):
        self.__position = None

    def onExitOk(self, position):
        execInfo = position.getExitOrder().getExecutionInfo()
        self.info("SELL at $%.2f" % (execInfo.getPrice()))
        self.__position = None
        #calculate profit 
        self.profit+=execInfo.getPrice()-self.longprice
            
        if execInfo.getPrice()-self.longprice >0:
            self.win+=1
        else:
            self.loss+=1

    def onExitCanceled(self, position):
        # If the exit was canceled, re-submit it.
        self.__position.exitMarket()

    def onBars(self, bars):   
        # Wait for enough bars to be available to calculate a SMA.
        bar = bars[self.__instrument]
        
        #getfeed
        barDs = self.getFeed().getDataSeries("orcl")
        closeDs = self.getFeed().getDataSeries("orcl").getCloseDataSeries()
        volumeDs = self.getFeed().getDataSeries("orcl").getVolumeDataSeries()

        #engulfing signal: engulfing where 100 for bullish engulfing;  -100 for bearish engulfing;   0 for no engulfing
        engulfing = indicator.CDLENGULFING(barDs,50000)
        
        #recognize decreasing trend by previous 3 price and 3 volume
        trenddropprice = indicator.ROC(closeDs,50000,timeperiod=3)
        trenddropvol = indicator.ROC(volumeDs,50000,timeperiod=2)
    
       
        #Long exit (1): Edit the 90% price if price goes up
        if self.__position is not None and not self.__position.exitActive() and bar.getPrice()> (self.stoplossprice/0.9):
            self.stoplossprice=bar.getPrice()*0.9
        
        # If a position was not opened, check if we should enter a long position.
        if self.__position is None:
            
            # Long entry (2): [candle stick (try bullish engulfing first)] AND [rsi below 50] AND [price increase with volume high]
            # Enter a buy market order for 10 shares. The order is good till canceled.
            if engulfing[-1]==100 and trenddropprice[-2]<-2 and self.__rsi[-1]<50 and trenddropvol[-1]>0:
                self.__position = self.enterLong(self.__instrument, 10, True)
                self.stoplossprice=  bar.getPrice()*0.9      #Stop Long loss
                self.longprice=bar.getPrice()                #calculate profit only
            
        # Check if we have to exit the position.
        # Long exit (1) AND Stop Long loss
        elif not self.__position.exitActive() and bar.getPrice() < self.stoplossprice:
            self.__position.exitMarket()

        
def run_strategy(smaPeriod):
    
    instrument = "orcl"
    feed = yahoofinance.build_feed([instrument], 2000, 2000, ".") 
    
    # Load the yahoo feed from the CSV file
    feed = yahoofeed.Feed()
    feed.addBarsFromCSV("orcl", "orcl-2000-yahoofinance.csv")

    # Evaluate the strategy with the feed.
    myStrategy = MyStrategy(feed, "orcl", smaPeriod)
    myStrategy.run()
    print "Final portfolio value: $%.2f" % myStrategy.getBroker().getEquity()
    print "Profit %s Win: %s Loss: %s Win rate: %s%% " % (myStrategy.profit, myStrategy.win, myStrategy.loss, round(decimal.Decimal(myStrategy.win)/(decimal.Decimal(myStrategy.win)+decimal.Decimal(myStrategy.loss))*100,2))    
    

run_strategy(15)




