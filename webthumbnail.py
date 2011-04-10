# Webpage thumbnailer
# encoding: utf-8

from __future__ import print_function, division, unicode_literals

import sys
import argparse
import signal

from PySide.QtCore import Signal, Qt, QObject
from PySide.QtGui import QApplication, QImage, QPainter
from PySide.QtNetwork import QNetworkReply
from PySide.QtWebKit import QWebPage


argument_parser = argparse.ArgumentParser(description="Webpage thumbnailer")
argument_parser.add_argument("url")
argument_parser.add_argument("--width", type=int)
argument_parser.add_argument("--height", type=int)
argument_parser.add_argument("--out", default="out.png")


class Thumbnailer(QObject):
    finished = Signal(unicode)

    def __init__(self, url, out, width, height):
        super(Thumbnailer, self).__init__()
        self.url = url
        self.out = out
        self.width = width
        self.height = height
        self.reply = None
        self.page = QWebPage(self)
        self.page.mainFrame().setScrollBarPolicy(
                Qt.Horizontal, Qt.ScrollBarAlwaysOff)
        self.page.mainFrame().setScrollBarPolicy(
                Qt.Vertical, Qt.ScrollBarAlwaysOff)
        self.page.loadFinished.connect(self.on_page_finished)
        self.page.networkAccessManager().finished.connect(
                self.on_network_finished)
        self.page.mainFrame().load(url)

    def on_page_finished(self, ok):
        if ok:
            self.render()
        if self.reply is None:
            # FIXME: on_network_finished() is not called.
            # May be url is invalid (e.g. port >= 65535).
            # How to get error for it?
            error = "Invalid Request Error"
        elif self.reply.error() == QNetworkReply.NoError:
            error = None
        else:
            error = self.reply.error().name
        self.finished.emit(error)

    def on_network_finished(self, reply):
        self.reply = reply

    def render(self):
        self.page.setViewportSize(self.page.mainFrame().contentsSize())
        image = QImage(self.page.viewportSize(), QImage.Format_ARGB32)
        painter = QPainter(image)
        self.page.mainFrame().render(painter)
        painter.end()
        if self.width is None and self.height is None:
            outimg = image
        elif self.width is None:
            outimg = image.scaledToHeight(self.height, Qt.SmoothTransformation)
        elif self.height is None:
            outimg = image.scaledToWidth(self.width, Qt.SmoothTransformation)
        else:
            scaled = image.scaled(self.width, self.height,
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation)
            outimg = scaled.copy(0, 0, self.width, self.height)
        outimg.save(self.out)


def on_finished(error):
    if error is None:
        QApplication.exit(0)
    else:
        sys.stderr.write("{0}\n".format(error))
        QApplication.exit(1)


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    args = argument_parser.parse_args()
    app = QApplication(sys.argv)
    thumbnailer = Thumbnailer(args.url, args.out, args.width, args.height)
    thumbnailer.finished.connect(on_finished)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
