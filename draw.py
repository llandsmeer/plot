import sys
from PyQt5.QtWidgets import (QWidget, QSlider, QApplication, 
                             QHBoxLayout, QVBoxLayout, QFileDialog)
from PyQt5.QtCore import QObject, Qt, pyqtSignal, QSize, QRect
from PyQt5.QtGui import QPainter, QFont, QColor, QPen, QPainterPath, QBrush
from PyQt5.QtSvg import QSvgGenerator

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

    @classmethod
    def as_line(cls, line):
        return line if isinstance(line, cls) else cls(line)

    def __iter__(self):
        return iter(self.line)

class PlotDrawer:
    def __init__(self):
        self.reset_view()
        self.xmin = self.ymin = 0
        self.xmax = self.ymax = 1
        self.width = 100
        self.height = 100

    def drag(self, x, y):
        return PlotDrawerDrag(self, x, y)

    def reset_view(self):
        self.trans_x = 0
        self.trans_y = 0
        self.zoom = 0

    def set_bounds(self, xmin, ymin, xmax, ymax):
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax

    def set_size(self, width, height):
        self.width = width
        self.height = height

    def translate_point(self, point):
        px, py = point
        relx = (px-self.xmin)/(self.xmax-self.xmin)
        rely = (py-self.ymin)/(self.ymax-self.ymin)
        tx, ty = self.zoomed((relx-self.trans_x, rely-self.trans_y))
        return tx * self.width, (1-ty) * self.height

    def zoomed(self, point):
        x, y = point
        x = (x-0.5)*ZOOM_FACTOR**self.zoom + 0.5
        y = (y-0.5)*ZOOM_FACTOR**self.zoom + 0.5
        return x, y

    def unzoomed(self, point):
        x, y = point
        x = (x-0.5)/ZOOM_FACTOR**self.zoom + 0.5
        y = (y-0.5)/ZOOM_FACTOR**self.zoom + 0.5
        return x, y

    def scaled(self, point):
        x, y = point
        return x / self.width, 1 - y / self.height

    def zoom_to_point(self, direction, point):
        point = self.scaled(point)
        ox, oy = self.unzoomed(point)
        self.zoom += direction
        nx, ny = self.unzoomed(point)
        self.trans_x += ox - nx
        self.trans_y += oy - ny

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

    def draw_lines(self, painter, lines):
        pmin = self.xmin, self.ymin
        pmax = self.xmax, self.ymax
        xmin, ymin = self.translate_point(pmin)
        xmax, ymax = self.translate_point(pmax)
        painter.fillRect(xmin, ymax, xmax-xmin, ymin-ymax, Qt.white)
        for line in lines:
            self.draw_line(painter, line)

    def move_zoomed(self, dx, dy):
        self.trans_x += dx / ZOOM_FACTOR**self.zoom
        self.trans_y += dy / ZOOM_FACTOR**self.zoom

class PlotDrawerDrag:
    def __init__(self, drawer, x, y):
        self.drawer = drawer
        self.start = x, y
        self.trans = drawer.trans_x, drawer.trans_y

    def update(self, x, y):
        sx, sy = self.start
        tx, ty = self.trans
        rdx =   (sx-x) / self.drawer.width / ZOOM_FACTOR**self.drawer.zoom
        rdy = - (sy-y) / self.drawer.height / ZOOM_FACTOR**self.drawer.zoom
        self.drawer.trans_x = tx + rdx
        self.drawer.trans_y = ty + rdy

class PlotWindow(QWidget):
    def __init__(self, lines=(), **kwargs):
        super(**kwargs).__init__()
        self.drawer = PlotDrawer()
        self.update_size()
        self.load_lines(lines)
        self.reset_view()
        self.drag = None

    def reset_view(self):
        self.drawer.reset_view()

    def load_lines(self, lines):
        lines = [Line.as_line(l) for l in lines]
        self.lines = lines
        pmin = pmax = None, None
        for line in lines:
            for point in line:
                pmin = pointfn(min, pmin, point)
                pmax = pointfn(max, pmax, point)
        self.drawer.set_bounds(*pmin, *pmax)

    def update_size(self):
        size = self.size()
        self.drawer.set_size(size.width(), size.height())

    def modify_tr(self, x, y):
        self.drawer.move_zoomed(x*TRANS_DELTA, y*TRANS_DELTA)

    def modify_zoom(self, z):
        self.drawer.zoom += z

    def quicksave(self):
        path, type_ = QFileDialog.getSaveFileName(self, "Save SVG")
        if path:
            self.save_svg(path, self.drawer.width, self.drawer.height)

    def save_svg(self, path, width, height):
        generator = QSvgGenerator()
        generator.setFileName(path)
        generator.setSize(QSize(width, height))
        generator.setViewBox(QRect(0, 0, width, height))
        # generator.setTitle
        painter = QPainter()
        self.drawer.set_size(width, height)
        painter.begin(generator)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.HighQualityAntialiasing)
        self.drawer.draw_lines(painter, self.lines)
        painter.end()
        self.update_size()
        

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
        self.drawer.draw_lines(painter, self.lines)
        painter.end()

    def wheelEvent(self, e):
        self.update_size()
        y = e.angleDelta().y()
        point = e.x(), e.y()
        direction = (y > 0) - (y < 0)
        self.drawer.zoom_to_point(direction, point)
        self.update()

    def mousePressEvent(self, e):
        self.drag = self.drawer.drag(e.x(), e.y())
        self.setMouseTracking(True)

    def mouseReleaseEvent(self, e):
        if not self.drag is None:
            self.drag.update(e.x(), e.y())
            self.update()
        self.drag = None
        self.setMouseTracking(False)

    def mouseMoveEvent(self, e):
        if not self.drag is None:
            self.drag.update(e.x(), e.y())
            self.update()

    def resizeEvent(self, e):
        self.update_size()


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
        Qt.Key_W: 'quicksave',
    }

    actionmap = {
        'exit': QWidget.close,
        'move_up': lambda self: self.modify_tr(0, +1),
        'move_down': lambda self: self.modify_tr(0, -1),
        'move_left': lambda self: self.modify_tr(-1, 0),
        'move_right': lambda self: self.modify_tr(+1, 0),
        'zoom_in': lambda self: self.modify_zoom(+1),
        'zoom_out': lambda self: self.modify_zoom(-1),
        'reset': reset_view,
        'quicksave': quicksave
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
