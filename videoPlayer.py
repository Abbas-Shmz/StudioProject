
# import os
# from PyQt5 import QtCore, QtGui, QtWidgets, QtMultimedia, QtMultimediaWidgets
# from PyQt5.QtMultimedia import QMediaPlayer
#
# class Widget(QtWidgets.QWidget):
#     def __init__(self, parent=None):
#         super(Widget, self).__init__(parent)
#
#         self._scene = QtWidgets.QGraphicsScene(self)
#         self._gv = QtWidgets.QGraphicsView(self._scene)
#         self._gv.setBackgroundBrush(QtGui.QBrush(QtCore.Qt.lightGray))
#         # self._scene.set
#
#         self._videoitem = QtMultimediaWidgets.QGraphicsVideoItem()
#         self._scene.addItem(self._videoitem)
#
#         # self._ellipse_item = QtWidgets.QGraphicsEllipseItem(QtCore.QRectF(0, 0, 40, 60), self._videoitem)
#         # self._ellipse_item.setBrush(QtGui.QBrush(QtCore.Qt.green))
#         # self._ellipse_item.setPen(QtGui.QPen(QtCore.Qt.red))
#
#         self._line_item = QtWidgets.QGraphicsLineItem(100, 100, 300, 200 , self._videoitem)
#         # self._ellipse_item.setBrush(QtGui.QBrush(QtCore.Qt.green))
#         self._line_item.setPen(QtGui.QPen(QtCore.Qt.red))
#
#         self._player = QtMultimedia.QMediaPlayer(self, QtMultimedia.QMediaPlayer.VideoSurface)
#         self._player.stateChanged.connect(self.on_stateChanged)
#         self._player.setVideoOutput(self._videoitem)
#
#         file = os.path.join(os.path.dirname(__file__), "/Users/Abbas/IMG_0389.MP4")
#         self._player.setMedia(QtMultimedia.QMediaContent(QtCore.QUrl.fromLocalFile(file)))
#         button = QtWidgets.QPushButton("Play")
#         button.clicked.connect(self.play)
#
#         self.resize(640, 480)
#         lay = QtWidgets.QVBoxLayout(self)
#         lay.addWidget(self._gv)
#         lay.addWidget(button)
#
#     def play(self):
#         if self._player.state() == QMediaPlayer.PlayingState:
#             self._player.pause()
#         else:
#             self._player.play()
#
#     @QtCore.pyqtSlot(QtMultimedia.QMediaPlayer.State)
#     def on_stateChanged(self, state):
#         if state == QtMultimedia.QMediaPlayer.PlayingState:
#             self._gv.fitInView(self._videoitem, QtCore.Qt.KeepAspectRatio)
#
# if __name__ == '__main__':
#     import sys
#     app = QtWidgets.QApplication(sys.argv)
#     w = Widget()
#     w.show()
#     sys.exit(app.exec_())
# ===========================================================================================

from PyQt5.QtCore import QDir, Qt, QUrl, QLineF, QPoint, QSizeF
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtMultimediaWidgets import QVideoWidget, QGraphicsVideoItem
from PyQt5.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QLabel,
        QPushButton, QSizePolicy, QSlider, QStyle, QVBoxLayout, QWidget, QGraphicsView, QGraphicsScene,
        QGraphicsLineItem)
from PyQt5.QtWidgets import QMainWindow,QWidget, QPushButton, QAction, qApp, QStatusBar
from PyQt5.QtGui import QIcon, QBrush, QResizeEvent

from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
from hachoir.core import config as HachoirConfig

import sys
from datetime import datetime, timedelta

class GraphicView(QGraphicsView):
    def __init__(self, *args):
        super().__init__(*args)
        self.graphicItem = None
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # self.setMouseTracking(True)

    def mousePressEvent(self, event):
        if event.buttons() == Qt.MidButton:
            p1 = self.mapToScene(event.x(), event.y())
            self.graphicItem = self.scene().addLine(QLineF(p1, p1))
        else:
            self.parent().parent().play()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MidButton:
            p2 = self.mapToScene(event.x(), event.y())
            # self.parent().parent().statusBar.showMessage(f'x: {event.x()},  y: {event.y()}')
            # .prepareGeometryChange()
            self.graphicItem.setLine(QLineF(self.graphicItem.line().p1(), p2))

    def resizeEvent(self, event):
        self.fitInView(self.items()[-1], Qt.KeepAspectRatio)

    def mouseDoubleClickEvent(self, event):
        self.fitInView(self.items()[-1], Qt.KeepAspectRatio)
    #     print(self.items()[-1].boundingRect())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.parent().parent().play()


class VideoWindow(QMainWindow):

    def __init__(self, parent=None):
        super(VideoWindow, self).__init__(parent)
        self.setWindowTitle("Video Player")
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.gScene = QGraphicsScene(self)
        self.gView = GraphicView(self.gScene)
        self.gView.setSceneRect(0, 0, 320, 240)
        self.gView.setBackgroundBrush(QBrush(Qt.black))

        self.videoStartDatetime = None
        self.videoCurrentDatetime = None

        # ===================== Setting video item ==============================
        self.videoItem = QGraphicsVideoItem()
        self.videoItem.setAspectRatioMode(Qt.KeepAspectRatio)
        self.gScene.addItem(self.videoItem)
        self.mediaPlayer = QMediaPlayer(self, QMediaPlayer.VideoSurface)
        self.mediaPlayer.setVideoOutput(self.videoItem)
        # self.mediaPlayer.stateChanged.connect(self.on_stateChanged)
        # file = "/Users/Abbas/Stuart_GOPR0196.MP4"
        # self.mediaPlayer.setMedia(QMediaContent(QtCore.QUrl.fromLocalFile(file)))
        self.mediaPlayer.stateChanged.connect(self.mediaStateChanged)
        self.mediaPlayer.positionChanged.connect(self.positionChanged)
        self.mediaPlayer.durationChanged.connect(self.durationChanged)
        self.mediaPlayer.error.connect(self.handleError)

        self.playButton = QPushButton()
        self.playButton.setEnabled(False)
        self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.playButton.clicked.connect(self.play)

        self.positionSlider = QSlider(Qt.Horizontal)
        self.positionSlider.setRange(0, 0)
        self.positionSlider.sliderMoved.connect(self.setPosition)

        self.timerLabel = QLabel()
        self.timerLabel.setText('--:--:--')
        self.timerLabel.setFixedWidth(55)

        self.dateLabel = QLabel()
        self.dateLabel.setText('Video date: --')
        self.statusBar.addPermanentWidget(self.dateLabel)


        # Create new action
        openAction = QAction('&Open', self)  # QIcon('open.png'),
        openAction.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        openAction.setShortcut('Ctrl+O')
        openAction.setStatusTip('Open video file')
        openAction.triggered.connect(self.openFile)

        # Create exit action
        exitAction = QAction('&Exit', self)  # QIcon('exit.png'),
        exitAction.setIcon(self.style().standardIcon(QStyle.SP_TitleBarCloseButton))
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(qApp.quit)  # self.exitCall

        # Create menu bar and add action
        menuBar = self.menuBar()
        menuBar.setNativeMenuBar(False)
        fileMenu = menuBar.addMenu('&File')
        fileMenu.addAction(openAction)
        fileMenu.addAction(exitAction)


        # Create a widget for window contents
        wid = QWidget(self)
        self.setCentralWidget(wid)

        # Create layouts to place inside widget
        controlLayout = QHBoxLayout()
        controlLayout.setContentsMargins(0, 0, 0, 0)
        controlLayout.addWidget(self.playButton)
        controlLayout.addWidget(self.timerLabel)
        controlLayout.addWidget(self.positionSlider)
        # controlLayout.addWidget(self.durationLabel)

        layout = QVBoxLayout()
        layout.addWidget(self.gView)
        layout.addLayout(controlLayout)

        # Set widget to contain window contents
        wid.setLayout(layout)

    # def showEvent(self, event):
        # self.gView.fitInView(self.videoItem, Qt.KeepAspectRatio)

    def openFile(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Open Movie",
                                                  QDir.homePath())

        if fileName != '':
            creation_datetime = self.getVideoMetadata(fileName)
            self.videoStartDatetime = self.videoCurrentDatetime = creation_datetime
            self.dateLabel.setText(creation_datetime.strftime('%a, %b %d, %Y'))
            print(creation_datetime)

            self.mediaPlayer.setMedia(
                QMediaContent(QUrl.fromLocalFile(fileName)))
            self.playButton.setEnabled(True)
            self.setWindowTitle(fileName)
            # self.mediaPlayer.pause()



            # self.gView.scale(1.5, 1.5)
            # self.gView.fitInView(self.videoItem, Qt.KeepAspectRatio)
            # self.mediaPlayer.pause()
            # self.videoItem.setSize(QSizeF(self.gView.size()))
            # self.gView.resizeEvent(QResizeEvent())
            # print(self.gView.size())
            # print(self.videoItem.nativeSize())


    def exitCall(self):
        sys.exit(app.exec_())
        self.mediaPlayer.pause()
        self.close()

    def play(self):
        # print(self.videoItem.nativeSize())
        # self.gView.fitInView(self.videoItem, Qt.KeepAspectRatio)

        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.mediaPlayer.pause()

        else:
            self.mediaPlayer.play()

    def mediaStateChanged(self, state):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.playButton.setIcon(
                self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            self.playButton.setIcon(
                self.style().standardIcon(QStyle.SP_MediaPlay))

    def positionChanged(self, position):
        self.positionSlider.setValue(position)
        s, m, h = self.convertMillis(position)
        self.videoCurrentDatetime = self.videoStartDatetime + \
                                    timedelta(hours=h, minutes=m, seconds=s)
        self.timerLabel.setText('{:02d}:{:02d}:{:02d}'.format(
                                self.videoCurrentDatetime.time().hour,
                                self.videoCurrentDatetime.time().minute,
                                self.videoCurrentDatetime.time().second))
        # self.videoCurrentDatetime = current_datetime
        # print(current_datetime)
        # print(self.videoCurrentDatetime)


    def durationChanged(self, duration):
        self.positionSlider.setRange(0, duration)
        # s, m, h = self.convertMillis(duration)
        # self.durationLabel.setText('{:02d}:{:02d}'.format(m, s))

    def setPosition(self, position):
        self.mediaPlayer.setPosition(position)

    def handleError(self):
        self.playButton.setEnabled(False)
        # self.errorLabel.setText("Error: " + self.mediaPlayer.errorString())

    @staticmethod
    def convertMillis(millis):
        seconds = int(millis / 1000) % 60
        minutes = int(millis / (1000 * 60)) % 60
        hours = int(millis / (1000 * 60 * 60)) % 24
        return seconds, minutes, hours

    @staticmethod
    def getVideoMetadata(filename):
        HachoirConfig.quiet = True
        parser = createParser(filename)

        with parser:
            try:
                metadata = extractMetadata(parser)
            except Exception as err:
                print("Metadata extraction error: %s" % err)
                metadata = None
        if not metadata:
            print("Unable to extract metadata")

        creationDatetime_text = metadata.exportDictionary()['Metadata']['Creation date']
        creationDatetime = datetime.strptime(creationDatetime_text, '%Y-%m-%d %H:%M:%S%f')
        return creationDatetime
        # creationDate_text = creationDateTime.strftime('%a, %b %d, %Y')
        # self.videoStartDatetime = creationDateTime
        # creationTime = creationDateTime.time()
        # return creationDate_text, creationDate, creationTime



if __name__ == '__main__':
    app = QApplication(sys.argv)
    player = VideoWindow()
    player.resize(640, 480)
    player.show()
    sys.exit(app.exec_())