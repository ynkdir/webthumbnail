# Webpage thumbnailer
# encoding: utf-8

from __future__ import print_function, division, unicode_literals

import sys
import argparse
import signal
import logging

from PySide.QtCore import Signal, Qt, QObject, QTimer, QSize
from PySide.QtGui import QApplication, QImage, QPainter
from PySide.QtWebKit import QWebPage, QWebSettings


argument_parser = argparse.ArgumentParser(description="Webpage thumbnailer")
argument_parser.add_argument("url")
argument_parser.add_argument("--out", default="out.png",
        help="write image to specified file")
argument_parser.add_argument("--width", type=int,
        help="scale image to specified width")
argument_parser.add_argument("--height", type=int,
        help="scale image to specified height")
argument_parser.add_argument("--window-width", type=int, default=1024,
        help="window width")
argument_parser.add_argument("--window-height", type=int, default=768,
        help="window height")
argument_parser.add_argument("--timeout", type=float,
        help="render page on timeout (sec)")
argument_parser.add_argument("--noplugin", action="store_true",
        help="disable plugin")
argument_parser.add_argument("--debug", action='store_true',
        help="enable debug output")


class WebThumbnailer(QObject):
    finished = Signal(bool)

    def __init__(self, window_width, window_height):
        super(WebThumbnailer, self).__init__()
        self.ok = None
        self.page = QWebPage(self)
        self.page.mainFrame().setScrollBarPolicy(
                Qt.Horizontal, Qt.ScrollBarAlwaysOff)
        self.page.mainFrame().setScrollBarPolicy(
                Qt.Vertical, Qt.ScrollBarAlwaysOff)
        self.page.loadStarted.connect(self.on_page_started)
        self.page.loadFinished.connect(self.on_page_finished)
        self.page.networkAccessManager().finished.connect(
                self.on_network_finished)
        self.page.setViewportSize(QSize(window_width, window_height))

    def on_page_started(self):
        logging.debug('on_page_started')
        self.ok = None

    def on_page_finished(self, ok):
        logging.debug('on_page_finished: ok=%s', ok)
        self.ok = ok
        self.finished.emit(ok)

    def on_network_finished(self, reply):
        logging.debug('on_network_finished: %s', reply.url().toEncoded())

    def load(self, url):
        self.page.mainFrame().load(url)

    def save(self, out, width=None, height=None):
        image = self.render()
        scaled = self.scale(image, width, height)
        scaled.save(out)
        logging.debug('imagesize: %s', scaled.size())

    def render(self):
        image = QImage(self.page.viewportSize(), QImage.Format_RGB32)
        painter = QPainter(image)
        self.page.mainFrame().render(painter)
        painter.end()
        return image

    def scale(self, image, width=None, height=None):
        if width is None and height is None:
            scaled = image
        elif width is None:
            scaled = image.scaledToHeight(height, Qt.SmoothTransformation)
        elif height is None:
            scaled = image.scaledToWidth(width, Qt.SmoothTransformation)
        else:
            scaled = image.scaled(width, height,
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation)
            scaled = scaled.copy(0, 0, width, height)
        return scaled


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    args = argument_parser.parse_args()

    if args.debug:
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s: %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S")
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    app = QApplication(sys.argv)
    QWebSettings.globalSettings() \
            .setAttribute(QWebSettings.PluginsEnabled, not args.noplugin)

    webthumbnailer = WebThumbnailer(args.window_width, args.window_height)

    def on_finished(ok):
        webthumbnailer.save(args.out, args.width, args.height)
        QApplication.exit(0 if ok else 1)

    def on_timedout():
        webthumbnailer.save(args.out, args.width, args.height)
        QApplication.exit(0 if webthumbnailer.ok else 1)

    if args.timeout is None:
        webthumbnailer.finished.connect(on_finished)
    else:
        QTimer.singleShot(int(args.timeout * 1000), on_timedout)

    webthumbnailer.load(args.url)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
