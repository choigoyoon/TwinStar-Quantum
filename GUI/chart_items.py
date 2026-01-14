# chart_items.py - PyQtGraph 차트 아이템들

import pyqtgraph as pg
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPicture


class CandlestickItem(pg.GraphicsObject):
    """캔들스틱 차트 아이템"""
    
    def __init__(self, data=None):
        pg.GraphicsObject.__init__(self)
        self.data = data  # [(timestamp, open, high, low, close), ...]
        self.picture = QPicture()
        self.generatePicture()
    
    def setData(self, data):
        self.data = data
        self.generatePicture()
        self.update()
    
    def generatePicture(self):
        self.picture = QPicture()
        p = QPainter(self.picture)
        
        if self.data is None or len(self.data) == 0:
            p.end()
            return
        
        w = 0.3  # 캔들 너비의 절반
        
        for i, (t, o, h, l, c) in enumerate(self.data):
            if c >= o:
                # 양봉 (상승)
                p.setPen(pg.mkPen('#26a69a'))
                p.setBrush(pg.mkBrush('#26a69a'))
            else:
                # 음봉 (하락)
                p.setPen(pg.mkPen('#ef5350'))
                p.setBrush(pg.mkBrush('#ef5350'))
            
            # 심지
            p.drawLine(QPointF(i, l), QPointF(i, h))
            
            # 몸통
            p.drawRect(QRectF(i - w, o, w * 2, c - o))
        
        p.end()
    
    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)
    
    def boundingRect(self):
        if self.data is None or len(self.data) == 0:
            return QRectF()
        
        min_price = min(d[3] for d in self.data)  # low
        max_price = max(d[2] for d in self.data)  # high
        
        return QRectF(-1, min_price, len(self.data) + 2, max_price - min_price)


class VolumeItem(pg.GraphicsObject):
    """거래량 막대 차트 아이템"""
    
    def __init__(self, data=None):
        pg.GraphicsObject.__init__(self)
        self.data = data  # [(timestamp, open, close, volume), ...]
        self.picture = QPicture()
        self.generatePicture()
    
    def setData(self, data):
        self.data = data
        self.generatePicture()
        self.update()
    
    def generatePicture(self):
        self.picture = QPicture()
        p = QPainter(self.picture)
        
        if self.data is None or len(self.data) == 0:
            p.end()
            return
        
        w = 0.35
        
        for i, (t, o, c, v) in enumerate(self.data):
            if c >= o:
                p.setPen(pg.mkPen('#26a69a'))
                p.setBrush(pg.mkBrush('#26a69a80'))
            else:
                p.setPen(pg.mkPen('#ef5350'))
                p.setBrush(pg.mkBrush('#ef535080'))
            
            p.drawRect(QRectF(i - w, 0, w * 2, v))
        
        p.end()
    
    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)
    
    def boundingRect(self):
        if self.data is None or len(self.data) == 0:
            return QRectF()
        max_vol = max(d[3] for d in self.data)
        return QRectF(-1, 0, len(self.data) + 2, max_vol)


class Crosshair:
    """크로스헤어 (십자선)"""
    
    def __init__(self, plot_widget):
        self.pw = plot_widget
        
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#787b86', width=1, style=Qt.PenStyle.DashLine))
        self.hLine = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#787b86', width=1, style=Qt.PenStyle.DashLine))
        
        plot_widget.addItem(self.vLine, ignoreBounds=True)
        plot_widget.addItem(self.hLine, ignoreBounds=True)
        
        # 라벨
        self.price_label = pg.TextItem(color='w', anchor=(0, 0.5))
        plot_widget.addItem(self.price_label)
        
        # 마우스 이동 연결
        plot_widget.scene().sigMouseMoved.connect(self.mouseMoved)
    
    def mouseMoved(self, pos):
        if self.pw.sceneBoundingRect().contains(pos):
            mousePoint = self.pw.plotItem.vb.mapSceneToView(pos)
            self.vLine.setPos(mousePoint.x())
            self.hLine.setPos(mousePoint.y())
            self.price_label.setPos(mousePoint.x() + 2, mousePoint.y())
            self.price_label.setText(f'{mousePoint.y():.2f}')


class TradeLabelItem(pg.GraphicsObject):
    """거래 진입/청산 마커"""
    
    def __init__(self, trade_data=None):
        """
        trade_data: [{'index': idx, 'price': price, 'type': 'entry'/'exit', 'side': 'long'/'short', 'pnl': pnl}]
        """
        pg.GraphicsObject.__init__(self)
        self.trade_data = trade_data or []
        self.picture = QPicture()
        self.generatePicture()
    
    def setData(self, data):
        self.trade_data = data
        self.generatePicture()
        self.update()
    
    def generatePicture(self):
        self.picture = QPicture()
        p = QPainter(self.picture)
        
        for trade in self.trade_data:
            idx = trade.get('index', 0)
            price = trade.get('price', 0)
            trade_type = trade.get('type', 'entry')
            side = trade.get('side', 'long')
            pnl = trade.get('pnl', 0)
            
            if trade_type == 'entry':
                if side == 'long':
                    # 롱 진입 - 초록색 삼각형 위쪽
                    p.setPen(pg.mkPen('#26a69a', width=2))
                    p.setBrush(pg.mkBrush('#26a69a'))
                    self._drawTriangle(p, idx, price, up=True)
                else:
                    # 숏 진입 - 빨간색 삼각형 아래쪽
                    p.setPen(pg.mkPen('#ef5350', width=2))
                    p.setBrush(pg.mkBrush('#ef5350'))
                    self._drawTriangle(p, idx, price, up=False)
            else:
                # 청산
                if pnl >= 0:
                    p.setPen(pg.mkPen('#26a69a', width=2))
                    p.setBrush(pg.mkBrush('#26a69a'))
                else:
                    p.setPen(pg.mkPen('#ef5350', width=2))
                    p.setBrush(pg.mkBrush('#ef5350'))
                
                # X 마크
                size = 10
                p.drawLine(QPointF(idx - size/2, price - size/2), QPointF(idx + size/2, price + size/2))
                p.drawLine(QPointF(idx - size/2, price + size/2), QPointF(idx + size/2, price - size/2))
        
        p.end()
    
    def _drawTriangle(self, p, x, y, up=True):
        size = 8
        if up:
            points = [QPointF(x, y - size), QPointF(x - size/2, y), QPointF(x + size/2, y)]
        else:
            points = [QPointF(x, y + size), QPointF(x - size/2, y), QPointF(x + size/2, y)]
        
        from PyQt6.QtGui import QPolygonF
        p.drawPolygon(QPolygonF(points))
    
    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)
    
    def boundingRect(self):
        return QRectF()


# 테스트용
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 테스트 데이터
    data = [(i, 100+i, 105+i, 95+i, 102+i) for i in range(50)]
    
    win = pg.GraphicsLayoutWidget()
    win.setWindowTitle('Chart Items Test')
    win.resize(800, 600)
    
    plot = win.addPlot()
    candles = CandlestickItem(data)
    plot.addItem(candles)
    
    crosshair = Crosshair(plot)
    
    win.show()
    sys.exit(app.exec())
