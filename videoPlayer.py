
# ===========================================================================================

from PyQt5.QtCore import (QDir, Qt, QUrl, QPointF, QLineF, QSize, QFile, QIODevice, QXmlStreamReader,
                          QXmlStreamWriter, QRectF, QSizeF)
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtMultimediaWidgets import QVideoWidget, QGraphicsVideoItem
from PyQt5.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QLabel,
        QPushButton, QSizePolicy, QSlider, QStyle, QVBoxLayout, QWidget, QGraphicsView, QGraphicsScene,
        QGraphicsLineItem, QGraphicsTextItem, QGraphicsEllipseItem, QGridLayout, QComboBox,
        QOpenGLWidget, QMessageBox, QActionGroup, QGraphicsRectItem)
from PyQt5.QtWidgets import (QMainWindow, QAction, qApp, QStatusBar, QDialog,
                             QLineEdit, QGraphicsItem, QGraphicsItemGroup)
from PyQt5.QtGui import QIcon, QBrush, QResizeEvent, QCursor, QPen, QFont, QColor, QPolygonF
from PyQt5.QtOpenGL import QGLWidget

import xml.etree.ElementTree as ET
import numpy as np
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
from hachoir.core import config as HachoirConfig

import sys
import os
from datetime import datetime, timedelta

from iframework import connectDatabase, Point, Line, Zone

from observationToolbox import ObsToolbox

class GraphicView(QGraphicsView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gLineItem = None #QGraphicsLineItem()
        self.gPolyItem = None
        self.labelShape = None
        self.currentPoly = None
        self.unsavedLines = []
        self.unsavedZones = []
        self.unsavedPoints = []
        self.labelSize = 10
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # self.setViewport(QOpenGLWidget())
        # self.setMouseTracking(True)

    def mousePressEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.parent().parent().drawLineAction.isChecked() \
                 and self.gLineItem == None:

            self.setMouseTracking(True)
            p1 = self.mapToScene(event.x(), event.y())
            self.gLineItem = self.scene().addLine(QLineF(p1, p1))
            r, g, b = np.random.choice(range(256), size=3)
            self.gLineItem.setPen(QPen(QColor(r, g, b), self.labelSize/6))
            # self.gLineItem.setOpacity(0.25)

        elif event.buttons() == Qt.LeftButton and self.parent().parent().drawZoneAction.isChecked():
            self.setMouseTracking(True)
            p_clicked = self.mapToScene(event.x(), event.y())
            if self.gPolyItem == None:
                self.currentPoly = QPolygonF([p_clicked])
                self.gPolyItem = self.scene().addPolygon(self.currentPoly)
                r, g, b = np.random.choice(range(256), size=3)
                self.gPolyItem.setPen(QPen(QColor(r, g, b), self.labelSize/10))
                self.gPolyItem.setBrush(QBrush(QColor(r, g, b, 40)))
            else:
                self.currentPoly.append(p_clicked)
                self.gPolyItem.setPolygon(self.currentPoly)

        elif event.buttons() == Qt.LeftButton and self.parent().parent().drawPointAction.isChecked():

            p = self.mapToScene(event.x(), event.y())
            pointBbx = QRectF()
            pointBbx.setSize(QSizeF(self.labelSize, self.labelSize))
            pointBbx.moveCenter(p)
            gPointItem = self.scene().addEllipse(pointBbx, QPen(Qt.white, 0.5), QBrush(Qt.black))
            self.unsavedPoints.append(gPointItem)
            self.scene().parent().drawPointAction.setChecked(False)
            self.unsetCursor()

        elif event.buttons() == Qt.RightButton:
            self.parent().parent().play()

    def mouseMoveEvent(self, event):
        if self.gLineItem != None and self.parent().parent().drawLineAction.isChecked():
            p2 = self.mapToScene(event.x(), event.y())
            self.gLineItem.setLine(QLineF(self.gLineItem.line().p1(), p2))

        elif self.gPolyItem != None and self.parent().parent().drawZoneAction.isChecked():
            p_floating = self.mapToScene(event.x(), event.y())
            self.gPolyItem.setPolygon(QPolygonF(list(self.currentPoly) + [p_floating]))

    def resizeEvent(self, event):
        self.fitInView(self.items()[-1], Qt.KeepAspectRatio)

    def showEvent(self, event):
        self.fitInView(self.items()[-1], Qt.KeepAspectRatio)

    def mouseDoubleClickEvent(self, event):
        if self.parent().parent().drawLineAction.isChecked() and self.gLineItem != None:
            self.setMouseTracking(False)
            self.parent().parent().drawLineAction.setChecked(False)
            self.unsavedLines.append(self.gLineItem)
            self.unsetCursor()
            self.gLineItem = None

        elif self.parent().parent().drawZoneAction.isChecked() and self.gPolyItem != None:
            self.setMouseTracking(False)
            self.parent().parent().drawZoneAction.setChecked(False)
            self.gPolyItem.setPolygon(self.currentPoly)
            self.unsavedZones.append(self.gPolyItem)
            self.unsetCursor()
            self.gPolyItem = None
        else:
            self.fitInView(self.items()[-1], Qt.KeepAspectRatio)

    def wheelEvent(self, event):
        factor = 1.1
        if event.angleDelta().y() < 0:
            factor = 0.9
        view_pos = event.pos()
        scene_pos = self.mapToScene(view_pos)
        self.centerOn(scene_pos)
        self.scale(factor, factor)
        delta = self.mapToScene(view_pos) - self.mapToScene(self.viewport().rect().center())
        self.centerOn(scene_pos - delta)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.parent().parent().play()


class VideoWindow(QMainWindow):

    def __init__(self, parent=None):
        super(VideoWindow, self).__init__(parent)
        self.setWindowTitle("StudioProject")
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.gScene = QGraphicsScene(self)
        self.gView = GraphicView(self.gScene, self)
        # self.gView.setBackgroundBrush(QBrush(Qt.black))

        self.videoStartDatetime = None
        self.videoCurrentDatetime = None

        self.projectFile = ''
        self.graphicsFile = ''
        self.videoFile = ''

        self.obsTb = ObsToolbox(self)

        # ===================== Setting video item ==============================
        self.videoItem = QGraphicsVideoItem()
        self.videoItem.setAspectRatioMode(Qt.KeepAspectRatio)
        self.gScene.addItem(self.videoItem)
        self.videoItem.mouseMoveEvent = self.gView.mouseMoveEvent

        self.mediaPlayer = QMediaPlayer(self, QMediaPlayer.VideoSurface)
        self.mediaPlayer.setVideoOutput(self.videoItem)
        self.mediaPlayer.stateChanged.connect(self.mediaStateChanged)
        self.mediaPlayer.positionChanged.connect(self.positionChanged)
        self.mediaPlayer.durationChanged.connect(self.durationChanged)
        self.mediaPlayer.error.connect(self.handleError)
        self.mediaPlayer.setMuted(True)
        self.mediaPlayer.setNotifyInterval(100)

        self.playButton = QPushButton()
        self.playButton.setEnabled(False)
        self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.playButton.clicked.connect(self.play)

        self.incrPlayRateBtn = QPushButton()
        # self.incrPlayRateBtn.setEnabled(False)
        self.incrPlayRateBtn.setIcon(self.style().standardIcon(QStyle.SP_MediaSeekForward))
        self.incrPlayRateBtn.clicked.connect(self.incrPlayRate)

        self.decrPlayRateBtn = QPushButton()
        # self.incrPlayRateBtn.setEnabled(False)
        self.decrPlayRateBtn.setIcon(self.style().standardIcon(QStyle.SP_MediaSeekBackward))
        self.decrPlayRateBtn.clicked.connect(self.decrPlayRate)

        self.positionSlider = QSlider(Qt.Horizontal)
        self.positionSlider.setRange(0, 0)
        self.positionSlider.sliderMoved.connect(self.setPosition)

        self.timerLabel = QLabel()
        self.timerLabel.setText('--:--:--')
        self.timerLabel.setFixedWidth(55)

        self.dateLabel = QLabel()
        self.dateLabel.setText('Video date: --')
        self.statusBar.addPermanentWidget(self.dateLabel)


        # Create open action
        self.openVideoAction = QAction(QIcon('icons/video-file.png'), 'Open video', self)
        self.openVideoAction.setShortcut('Ctrl+O')
        self.openVideoAction.setStatusTip('Open video file')
        self.openVideoAction.triggered.connect(self.openVideoFile)

        # Create observation action
        obsTbAction = QAction(QIcon('icons/checklist.png'), 'Observation toolbox', self)
        obsTbAction.setStatusTip('Open observation toolbox')
        obsTbAction.triggered.connect(self.openObsToolbox)

        self.drawPointAction = QAction(QIcon('icons/drawPoint.png'), 'Draw point', self)
        self.drawPointAction.setStatusTip('Draw point over the video')
        self.drawPointAction.setCheckable(True)
        self.drawPointAction.setEnabled(False)
        self.drawPointAction.triggered.connect(self.drawingClick)

        self.drawLineAction = QAction(QIcon('icons/drawLine.png'), 'Draw line', self)
        self.drawLineAction.setStatusTip('Draw line over the video')
        self.drawLineAction.setCheckable(True)
        self.drawLineAction.setEnabled(False)
        self.drawLineAction.triggered.connect(self.drawingClick)

        self.drawZoneAction = QAction(QIcon('icons/drawZone.png'), 'Draw zone', self)
        self.drawZoneAction.setStatusTip('Draw zone over the video')
        self.drawZoneAction.setCheckable(True)
        self.drawZoneAction.setEnabled(False)
        self.drawZoneAction.triggered.connect(self.drawingClick)

        actionGroup = QActionGroup(self)
        actionGroup.addAction(self.drawPointAction)
        actionGroup.addAction(self.drawLineAction)
        actionGroup.addAction(self.drawZoneAction)

        openProjectAction = QAction(QIcon('icons/open-project.png'), 'Open project', self)
        openProjectAction.setStatusTip('Open project')
        openProjectAction.triggered.connect(self.openProject)

        self.saveProjectAction = QAction(QIcon('icons/save-project.png'), 'Save project', self)
        self.saveProjectAction.setStatusTip('Save project')
        self.saveProjectAction.setEnabled(False)
        self.saveProjectAction.triggered.connect(self.saveProject)

        self.saveGraphAction = QAction(QIcon('icons/save-graphics.png'), 'Save graphics', self)
        self.saveGraphAction.setStatusTip('Save graphics to database')
        self.saveGraphAction.setEnabled(False)
        self.saveGraphAction.triggered.connect(self.saveGraphics)

        self.loadGraphAction = QAction(QIcon('icons/folders.png'), 'Load graphics', self)
        self.loadGraphAction.setStatusTip('Load graphics from database')
        self.loadGraphAction.setEnabled(False)
        self.loadGraphAction.triggered.connect(self.loadGraphics)


        # Create exit action
        exitAction = QAction(QIcon('icons/close.png'), 'Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(qApp.quit)  # self.exitCall

        # Create menu bar and add action
        # menuBar = self.menuBar()
        # menuBar.setNativeMenuBar(False)
        # fileMenu = menuBar.addMenu('&File')
        # fileMenu.addAction(openVideoAction)
        # fileMenu.addAction(obsTbAction)
        # fileMenu.addAction(exitAction)

        self.toolbar = self.addToolBar('Tools')
        self.toolbar.setIconSize(QSize(24, 24))
        self.toolbar.addAction(openProjectAction)
        self.toolbar.addAction(self.saveProjectAction)
        self.toolbar.addAction(self.openVideoAction)

        self.toolbar.insertSeparator(self.loadGraphAction)
        self.toolbar.addAction(self.loadGraphAction)
        self.toolbar.addAction(self.saveGraphAction)
        self.toolbar.addAction(self.drawPointAction)
        self.toolbar.addAction(self.drawLineAction)
        self.toolbar.addAction(self.drawZoneAction)
        self.toolbar.insertSeparator(self.drawPointAction)


        self.toolbar.insertSeparator(obsTbAction)
        self.toolbar.addAction(obsTbAction)

        self.toolbar.insertSeparator(exitAction)
        self.toolbar.addAction(exitAction)


        # Create a widget for window contents
        wid = QWidget(self)
        self.setCentralWidget(wid)

        # Create layouts to place inside widget
        controlLayout = QHBoxLayout()
        controlLayout.setContentsMargins(0, 0, 0, 0)
        controlLayout.addWidget(self.decrPlayRateBtn)
        controlLayout.addWidget(self.playButton)
        controlLayout.addWidget(self.incrPlayRateBtn)
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

    def openVideoFile(self):
        # self.mediaPlayer.setMedia(QMediaContent())
        if self.sender() == self.openVideoAction:
            self.videoFile, _ = QFileDialog.getOpenFileName(self, "Open video", QDir.homePath())
            if self.videoFile != '':
                self.setWindowTitle('{} - {}'.format(os.path.basename(self.videoFile),
                                                     os.path.basename(self.projectFile)))

        if self.videoFile != '':
            self.saveProjectAction.setEnabled(True)
            self.loadGraphAction.setEnabled(True)
            self.saveGraphAction.setEnabled(True)
            self.drawPointAction.setEnabled(True)
            self.drawLineAction.setEnabled(True)
            self.drawZoneAction.setEnabled(True)

            creation_datetime, width, height = self.getVideoMetadata(self.videoFile)
            self.videoStartDatetime = self.videoCurrentDatetime = creation_datetime
            self.dateLabel.setText(creation_datetime.strftime('%a, %b %d, %Y'))

            self.gView.setSceneRect(0, 0, width, height)
            self.videoItem.setSize(QSizeF(width, height))
            self.gView.labelSize = width/50

            self.mediaPlayer.setMedia(QMediaContent(QUrl.fromLocalFile(self.videoFile)))
            self.playButton.setEnabled(True)
            self.gView.setViewport(QOpenGLWidget())
            self.mediaPlayer.pause()

    def exitCall(self):
        sys.exit(app.exec_())
        self.mediaPlayer.pause()
        self.close()

    def play(self):
        # self.gView.fitInView(self.videoItem, Qt.KeepAspectRatio)

        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.mediaPlayer.pause()

        else:
            self.mediaPlayer.play()

    def incrPlayRate(self):
        self.mediaPlayer.setPlaybackRate(2)
        # if self.mediaPlayer.playbackRate() < 2:
        #     self.mediaPlayer.setPlaybackRate(self.mediaPlayer.playbackRate() + 0.2)
        #     self.statusBar.showMessage('Play back rate = x{}'.\
        #                                format(round(self.mediaPlayer.playbackRate(),1)), 2000)

    def decrPlayRate(self):
        self.mediaPlayer.setPlaybackRate(1)
        # if self.mediaPlayer.playbackRate() > 0.2:
        #     self.mediaPlayer.setPlaybackRate(self.mediaPlayer.playbackRate() - 0.2)
        #     self.statusBar.showMessage('Play back rate = x{}'.\
        #                                format(round(self.mediaPlayer.playbackRate(), 1)), 2000)

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


    def durationChanged(self, duration):
        self.positionSlider.setRange(0, duration)

        # s, m, h = self.convertMillis(duration)
        # self.durationLabel.setText('{:02d}:{:02d}'.format(m, s))

    def setPosition(self, position):
        self.mediaPlayer.setPosition(position)

    def handleError(self):
        self.playButton.setEnabled(False)
        # self.errorLabel.setText("Error: " + self.mediaPlayer.errorString())

    def openObsToolbox(self):
        if not self.obsTb.isVisible():
            self.obsTb.show()

    def drawingClick(self):
        # if self.sender() == self.drawLineAction:
        #     self.labelingAction.setChecked(False)
        # else:
        #     self.drawLineAction.setChecked(False)
        cursor = QCursor(Qt.CrossCursor)
        self.gView.setCursor(cursor)

    def openProject(self):
        self.projectFile, _ = QFileDialog.getOpenFileName(self, "Open project file",
                                                  QDir.homePath(), "Project (*.prj)")

        if self.projectFile == '':
            return

        self.saveProjectAction.setEnabled(True)
        self.loadGraphAction.setEnabled(True)
        self.saveGraphAction.setEnabled(True)
        self.drawPointAction.setEnabled(True)
        self.drawLineAction.setEnabled(True)
        self.drawZoneAction.setEnabled(True)

        tree = ET.parse(self.projectFile)
        root = tree.getroot()
        gItems = []
        for elem in root:
            subEelTexts = {}
            for subelem in elem:
                subEelTexts[subelem.tag] = subelem.text
            gItems.append([elem.tag, subEelTexts])


        for key in gItems:
            if key[0] == 'video':
                item = key[1]
                self.videoFile = item['fileName']
                self.openVideoFile()
                self.mediaPlayer.setPosition(int(item['sliderValue']))

            # elif key[0] == 'graphics':
            #     item = key[1]
            #     print(item['fileName'])
            #     if item['fileName'] != None:
            #         self.graphicsFile = item['fileName']
            #         self.loadGraphics()

            elif key[0] == 'database':
                item = key[1]
                print(item['fileName'])
                if item['fileName'] != None:
                    self.obsTb.dbFilename = item['fileName']
                    self.obsTb.opendbFile()

            elif key[0] == 'window':
                item = key[1]
                x, y = item['mainWin_pos'].split(',')
                w, h = item['mainWin_size'].split(',')
                self.setGeometry(int(x), int(y), int(w), int(h))
                if item['obsTbx_open'] == 'True':
                    self.obsTb.show()
                    x, y = item['obsTbx_pos'].split(',')
                    w, h = item['obsTbx_size'].split(',')
                    self.obsTb.setGeometry(int(x), int(y), int(w), int(h))

        self.loadGraphics()
        self.setWindowTitle('{} - {}'.format(os.path.basename(self.videoFile),
                                             os.path.basename(self.projectFile)))

    def saveProject(self):

        if self.projectFile == '':
            fileDir = QDir.homePath()
        else:
            fileDir = self.projectFile

        self.projectFile, _ = QFileDialog.getSaveFileName(self, "Save project file",fileDir,
                                                          "Project (*.prj)")
        # fileName = "/Users/Abbas/project.xml"
        if self.projectFile == '':
            return


        file = QFile(self.projectFile)
        if (not file.open(QIODevice.WriteOnly | QIODevice.Text)):
            return

        xmlWriter = QXmlStreamWriter(file)
        xmlWriter.setAutoFormatting(True)
        xmlWriter.writeStartDocument()

        xmlWriter.writeStartElement('project')

        xmlWriter.writeStartElement('video')
        xmlWriter.writeTextElement("fileName", self.videoFile) #mediaPlayer.media().canonicalUrl().path())
        xmlWriter.writeTextElement("sliderValue", str(self.mediaPlayer.position()))
        xmlWriter.writeEndElement()

        # xmlWriter.writeStartElement('graphics')
        # xmlWriter.writeTextElement("fileName", self.graphicsFile)
        # xmlWriter.writeEndElement()

        xmlWriter.writeStartElement('database')
        xmlWriter.writeTextElement("fileName", self.obsTb.dbFilename)
        xmlWriter.writeEndElement()

        xmlWriter.writeStartElement('window')
        xmlWriter.writeTextElement("mainWin_size", "{},{}".format(int(self.width()),
                                                                  int(self.height())))
        xmlWriter.writeTextElement("mainWin_pos", "{},{}".format(int(self.x()),
                                                                  int(self.y())))
        xmlWriter.writeTextElement("obsTbx_open", str(self.obsTb.isVisible()))
        xmlWriter.writeTextElement("obsTbx_size", "{},{}".format(int(self.obsTb.width()),
                                                                  int(self.obsTb.height())))
        xmlWriter.writeTextElement("obsTbx_pos", "{},{}".format(int(self.obsTb.x()),
                                                                  int(self.obsTb.y())))
        xmlWriter.writeEndElement()

        xmlWriter.writeEndElement()

        self.setWindowTitle('{} - {}'.format(os.path.basename(self.videoFile),
                                             os.path.basename(self.projectFile)))
        self.obsTb.setWindowTitle('{} - {}'.format(os.path.basename(self.obsTb.dbFilename),
                                             os.path.basename(self.projectFile)))

    def saveGraphics(self):
        dbfilename = self.obsTb.dbFilename
        if dbfilename != None:
            self.session = connectDatabase(dbfilename)
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText('The database file is not defined.')
            msg.setInformativeText('In order to set the database file, open the Observation Toolbox')
            msg.setIcon(QMessageBox.Critical)
            msg.exec_()
            return

        if self.gView.unsavedLines == [] and self.gView.unsavedZones == [] and \
                self.gView.unsavedPoints == []:
            QMessageBox.information(self, 'Save', 'No new graphical items to save!')
            return

        for item in self.gView.unsavedLines:
            x1 = round(item.line().x1(), 2)
            y1 = round(item.line().y1(), 2)
            x2 = round(item.line().x2(), 2)
            y2 = round(item.line().y2(), 2)
            line = Line(x1, y1, x2, y2)
            self.session.add(line)
            self.session.flush()
            label = self.generate_label([x1, x2], [y1, y2], line.idx)
            self.gView.scene().addItem(label)

        for item in self.gView.unsavedZones:
            xs = []
            ys = []
            for p in item.polygon():
                xs.append(round(p.x(), 2))
                ys.append(round(p.y(), 2))
            zone = Zone(xs, ys)
            self.session.add(zone)
            self.session.flush()

            label = self.generate_label(xs, ys, zone.idx)
            self.gView.scene().addItem(label)

        for item in self.gView.unsavedPoints:
            x = round(item.rect().center().x(), 2)
            y = round(item.rect().center().y(), 2)

            point = Point(x, y)
            self.session.add(point)
            self.session.flush()

            label = self.generate_label([x], [y], point.idx)
            self.gView.scene().removeItem(item)
            self.gView.scene().addItem(label)

        QMessageBox.information(self, 'Save',
                                '{} point(s), {} line(s) and {} zone(s) saved to database successfully!'
                                .format(len(self.gView.unsavedPoints), len(self.gView.unsavedLines),
                                        len(self.gView.unsavedZones)))
        self.gView.unsavedLines = []
        self.gView.unsavedZones = []
        self.gView.unsavedPoints = []

        self.session.commit()

    def generate_label(self, xs, ys, text):
        gItemGroup = QGraphicsItemGroup()
        pointBbx = QRectF()
        pointBbx.setSize(QSizeF(self.gView.labelSize, self.gView.labelSize))
        pointBbx.moveCenter(QPointF(np.mean(xs), np.mean(ys)))

        if len(xs) == 1:
            pointShape = QGraphicsEllipseItem(pointBbx)
            shapeColor = Qt.white
            textColor = Qt.black
        elif len(xs) ==2:
            pointShape = QGraphicsEllipseItem(pointBbx)
            shapeColor = Qt.black
            textColor = Qt.white
        else:
            pointShape = QGraphicsRectItem(pointBbx)
            shapeColor = Qt.darkBlue
            textColor = Qt.white
        pointShape.setPen(QPen(Qt.white, 0.5))
        pointShape.setBrush(QBrush(shapeColor))
        # self.gView.scene().addEllipse(pointBbx, QPen(Qt.white, 0.5), QBrush(Qt.black))
        gItemGroup.addToGroup(pointShape)
        textLabel = QGraphicsTextItem(str(text))
        labelFont = QFont()
        labelFont.setPointSize(self.gView.labelSize/2)
        labelFont.setBold(True)
        textLabel.setFont(labelFont)
        textLabel.setDefaultTextColor(textColor)
        textLabel.setPos(np.mean(xs) - (textLabel.boundingRect().width() / 2),
                         np.mean(ys) - (textLabel.boundingRect().height() / 2))
        gItemGroup.addToGroup(textLabel)
        return gItemGroup

    def loadGraphics(self):
        dbfilename = self.obsTb.dbFilename
        if dbfilename != None:
            self.session = connectDatabase(dbfilename)
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText('The database file is not defined.')
            msg.setInformativeText('In order to set the database file, open the Observation Toolbox')
            msg.setIcon(QMessageBox.Critical)
            msg.exec_()
            return

        q_line = self.session.query(Line)
        q_zone = self.session.query(Zone)
        if q_line.all() == [] or q_zone.all() == []:
            QMessageBox.information(self, 'Warning!', 'There is no graphics to load!')
            return

        for line in q_line:
            p1 = line.points[0]
            p2 = line.points[1]
            r, g, b = np.random.choice(range(256), size=3)
            self.gScene.addLine(p1.x, p1.y, p2.x, p2.y, QPen(QColor(r, g, b),
                                                             self.gView.labelSize/6))

            label = self.generate_label([p1.x, p2.x], [p1.y, p2.y], line.idx)
            self.gScene.addItem(label)

        for zone in q_zone:
            points = [QPointF(point.x, point.y) for point in zone.points]
            polygon = QPolygonF(points)
            r, g, b = np.random.choice(range(256), size=3)
            self.gScene.addPolygon(polygon, QPen(QColor(r, g, b), self.gView.labelSize/10),
                                   QBrush(QColor(r, g, b, 40)))

            label = self.generate_label([point.x for point in zone.points],
                                        [point.y for point in zone.points], zone.idx)
            self.gScene.addItem(label)



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
                metadata = extractMetadata(parser, 7)
            except Exception as err:
                print("Metadata extraction error: %s" % err)
                metadata = None
        if not metadata:
            print("Unable to extract metadata")

        # creationDatetime_text = metadata.exportDictionary()['Metadata']['Creation date']
        # creationDatetime = datetime.strptime(creationDatetime_text, '%Y-%m-%d %H:%M:%S')

        metadata_dict = metadata._Metadata__data
        # for key in metadata_dict.keys():
        #     if metadata_dict[key].values:
        #         print(key, metadata_dict[key].values[0].value)
        creationDatetime = metadata_dict['creation_date'].values[0].value
        width = metadata_dict['width'].values[0].value
        height = metadata_dict['height'].values[0].value


        return creationDatetime, width, height


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion') #'Fusion', 'Windows', 'WindowsVista', 'Macintosh'
    player = VideoWindow()
    player.resize(640, 480)
    player.show()
    sys.exit(app.exec_())