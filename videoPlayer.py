
# ===========================================================================================

from PyQt6.QtCore import (QDir, Qt, QUrl, QPointF, QLineF, QSize, QFile, QIODevice, QXmlStreamReader,
                          QXmlStreamWriter, QRectF, QSizeF)
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget, QGraphicsVideoItem
from PyQt6.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QLabel,
        QPushButton, QSizePolicy, QSlider, QStyle, QVBoxLayout, QWidget, QGraphicsView, QGraphicsScene,
        QGraphicsLineItem, QGraphicsTextItem, QGraphicsEllipseItem, QGridLayout, QComboBox,
        QMessageBox, QGraphicsRectItem, QGraphicsPolygonItem, QListWidgetItem)
from PyQt6.QtWidgets import (QMainWindow, QStatusBar, QDialog,
                             QLineEdit, QGraphicsItem, QGraphicsItemGroup)
from PyQt6.QtGui import (QIcon, QBrush, QResizeEvent, QCursor, QPen, QFont, QColor, QPolygonF,
                         QActionGroup, QAction)

import xml.etree.ElementTree as ET
import numpy as np

from PIL import Image, ImageDraw

import sys
import os
from datetime import datetime, timedelta

from iframework import connectDatabase, Point, Line, Zone
from indicators import getVideoMetadata

from observationToolbox import ObsToolbox
import observationToolbox

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
        # self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # self.setMouseTracking(True)

    def mousePressEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and (self.parent().parent().drawLineAction.isChecked() \
                 or self.parent().parent().obsTb.line_newRecButton.isChecked()) and self.gLineItem == None:

            self.setMouseTracking(True)
            p1 = self.mapToScene(int(event.position().x()), int(event.position().y()))
            self.gLineItem = self.scene().addLine(QLineF(p1, p1))
            r, g, b = np.random.choice(range(256), size=3)
            self.gLineItem.setPen(QPen(QColor(0, 0, 0), self.labelSize/7))
            # self.gLineItem.setOpacity(0.25)

        elif event.buttons() == Qt.MouseButton.LeftButton and (self.parent().parent().maskGenAction.isChecked() \
                or self.parent().parent().obsTb.zone_newRecButton.isChecked()):
            self.setMouseTracking(True)
            p_clicked = self.mapToScene(int(event.position().x()), int(event.position().y()))
            if self.gPolyItem == None:
                self.currentPoly = QPolygonF([p_clicked])
                self.gPolyItem = self.scene().addPolygon(self.currentPoly)
                r, g, b = np.random.choice(range(256), size=3)
                self.gPolyItem.setPen(QPen(QColor(r, g, b), self.labelSize/10))
                self.gPolyItem.setBrush(QBrush(QColor(r, g, b, 40)))
            else:
                self.currentPoly.append(p_clicked)
                self.gPolyItem.setPolygon(self.currentPoly)

        elif event.buttons() == Qt.MouseButton.LeftButton and self.parent().parent().drawPointAction.isChecked():

            p = self.mapToScene(event.x(), event.y())
            pointBbx = QRectF()
            pointBbx.setSize(QSizeF(self.labelSize, self.labelSize))
            pointBbx.moveCenter(p)
            gPointItem = self.scene().addEllipse(pointBbx, QPen(Qt.GlobalColor.white, 0.5), QBrush(Qt.GlobalColor.black))
            self.unsavedPoints.append(gPointItem)
            self.scene().parent().drawPointAction.setChecked(False)
            self.unsetCursor()

        elif event.buttons() == Qt.MouseButton.LeftButton: #RightButton:
            self.parent().parent().play()

    def mouseMoveEvent(self, event):
        if self.gLineItem != None and (self.parent().parent().drawLineAction.isChecked() \
                or self.parent().parent().obsTb.line_newRecButton.isChecked()):
            p2 = self.mapToScene(int(event.position().x()), int(event.position().y()))
            self.gLineItem.setLine(QLineF(self.gLineItem.line().p1(), p2))

        elif self.gPolyItem != None and (self.parent().parent().maskGenAction.isChecked() \
                or self.parent().parent().obsTb.zone_newRecButton.isChecked()):
            p_floating = self.mapToScene(int(event.position().x()), int(event.position().y()))
            self.gPolyItem.setPolygon(QPolygonF(list(self.currentPoly) + [p_floating]))

    def resizeEvent(self, event):
        if len(self.items()) > 0:
            self.fitInView(self.items()[-1], Qt.AspectRatioMode.KeepAspectRatio)

    def showEvent(self, event):
        if len(self.items()) > 0:
            self.fitInView(self.items()[-1], Qt.KeepAspectRatio)

    def mouseDoubleClickEvent(self, event):
        if self.gLineItem != None and (self.parent().parent().drawLineAction.isChecked() \
                or self.parent().parent().obsTb.line_newRecButton.isChecked()):
            self.setMouseTracking(False)
            self.parent().parent().drawLineAction.setChecked(False)
            self.parent().parent().obsTb.line_newRecButton.setChecked(False)
            self.unsavedLines.append(self.gLineItem)
            self.unsetCursor()

            x1 = round(self.gLineItem.line().x1(), 2)
            y1 = round(self.gLineItem.line().y1(), 2)
            x2 = round(self.gLineItem.line().x2(), 2)
            y2 = round(self.gLineItem.line().y2(), 2)
            line = Line(None, None, x1, y1, x2, y2)
            observationToolbox.session.add(line)
            observationToolbox.session.flush()

            itmGroup = self.parent().parent().generate_itemGroup([x1, x2], [y1, y2], str(line.idx), None)
            self.scene().addItem(itmGroup)
            self.scene().removeItem(self.gLineItem)

            new_item = QListWidgetItem(str(line.idx))
            self.parent().parent().obsTb.line_list_wdgt.addItem(new_item)
            self.parent().parent().obsTb.line_list_wdgt.setCurrentItem(new_item)
            self.parent().parent().obsTb.init_input_widgets(self.parent().parent().obsTb.line_grpBox)

            self.gLineItem = None

        elif self.gPolyItem != None and (self.parent().parent().maskGenAction.isChecked() \
                or self.parent().parent().obsTb.zone_newRecButton.isChecked()):
            self.setMouseTracking(False)
            self.parent().parent().obsTb.zone_newRecButton.setChecked(False)
            self.gPolyItem.setPolygon(self.currentPoly)
            self.unsavedZones.append(self.gPolyItem)
            self.unsetCursor()

            if self.parent().parent().maskGenAction.isChecked():
                self.parent().parent().maskGenAction.setChecked(False)
                # self.scene().addItem(self.gPolyItem)
                self.parent().parent().saveMaskFile()
                self.gPolyItem = None
                return

            xs = []
            ys = []
            for p in self.gPolyItem.polygon():
                xs.append(round(p.x(), 2))
                ys.append(round(p.y(), 2))
            zone = Zone(None, None, xs, ys)
            observationToolbox.session.add(zone)
            observationToolbox.session.flush()

            itmGroup = self.parent().parent().generate_itemGroup(xs, ys, str(zone.idx), None)
            self.scene().addItem(itmGroup)
            self.scene().removeItem(self.gPolyItem)

            new_item = QListWidgetItem(str(zone.idx))
            self.parent().parent().obsTb.zone_list_wdgt.addItem(new_item)
            self.parent().parent().obsTb.zone_list_wdgt.setCurrentItem(new_item)
            self.parent().parent().obsTb.init_input_widgets(self.parent().parent().obsTb.zone_grpBox)

            self.gPolyItem = None
        # elif len(self.items()) > 0:
        #     self.fitInView(self.items()[-1], Qt.AspectRatioMode.KeepAspectRatio)

    # def wheelEvent(self, event):
    #     factor = 1.1
    #     if event.angleDelta().y() < 0:
    #         factor = 0.9
    #     # scene_pos = event.scenePosition()
    #     scene_pos = self.mapToScene(int(event.position().x()), int(event.position().y()))
    #     self.centerOn(scene_pos)
    #     self.scale(factor, factor)
    #     # delta = self.mapToScene(view_pos) - self.mapToScene(self.viewport().rect().center())
    #     delta = scene_pos - self.mapToScene(self.viewport().rect().center())
    #     self.centerOn(scene_pos - delta)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self.parent().parent().play()


class VideoWindow(QMainWindow):

    def __init__(self, parent=None):
        super(VideoWindow, self).__init__(parent)
        self.setWindowTitle("StudioProject")
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.gScene = QGraphicsScene(self)
        self.gView = GraphicView(self.gScene, self)
        self.gView.viewport().setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, False)
        # self.gView.setBackgroundBrush(QBrush(Qt.black))

        self.videoStartDatetime = None
        self.videoCurrentDatetime = None

        self.projectFile = ''
        self.graphicsFile = ''
        self.videoFile = ''

        self.obsTb = ObsToolbox(self)

        # # ===================== Setting video item ==============================
        # self.videoItem = QGraphicsVideoItem()
        # self.videoItem.setAspectRatioMode(Qt.KeepAspectRatio)
        # self.gScene.addItem(self.videoItem)
        # self.videoItem.mouseMoveEvent = self.gView.mouseMoveEvent

        self.mediaPlayer = QMediaPlayer(self)
        # self.mediaPlayer.setVideoOutput(self.videoItem)
        self.mediaPlayer.playbackStateChanged.connect(self.mediaStateChanged)
        self.mediaPlayer.positionChanged.connect(self.positionChanged)
        self.mediaPlayer.durationChanged.connect(self.durationChanged)
        self.mediaPlayer.errorOccurred.connect(self.handleError)
        # self.mediaPlayer.setMuted(True)
        # self.mediaPlayer.setNotifyInterval(100)

        self.playButton = QPushButton()
        self.playButton.setEnabled(False)
        self.playButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.playButton.clicked.connect(self.play)

        self.changePlayRateBtn = QPushButton('1x')
        self.changePlayRateBtn.setFixedWidth(40)
        # self.incrPlayRateBtn.setEnabled(False)
        self.changePlayRateBtn.clicked.connect(self.changePlayRate)

        self.positionSlider = QSlider(Qt.Orientation.Horizontal)
        self.positionSlider.setRange(0, 0)
        self.positionSlider.sliderMoved.connect(self.setPosition)

        self.timerLabel = QLabel()
        self.timerLabel.setText('--:--:--')
        self.timerLabel.setFixedWidth(58)

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

        self.maskGenAction = QAction(QIcon('icons/mask.png'), 'Generate mask file', self)
        self.maskGenAction.setStatusTip('Generate mask file for TrafficIntelligence')
        self.maskGenAction.setCheckable(True)
        self.maskGenAction.setEnabled(False)
        self.maskGenAction.triggered.connect(self.generateMask)

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
        exitAction.triggered.connect(self.exitCall)  # self.exitCall

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

        # self.toolbar.insertSeparator(self.loadGraphAction)
        # self.toolbar.addAction(self.loadGraphAction)
        # self.toolbar.addAction(self.saveGraphAction)
        # self.toolbar.addAction(self.drawPointAction)
        # self.toolbar.addAction(self.drawLineAction)
        # self.toolbar.addAction(self.drawZoneAction)
        self.toolbar.addAction(self.maskGenAction)
        # self.toolbar.insertSeparator(self.drawPointAction)


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
        # controlLayout.addWidget(self.decrPlayRateBtn)
        controlLayout.addWidget(self.playButton)
        controlLayout.addWidget(self.changePlayRateBtn)
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
            # if self.videoFile != '':
            #     self.setWindowTitle('{} - {}'.format(os.path.basename(self.videoFile),
            #                                          os.path.basename(self.projectFile)))

        if self.videoFile != '':
            self.setWindowTitle('{} - {}'.format(os.path.basename(self.videoFile),
                                                 os.path.basename(self.projectFile)))
            self.saveProjectAction.setEnabled(True)
            self.maskGenAction.setEnabled(True)
            # self.loadGraphAction.setEnabled(True)
            # self.saveGraphAction.setEnabled(True)
            # self.drawPointAction.setEnabled(True)
            # self.drawLineAction.setEnabled(True)
            # self.drawZoneAction.setEnabled(True)

            creation_datetime, width, height = getVideoMetadata(self.videoFile)
            self.videoStartDatetime = self.videoCurrentDatetime = self.obsTb.video_start = creation_datetime
            self.dateLabel.setText(creation_datetime.strftime('%a, %b %d, %Y'))

            self.timerLabel.setText('{:02d}:{:02d}:{:02d}'.format(
                creation_datetime.time().hour,
                creation_datetime.time().minute,
                creation_datetime.time().second))

            self.gView.setSceneRect(0, 0, width, height)

            self.videoItem = QGraphicsVideoItem()
            self.videoItem.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
            self.gScene.addItem(self.videoItem)
            self.videoItem.mouseMoveEvent = self.gView.mouseMoveEvent
            self.videoItem.setSize(QSizeF(width, height))

            self.mediaPlayer.setVideoOutput(self.videoItem)
            self.mediaPlayer.setSource(QUrl.fromLocalFile(self.videoFile))

            self.gView.labelSize = width/50

            self.playButton.setEnabled(True)
            # self.gView.setViewport(QOpenGLWidget())
            self.mediaPlayer.pause()

    def exitCall(self):
        # sys.exit(app.exec())
        # self.mediaPlayer.pause()
        self.close()

    def play(self):
        # self.gView.fitInView(self.videoItem, Qt.KeepAspectRatio)

        if self.mediaPlayer.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.mediaPlayer.pause()

        else:
            self.mediaPlayer.play()

    def changePlayRate(self):
        if self.mediaPlayer.playbackRate() < 2:
            r = self.mediaPlayer.playbackRate() + 0.5
            self.mediaPlayer.setPlaybackRate(r)
            self.changePlayRateBtn.setText('{:g}x'.format(r))
            self.statusBar.showMessage('Play back rate = {:g}x'.format(r), 2000)
        elif self.mediaPlayer.playbackRate() == 2:
            self.mediaPlayer.setPlaybackRate(1)
            self.changePlayRateBtn.setText('{}x'.format(1))
            self.statusBar.showMessage('Play back rate = {}x'.format(1), 2000)

    def mediaStateChanged(self, state):
        if self.mediaPlayer.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.playButton.setIcon(
                self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        else:
            self.playButton.setIcon(
                self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))

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
        cursor = QCursor(Qt.CursorShape.CrossCursor)
        self.gView.setCursor(cursor)

    def generateMask(self):
        if not self.sender().isChecked():
            self.gView.unsetCursor()
            return
        cursor = QCursor(Qt.CursorShape.CrossCursor)
        self.gView.setCursor(cursor)

        # dbfilename = self.obsTb.dbFilename
        # if dbfilename != None:
        #     self.session = connectDatabase(dbfilename)
        # else:
        #     msg = QMessageBox()
        #     msg.setIcon(QMessageBox.Information)
        #     msg.setText('The database file is not defined.')
        #     msg.setInformativeText('In order to set the database file, open the Observation Toolbox')
        #     msg.setIcon(QMessageBox.Critical)
        #     msg.exec_()
        #     return

        # if self.gView.unsavedLines == [] and self.gView.unsavedZones == [] and \
        #         self.gView.unsavedPoints == []:
        #     QMessageBox.information(self, 'Save', 'There is no polygon to generate mask!')
        #     return

    def saveMaskFile(self):
        creation_datetime, width, height = getVideoMetadata(self.videoFile)
        item = self.gView.gPolyItem #self.gView.unsavedZones[0]
        mask_polygon = item.polygon()
        xy = []
        for p in mask_polygon:
            xy.append((p.x(), p.y()))

        img = Image.new('RGB', (width, height), color='black')
        img1 = ImageDraw.Draw(img)
        img1.polygon(xy, fill="white", outline="white")

        fileName, _ = QFileDialog.getSaveFileName(self, "Open database file",
                                                  QDir.homePath(), "PNG files (*.png)")
        if fileName != '':
            img.save(fileName)

        self.gView.scene().removeItem(item)
        self.gView.unsavedZones = []


    def openProject(self):
        self.projectFile, _ = QFileDialog.getOpenFileName(self, "Open project file",
                                                  QDir.homePath(), "Project (*.prj)")

        if self.projectFile == '':
            return

        self.saveProjectAction.setEnabled(True)
        self.maskGenAction.setEnabled(True)
        # self.loadGraphAction.setEnabled(True)
        # self.saveGraphAction.setEnabled(True)
        # self.drawPointAction.setEnabled(True)
        # self.drawLineAction.setEnabled(True)
        # self.drawZoneAction.setEnabled(True)

        tree = ET.parse(self.projectFile)
        root = tree.getroot()
        gItems = []
        for elem in root:
            subEelTexts = {}
            for subelem in elem:
                subEelTexts[subelem.tag] = subelem.text
            gItems.append([elem.tag, subEelTexts])


        for key in gItems:
            if key[0] == 'database':
                item = key[1]
                if item['fileName'] is not None:
                    self.obsTb.dbFilename = item['fileName']
                    self.obsTb.opendbFile()

            elif key[0] == 'video':
                item = key[1]
                if item['fileName'] is not None:
                    self.videoFile = item['fileName']
                    self.openVideoFile()
                    self.mediaPlayer.setPosition(int(item['sliderValue']))
                    if item['fileName'] is not None:
                        self.loadGraphics()

            elif key[0] == 'trajectory':
                item = key[1]
                if item['metadata'] != None:
                    self.obsTb.mdbFileLedit.setText(item['metadata'])
                    self.obsTb.openMdbFile()
                    self.obsTb.siteNameCombobx.setCurrentIndex(int(item['site']))
                    self.obsTb.camViewCombobx.setCurrentIndex(int(item['cam_view']))
                    self.obsTb.trjDbCombobx.setCurrentIndex(int(item['traj_db']))
                    self.obsTb.plotItems()

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


        # self.setWindowTitle('{} - {}'.format(os.path.basename(self.videoFile),
        #                                      os.path.basename(self.projectFile)))

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
        if (not file.open(QIODevice.OpenModeFlag.WriteOnly | QIODevice.OpenModeFlag.Text)):
            return

        xmlWriter = QXmlStreamWriter(file)
        xmlWriter.setAutoFormatting(True)
        xmlWriter.writeStartDocument()

        xmlWriter.writeStartElement('project')

        xmlWriter.writeStartElement('database')
        xmlWriter.writeTextElement("fileName", self.obsTb.dbFilename)
        xmlWriter.writeEndElement()

        xmlWriter.writeStartElement('video')
        xmlWriter.writeTextElement("fileName", self.videoFile) #mediaPlayer.media().canonicalUrl().path())
        xmlWriter.writeTextElement("sliderValue", str(self.mediaPlayer.position()))
        xmlWriter.writeEndElement()

        xmlWriter.writeStartElement('trajectory')
        xmlWriter.writeTextElement("metadata", self.obsTb.mdbFileLedit.text())
        xmlWriter.writeTextElement("site", str(self.obsTb.siteNameCombobx.currentIndex()))
        xmlWriter.writeTextElement("cam_view", str(self.obsTb.camViewCombobx.currentIndex()))
        xmlWriter.writeTextElement("traj_db", str(self.obsTb.trjDbCombobx.currentIndex()))
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
        if self.obsTb.dbFilename != None:
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
            line = Line(None, None, x1, y1, x2, y2)
            self.session.add(line)
            self.session.flush()
            label = self.generate_itemGroup([x1, x2], [y1, y2], line.idx)
            self.gView.scene().addItem(label)

        for item in self.gView.unsavedZones:
            xs = []
            ys = []
            for p in item.polygon():
                xs.append(round(p.x(), 2))
                ys.append(round(p.y(), 2))
            zone = Zone(None, None, xs, ys)
            self.session.add(zone)
            self.session.flush()

            label = self.generate_itemGroup(xs, ys, zone.idx)
            self.gView.scene().addItem(label)

        for item in self.gView.unsavedPoints:
            x = round(item.rect().center().x(), 2)
            y = round(item.rect().center().y(), 2)

            point = Point(x, y)
            self.session.add(point)
            self.session.flush()

            label = self.generate_itemGroup([x], [y], point.idx)
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

    def generate_itemGroup(self, xs, ys, label, type):
        gItemGroup = QGraphicsItemGroup()

        pointBbx = QRectF()
        pointBbx.setSize(QSizeF(self.gView.labelSize, self.gView.labelSize))

        textLabel = QGraphicsTextItem(label)

        if len(xs) == 1:
            pointBbx.moveCenter(QPointF(xs[0], ys[0]))
            textLabel.setPos(xs[0] - (textLabel.boundingRect().width() / 2),
                             ys[0] - (textLabel.boundingRect().height() / 2))

            pointShape = QGraphicsEllipseItem(pointBbx)
            shapeColor = Qt.GlobalColor.white
            textColor = Qt.GlobalColor.black
            tooltip = 'P{}:{}'
        elif len(xs) == 2:
            pointBbx.moveCenter(QPointF(xs[1], ys[1]))
            textLabel.setPos(xs[1] - (textLabel.boundingRect().width() / 2),
                             ys[1] - (textLabel.boundingRect().height() / 2))

            r, g, b = np.random.choice(range(256), size=3)
            line_item = QGraphicsLineItem(xs[0], ys[0], xs[1], ys[1])
            line_item.setPen(QPen(QColor(r, g, b, 128), self.gView.labelSize / 6))
            gItemGroup.addToGroup(line_item)

            # line_end = QGraphicsEllipseItem(xs[1], ys[1],
            #                                 int(self.gView.labelSize/3), int(self.gView.labelSize/3))
            # line_end.setPen(QPen(QColor(r, g, b), 0.5))
            # line_end.setBrush(QBrush(QColor(r, g, b)))
            # gItemGroup.addToGroup(line_end)

            pointShape = QGraphicsEllipseItem(pointBbx)
            shapeColor = QColor(r, g, b, 128)
            textColor = Qt.GlobalColor.black
            tooltip = 'L{}:{}'
            # textLabel.setRotation(np.arctan((ys[1] - ys[0])/(xs[1] - xs[0]))*(180/3.14))
        else:
            pointBbx.moveCenter(QPointF(np.mean(xs), np.mean(ys)))
            textLabel.setPos(np.mean(xs) - (textLabel.boundingRect().width() / 2),
                             np.mean(ys) - (textLabel.boundingRect().height() / 2))

            points = [QPointF(x, y) for x, y in zip(xs, ys)]
            polygon = QPolygonF(points)
            r, g, b = np.random.choice(range(256), size=3)
            zone_item = QGraphicsPolygonItem(polygon)
            zone_item.setPen(QPen(QColor(r, g, b), self.gView.labelSize / 10))
            zone_item.setBrush(QBrush(QColor(r, g, b, 40)))
            gItemGroup.addToGroup(zone_item)

            pointShape = QGraphicsRectItem(pointBbx)
            shapeColor = Qt.GlobalColor.darkBlue
            textColor = Qt.GlobalColor.white
            tooltip = 'Z{}:{}'

        pointShape.setPen(QPen(Qt.GlobalColor.white, 0.5))
        pointShape.setBrush(QBrush(shapeColor))
        # self.gView.scene().addEllipse(pointBbx, QPen(Qt.white, 0.5), QBrush(Qt.black))
        gItemGroup.setToolTip(tooltip.format(label, type))
        gItemGroup.addToGroup(pointShape)

        labelFont = QFont()
        labelFont.setPointSize(round(self.gView.labelSize/2))
        labelFont.setBold(True)

        textLabel.setFont(labelFont)
        textLabel.setDefaultTextColor(textColor)

        gItemGroup.addToGroup(textLabel)
        return gItemGroup

    def loadGraphics(self):
        dbfilename = self.obsTb.dbFilename
        if dbfilename != None:
            self.session = connectDatabase(dbfilename)
        else:
            msg = QMessageBox()
            # msg.setIcon(QMessageBox.Icon.Information)
            msg.setText('The database file is not defined.')
            msg.setInformativeText('In order to set the database file, open the Observation Toolbox')
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.exec()
            return

        for gitem in self.gView.scene().items():
            if isinstance(gitem, QGraphicsItemGroup):
                self.gView.scene().removeItem(gitem)

        q_line = self.session.query(Line)
        q_zone = self.session.query(Zone)
        if q_line.all() == [] and q_zone.all() == []:
            QMessageBox.information(self, 'Warning!', 'There is no graphics to load!')
            return

        line_items = []
        for line in q_line:
            p1 = line.points[0]
            p2 = line.points[1]

            if line.type != None:
                lineType = line.type.name
            else:
                lineType = None
            gItmGroup = self.generate_itemGroup([p1.x, p2.x], [p1.y, p2.y], str(line.idx), lineType)
            self.gScene.addItem(gItmGroup)

            line_items.append(str(line.idx))

        self.obsTb.line_list_wdgt.clear()
        self.obsTb.line_list_wdgt.addItems(line_items)
        self.obsTb.line_list_wdgt.setCurrentRow(0)

        self.obsTb.line_newRecButton.setEnabled(False)
        self.obsTb.line_saveButton.setEnabled(True)
        self.obsTb.line_saveButton.setText('Edit line(s)')
        self.obsTb.line_saveButton.setIcon(QIcon('icons/edit.png'))

        zone_items = []
        for zone in q_zone:
            if zone.type != None:
                zoneType = zone.type.name
            else:
                zoneType = None
            gItmGroup = self.generate_itemGroup([point.x for point in zone.points], [point.y for point in zone.points],
                                                str(zone.idx), zoneType)
            self.gScene.addItem(gItmGroup)

            zone_items.append(str(zone.idx))

        self.obsTb.zone_list_wdgt.clear()
        self.obsTb.zone_list_wdgt.addItems(zone_items)
        self.obsTb.zone_list_wdgt.setCurrentRow(0)

        self.obsTb.zone_newRecButton.setEnabled(False)
        self.obsTb.zone_saveButton.setEnabled(True)
        self.obsTb.zone_saveButton.setText('Edit zone(s)')
        self.obsTb.zone_saveButton.setIcon(QIcon('icons/edit.png'))


    @staticmethod
    def convertMillis(millis):
        seconds = int(millis / 1000) % 60
        minutes = int(millis / (1000 * 60)) % 60
        hours = int(millis / (1000 * 60 * 60)) % 24
        return seconds, minutes, hours


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # app.setAttribute()
    app.setStyle('Fusion') #'Fusion', 'Windows', 'WindowsVista', 'Macintosh'
    player = VideoWindow()
    player.resize(640, 480)
    player.show()
    sys.exit(app.exec())