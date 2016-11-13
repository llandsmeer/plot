import sys
from PyQt5.QtWidgets import (QWidget, QSlider, QApplication, 
    QHBoxLayout, QVBoxLayout)
from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QFont, QColor, QPen, QPainterPath, QBrush

ZOOM_FACTOR = 1.2
TRANS_DELTA = 0.2
DOTS, LINE = 0, 1

class Line:
    def __init__(self, line=()):
        line = list(line)
        self.line = line
        self.len = len(self.line)
        self.color = '#000000'
        self.style = LINE if len(line) > 3 else DOTS
        self.width = 4

    def __iter__(self):
        return iter(self.line)

class PlotWindow(QWidget):
    def __init__(self, lines=(), **kwargs):
        super(**kwargs).__init__()
        self.load_lines(lines)
        self.reset_view()
        self.drag_start = None

    def reset_view(self):
        self.trans_x = 0
        self.trans_y = 0
        self.zoom = 0

    def load_lines(self, lines):
        lines = [l if isinstance(l, Line) else Line(l) for l in lines]
        self.lines = lines
        pmin = pmax = None, None
        for line in lines:
            for point in line:
                pmin = pointfn(min, pmin, point)
                pmax = pointfn(max, pmax, point)
        self.xmin = pmin[0]
        self.ymin = pmin[1]
        self.xmax = pmax[0]
        self.ymax = pmax[1]

    def translate_point(self, point):
        size = self.size()
        width = size.width()
        height = size.height()
        px, py = point
        relx = (px-self.xmin)/(self.xmax-self.xmin)
        rely = (py-self.ymin)/(self.ymax-self.ymin)
        tx = ((relx-self.trans_x)-0.5)*ZOOM_FACTOR**self.zoom + 0.5
        ty = ((rely-self.trans_y)-0.5)*ZOOM_FACTOR**self.zoom + 0.5
        return tx * width, (1-ty) * height

    def wheelEvent(self, e):
        y = e.angleDelta().y()
        if y > 0:
            self.zoom += 1
        if y < 0:
            self.zoom -= 1
        self.update()

    def draw_plot_window(self, painter):
        for line in self.lines:
            self.draw_line(painter, line)
        self.draw_translation(painter)

    def modify_tr(self, x, y):
        self.trans_x += x * TRANS_DELTA
        self.trans_y += y * TRANS_DELTA

    def modify_zoom(self, z):
        self.zoom += z

    def draw_line(self, painter, line):
        path = self.path(line)
        try:
            color = QColor(line.color)
        except:
            color = Qt.black
        brush = QBrush(color)
        pen = QPen(brush, line.width)
        if line.style is DOTS:
            painter.setBrush(brush)
        painter.setPen(pen)
        painter.drawPath(path)

    def path(self, line):
        is_first = True
        path = QPainterPath()
        path.setFillRule(Qt.WindingFill)
        for point in line:
            x, y = self.translate_point(point)
            if is_first or line.style is DOTS:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
            if line.style is DOTS:
                path.addEllipse(-5, -5, 10, 10)
            is_first = False
        return path

    def keyPressEvent(self, e):
        key = e.key()
        action = self.keymap.get(key, None)
        function = self.actionmap.get(action, None)
        if function is None:
            return
        function(self)
        self.update()

    def paintEvent(self, e):
        painter = QPainter()
        painter.begin(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.HighQualityAntialiasing)
        xmin, ymin = self.translate_point((min(0, self.xmin), min(0, self.ymin)))
        xmax, ymax = self.translate_point((self.xmax, self.ymax))
        painter.fillRect(xmin, ymax, xmax-xmin, ymin-ymax, Qt.white)
        for line in self.lines:
            self.draw_line(painter, line)
        painter.end()

    def mousePressEvent(self, e):
        self.drag_start = e.x(), e.y(), self.trans_x, self.trans_y
        self.setMouseTracking(True)

    def mouseReleaseEvent(self, e):
        self.update_tr_drag(e.x(), e.y())
        self.drag_start = None
        self.setMouseTracking(False)

    def mouseMoveEvent(self, e):
        self.update_tr_drag(e.x(), e.y())

    def update_tr_drag(self, nx, ny):
        if self.drag_start is None:
            return
        ox, oy, tx, ty = self.drag_start
        size = self.size()
        rdx =   (ox-nx) / size.width() / ZOOM_FACTOR**self.zoom
        rdy = - (oy-ny) / size.height() / ZOOM_FACTOR**self.zoom
        self.trans_x = tx + rdx
        self.trans_y = ty + rdy
        self.update()


    keymap = {
        Qt.Key_Escape: 'exit',
        Qt.Key_Q: 'exit',
        Qt.Key_Up: 'move_up',
        Qt.Key_K: 'move_up',
        Qt.Key_Down: 'move_down',
        Qt.Key_J: 'move_down',
        Qt.Key_Left: 'move_left',
        Qt.Key_H: 'move_left',
        Qt.Key_Right: 'move_right',
        Qt.Key_L: 'move_right',
        Qt.Key_Plus: 'zoom_in',
        Qt.Key_Equal: 'zoom_in',
        Qt.Key_Minus: 'zoom_out',
        Qt.Key_R: 'reset',
    }

    actionmap = {
        'exit': QWidget.close,
        'move_up': lambda self: self.modify_tr(0, +1),
        'move_down': lambda self: self.modify_tr(0, -1),
        'move_left': lambda self: self.modify_tr(-1, 0),
        'move_right': lambda self: self.modify_tr(+1, 0),
        'zoom_in': lambda self: self.modify_zoom(+1),
        'zoom_out': lambda self: self.modify_zoom(-1),
        'reset': reset_view
    }

def pointfn(fn, target, src):
    tx, ty = target
    sx, sy = src
    rx = sx if tx is None else fn(tx, sx)
    ry = sy if ty is None else fn(ty, sy)
    return rx, ry

def main():
    line = []
    for input_line in sys.stdin:
        parsed_line = input_line.split('#', maxsplit=1)[0].strip()
        if not parsed_line:
            continue
        x, y = map(float, parsed_line.split())
        line.append((x, y))
    app = QApplication(sys.argv)
    window = PlotWindow([line])
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
