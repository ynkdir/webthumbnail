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
argument_parser.add_argument("--window-width", type=int,
        help="window width")
argument_parser.add_argument("--window-height", type=int,
        help="window height")
argument_parser.add_argument("--timeout", type=float,
        help="render page on timeout (sec)")
argument_parser.add_argument("--noplugin", action="store_true",
        help="disable plugin")
argument_parser.add_argument("--debug", action='store_true',
        help="enable debug output")


class Thumbnailer(QObject):
    DEFAULT_WINDOW_WIDTH = 1024
    DEFAULT_WINDOW_HEIGHT = 768

    finished = Signal(bool)

    def __init__(self, out, width, height, timeout=None,
            window_width=None, window_height=None):
        super(Thumbnailer, self).__init__()
        self.out = out
        self.width = width
        self.height = height
        if timeout is not None and timeout > 0:
            self.timeout = timeout
        else:
            self.timeout = None
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
        if window_width is None:
            window_width = self.DEFAULT_WINDOW_WIDTH
        if window_height is None:
            window_height = self.DEFAULT_WINDOW_HEIGHT
        self.page.setViewportSize(QSize(window_width, window_height))

    def load(self, url):
        self.page.mainFrame().load(url)
        if self.timeout is not None:
            QTimer.singleShot(int(self.timeout * 1000), self.on_timeout)

    def on_page_started(self):
        logging.debug('on_page_started')
        self.ok = None

    def on_page_finished(self, ok):
        logging.debug('on_page_finished: ok=%s', ok)
        self.ok = ok
        if self.timeout is None:
            self.finish(self.ok)

    def on_network_finished(self, reply):
        logging.debug('on_network_finished: %s', reply.url().toEncoded())

    def on_timeout(self):
        logging.debug('on_timeout')
        self.finish(self.ok if self.ok is not None else False)

    def finish(self, ok):
        logging.debug('finish: ok=%s', ok)
        # page loaded successfully or partly loaded with or without timeout
        image = self.render()
        scaled = self.scale(image, self.width, self.height)
        logging.debug('imagesize: %s', scaled.size())
        scaled.save(self.out)
        self.finished.emit(ok)

    def render(self):
        image = QImage(self.page.viewportSize(), QImage.Format_RGB32)
        painter = QPainter(image)
        self.page.mainFrame().render(painter)
        painter.end()
        return image

    def scale(self, image, width, height):
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


def on_finished(ok):
    if ok:
        QApplication.exit(0)
    else:
        QApplication.exit(1)


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
    thumbnailer = Thumbnailer(args.out, args.width, args.height,
            timeout=args.timeout,
            window_width=args.window_width,
            window_height=args.window_height)
    thumbnailer.finished.connect(on_finished)
    thumbnailer.load(args.url)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
