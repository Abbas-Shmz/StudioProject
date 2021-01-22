
# ===========================================================================================

from PyQt5.QtCore import (QDir, Qt, QUrl, QLineF, QPoint, QSize, QFile, QIODevice, QXmlStreamReader,
                          QXmlStreamWriter)
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtMultimediaWidgets import QVideoWidget, QGraphicsVideoItem
from PyQt5.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QLabel,
        QPushButton, QSizePolicy, QSlider, QStyle, QVBoxLayout, QWidget, QGraphicsView, QGraphicsScene,
        QGraphicsLineItem, QGraphicsTextItem, QGraphicsEllipseItem, QGridLayout, QComboBox,
        QOpenGLWidget, QMessageBox)
from PyQt5.QtWidgets import (QMainWindow, QAction, qApp, QStatusBar, QDialog,
                             QLineEdit)
from PyQt5.QtGui import QIcon, QBrush, QResizeEvent, QCursor, QPen, QFont, QColor
from PyQt5.QtOpenGL import QGLWidget

import xml.etree.ElementTree as ET

from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
from hachoir.core import config as HachoirConfig

import sys
import os
from datetime import datetime, timedelta

from framework.dbSchema import connectDatabase, Site_ODs

from observationToolbox import ObsToolbox

class GraphicView(QGraphicsView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graphicItem = None
        self.labelShape = None
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # self.setViewport(QOpenGLWidget())
        # self.setMouseTracking(True)

    def mousePressEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.parent().parent().drawLineAction.isChecked():
            p1 = self.mapToScene(event.x(), event.y())
            self.graphicItem = self.scene().addLine(QLineF(p1, p1))
            self.graphicItem.setPen(QPen(Qt.red))
            # self.graphicItem.setOpacity(0.25)
        elif event.buttons() == Qt.LeftButton and self.parent().parent().labelingAction.isChecked():
            dbfilename = self.scene().parent().obsTb.dbFilename
            if dbfilename != None:
                session = connectDatabase(dbfilename)
            else:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Information)
                msg.setText('The database file is not defined.')
                msg.setInformativeText('In order to set the database file, open the Observation Toolbox')
                msg.setIcon(QMessageBox.Critical)
                msg.exec_()
                self.parent().parent().labelingAction.setChecked(False)
                self.unsetCursor()
                return

            p = self.mapToScene(event.x(), event.y())
            labelShape = self.scene().addEllipse(p.x()-3.5, p.y()-3.5, 7, 7,
                                                 QPen(Qt.white, 0.5), QBrush(Qt.black))
            # labelShape.moveBy(-5, -5)

            labelWin = QDialog(self)
            labelWin.setModal(True)
            labelWinLayout = QVBoxLayout()

            labelWinGrid = QGridLayout()
            labelWinGrid.addWidget(QLabel('id'), 1,0)

            id_lineedit = QLineEdit()
            id_lineedit.setReadOnly(True)
            labelWinGrid.addWidget(id_lineedit, 1, 1)

            labelWinGrid.addWidget(QLabel('odName'), 0, 0)

            odName_cmbbx = QComboBox()
            labelWinGrid.addWidget(odName_cmbbx, 0, 1)

            odName_cmbbx.addItems([name[0] for name in session.query(Site_ODs.odName).all()])
            odName_cmbbx.setCurrentIndex(-1)

            labelWinLayout.addItem(labelWinGrid)
            addBtn = QPushButton('Add', labelWin)
            addBtn.setEnabled(False)
            addBtn.clicked.connect(lambda: self.labelAdd(p, id_lineedit, labelShape, session))

            cancelBtn = QPushButton('Cancel', labelWin)
            cancelBtn.clicked.connect(lambda: self.labelCancel(labelShape))

            odName_cmbbx.currentIndexChanged.connect(lambda: self.cmbbxIndexChanged(session, addBtn,
                                                                                    id_lineedit))

            btnsLayout = QHBoxLayout()
            btnsLayout.addWidget(cancelBtn)
            btnsLayout.addWidget(addBtn)
            labelWinLayout.addLayout(btnsLayout)
            labelWin.setLayout(labelWinLayout)
            labelWin.exec_()

        elif event.buttons() == Qt.LeftButton:
            self.parent().parent().play()

    def labelAdd(self, p, id_lineedit, labelShape, session):
        labelText = self.scene().addText(id_lineedit.text())
        labelFont = QFont()
        labelFont.setPointSize(5)
        labelFont.setBold(True)
        labelText.setFont(labelFont)
        labelText.setDefaultTextColor(Qt.white)
        labelText.setPos(p)
        labelText.moveBy(-labelText.boundingRect().width() / 2,
                         -labelText.boundingRect().height() / 2)

        od_type = session.query(Site_ODs.odType). \
            filter(Site_ODs.id == id_lineedit.text()).all()[0][0].name

        od_name = session.query(Site_ODs.odName). \
            filter(Site_ODs.id == id_lineedit.text()).all()[0][0]

        # labelShape.setToolTip("<h3>Name: {} <hr>Type: {}</h3>"
        #                 "".format(od_name, od_type))
        labelShape.setToolTip('Name: {}\nType: {}'.format(od_name, od_type))

        if od_type == 'sidewalk':
            labelShape.setBrush(QBrush(Qt.darkRed))
        elif od_type == 'road_lane':
            labelShape.setBrush(QBrush(Qt.darkGray))
        elif od_type == 'cycling_path':
            labelShape.setBrush(QBrush(Qt.darkGreen))
        elif od_type == 'bus_lane':
            labelShape.setBrush(QBrush(Qt.darkYellow))
        elif od_type == 'adjoining_ZOI':
            labelShape.setBrush(QBrush(Qt.darkBlue))

        # print(self.scene().parent().obsTb.dbFilename)
        self.sender().parent().close()

        self.sender().parent().parent().parent().parent().labelingAction.setChecked(False)
        self.sender().parent().parent().parent().parent().gView.unsetCursor()


    def labelCancel(self, labelShape):
        self.scene().removeItem(labelShape)
        self.sender().parent().close()


    def cmbbxIndexChanged(self, session, addBtn, id_lineedit):
        addBtn.setEnabled(True)
        id = session.query(Site_ODs.id).\
                           filter(Site_ODs.odName == self.sender().currentText()).all()[0][0]
        id_lineedit.setText(str(id))


    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.parent().parent().drawLineAction.isChecked():
            cursor = QCursor(Qt.CrossCursor)
            self.setCursor(cursor)

            p2 = self.mapToScene(event.x(), event.y())
            self.graphicItem.setLine(QLineF(self.graphicItem.line().p1(), p2))

    def mouseReleaseEvent(self, event):
        # if event.buttons() == Qt.LeftButton:# and self.parent().parent().drawLineAction.isChecked():
        self.parent().parent().drawLineAction.setChecked(False)
        self.unsetCursor()

    def resizeEvent(self, event):
        self.fitInView(self.items()[-1], Qt.KeepAspectRatio)

    def showEvent(self, event):
        self.fitInView(self.items()[-1], Qt.KeepAspectRatio)

    def mouseDoubleClickEvent(self, event):
        self.fitInView(self.items()[-1], Qt.KeepAspectRatio)
    #     print(self.items()[-1].boundingRect())

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
        self.gView.setSceneRect(0, 0, 320, 240)
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

        self.mediaPlayer = QMediaPlayer(self, QMediaPlayer.VideoSurface)
        self.mediaPlayer.setVideoOutput(self.videoItem)
        self.mediaPlayer.stateChanged.connect(self.mediaStateChanged)
        self.mediaPlayer.positionChanged.connect(self.positionChanged)
        self.mediaPlayer.durationChanged.connect(self.durationChanged)
        self.mediaPlayer.error.connect(self.handleError)
        self.mediaPlayer.setMuted(True)

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
        self.openVideoAction = QAction(QIcon('icons/video-file.png'), '&Open video file', self)
        self.openVideoAction.setShortcut('Ctrl+O')
        self.openVideoAction.setStatusTip('Open video file')
        self.openVideoAction.triggered.connect(self.openVideoFile)

        # Create observation action
        obsTbAction = QAction(QIcon('icons/checklist.png'), '&Observation toolbox', self)
        obsTbAction.setStatusTip('Open observation toolbox')
        obsTbAction.triggered.connect(self.openObsToolbox)

        self.drawLineAction = QAction(QIcon('icons/pencil.png'), 'Draw line', self)
        self.drawLineAction.setToolTip('Draw line over the video')
        self.drawLineAction.setCheckable(True)
        self.drawLineAction.triggered.connect(self.drawLabelClick)

        self.labelingAction = QAction(QIcon('icons/tags.png'), 'Labeling', self)
        self.labelingAction.setToolTip('Mark ODs over the video')
        self.labelingAction.setCheckable(True)
        self.labelingAction.triggered.connect(self.drawLabelClick)

        openProjectAction = QAction(QIcon('icons/open-project.png'), 'Open project', self)
        openProjectAction.setStatusTip('Open project')
        openProjectAction.triggered.connect(self.openProject)

        saveProjectAction = QAction(QIcon('icons/save-project.png'), 'Save project', self)
        saveProjectAction.setStatusTip('Save project')
        saveProjectAction.triggered.connect(self.saveProject)

        self.saveGraphAction = QAction(QIcon('icons/save-graphics.png'), 'Save graphics', self)
        self.saveGraphAction.setStatusTip('Save graphics')
        self.saveGraphAction.triggered.connect(self.saveGraphics)

        self.loadGraphAction = QAction(QIcon('icons/folders.png'), 'Load graphics', self)
        self.loadGraphAction.setStatusTip('Load graphics')
        self.loadGraphAction.triggered.connect(self.loadGraphics)


        # Create exit action
        exitAction = QAction(QIcon('icons/close.png'), '&Exit', self)
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
        self.toolbar.addAction(saveProjectAction)
        self.toolbar.addAction(self.openVideoAction)

        self.toolbar.insertSeparator(self.loadGraphAction)
        self.toolbar.addAction(self.loadGraphAction)
        self.toolbar.addAction(self.saveGraphAction)
        self.toolbar.addAction(self.drawLineAction)
        self.toolbar.addAction(self.labelingAction)

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
            creation_datetime = self.getVideoMetadata(self.videoFile)
            self.videoStartDatetime = self.videoCurrentDatetime = creation_datetime
            self.dateLabel.setText(creation_datetime.strftime('%a, %b %d, %Y'))

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
        if self.mediaPlayer.playbackRate() < 2:
            self.mediaPlayer.setPlaybackRate(self.mediaPlayer.playbackRate() + 0.2)
            self.statusBar.showMessage('Play back rate = x{}'.\
                                       format(round(self.mediaPlayer.playbackRate(),1)), 2000)

    def decrPlayRate(self):
        if self.mediaPlayer.playbackRate() > 0.2:
            self.mediaPlayer.setPlaybackRate(self.mediaPlayer.playbackRate() - 0.2)
            self.statusBar.showMessage('Play back rate = x{}'.\
                                       format(round(self.mediaPlayer.playbackRate(), 1)), 2000)

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

    def drawLabelClick(self):
        if self.sender() == self.drawLineAction:
            self.labelingAction.setChecked(False)
        else:
            self.drawLineAction.setChecked(False)
        cursor = QCursor(Qt.CrossCursor)
        self.gView.setCursor(cursor)

    def openProject(self):
        self.projectFile, _ = QFileDialog.getOpenFileName(self, "Open project file",
                                                  QDir.homePath(), "Project (*.prj)")
        # fileName = "/Users/Abbas/project.xml"
        if self.projectFile == '':
            return

        tree = ET.parse(self.projectFile)
        root = tree.getroot()
        gItems = []
        for elem in root:
            subEelTexts = {}
            for subelem in elem:
                subEelTexts[subelem.tag] = subelem.text
            gItems.append([elem.tag, subEelTexts])

        #print(gItems)

        for key in gItems:
            if key[0] == 'video':
                item = key[1]
                self.videoFile = item['fileName']
                self.openVideoFile()
                self.mediaPlayer.setPosition(int(item['sliderValue']))

            elif key[0] == 'graphics':
                item = key[1]
                print(item['fileName'])
                if item['fileName'] != None:
                    self.graphicsFile = item['fileName']
                    self.loadGraphics()

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

        self.setWindowTitle('{} - {}'.format(os.path.basename(self.videoFile),
                                             os.path.basename(self.projectFile)))


    def saveProject(self):
        self.saveGraphics()

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

        xmlWriter.writeStartElement('graphics')
        xmlWriter.writeTextElement("fileName", self.graphicsFile)
        xmlWriter.writeEndElement()

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

    def saveGraphics(self):
        if self.sender() == self.saveGraphAction or self.graphicsFile == '':
            if self.graphicsFile == '':
                fileDir = QDir.homePath()
            else:
                fileDir = self.graphicsFile

            self.graphicsFile, _ = QFileDialog.getSaveFileName(self, "Save graphics file",fileDir,
                                                               "Graphics (*.grpc)")
            if self.graphicsFile == '':
                return

        file = QFile(self.graphicsFile)
        if (not file.open(QIODevice.WriteOnly | QIODevice.Text)):
            return

        xmlWriter = QXmlStreamWriter(file)
        xmlWriter.setAutoFormatting(True)
        xmlWriter.writeStartDocument()

        xmlWriter.writeStartElement('graphicItems')

        for item in self.gScene.items():
            if isinstance(item, QGraphicsLineItem):
                xmlWriter.writeStartElement('line')

                xmlWriter.writeTextElement("x1", str(item.line().x1()))
                xmlWriter.writeTextElement("y1", str(item.line().y1()))
                xmlWriter.writeTextElement("x2", str(item.line().x2()))
                xmlWriter.writeTextElement("y2", str(item.line().y2()))
                xmlWriter.writeTextElement("zValue", str(item.zValue()))
                xmlWriter.writeTextElement("color", "{},{},{}".format(str(item.pen().color().red()),
                                                                      str(item.pen().color().green()),
                                                                      str(item.pen().color().blue())))

                xmlWriter.writeEndElement()
            elif isinstance(item, QGraphicsEllipseItem):
                xmlWriter.writeStartElement('ellipse')
                xmlWriter.writeTextElement("x", str(item.rect().x()))
                xmlWriter.writeTextElement("y", str(item.rect().y()))
                xmlWriter.writeTextElement("height", str(item.rect().height()))
                xmlWriter.writeTextElement("width", str(item.rect().width()))
                xmlWriter.writeTextElement("toolTip", str(item.toolTip()))
                xmlWriter.writeTextElement("zValue", str(item.zValue()))
                xmlWriter.writeTextElement("color_pen", "{},{},{}".
                                           format(str(item.pen().color().red()),
                                                  str(item.pen().color().green()),
                                                  str(item.pen().color().blue())))
                xmlWriter.writeTextElement("color_brush", "{},{},{}".
                                           format(str(item.brush().color().red()),
                                                  str(item.brush().color().green()),
                                                  str(item.brush().color().blue())))
                xmlWriter.writeEndElement()

            elif isinstance(item, QGraphicsTextItem):
                xmlWriter.writeStartElement('text')
                xmlWriter.writeTextElement("x", str(item.x()))
                xmlWriter.writeTextElement("y", str(item.y()))
                xmlWriter.writeTextElement("PlainText", str(item.toPlainText()))
                xmlWriter.writeTextElement("zValue", str(item.zValue()))
                xmlWriter.writeTextElement("font_size", str(item.font().pointSize()))
                xmlWriter.writeTextElement("font_bold", str(item.font().bold()))
                xmlWriter.writeTextElement("color_text", "{},{},{}".
                                           format(str(item.defaultTextColor().red()),
                                                  str(item.defaultTextColor().green()),
                                                  str(item.defaultTextColor().blue())))

                xmlWriter.writeEndElement()


        xmlWriter.writeEndDocument()

    def loadGraphics(self):
        if self.sender() == self.loadGraphAction:
            self.graphicsFile, _ = QFileDialog.getOpenFileName(self, "Open graphics file",
                                                  QDir.homePath(), "Graphics files (*.grpc)")
        if self.graphicsFile == '':
            return

        tree = ET.parse(self.graphicsFile)
        root = tree.getroot()
        gItems = []
        for elem in root:
            subEelTexts = {}
            for subelem in elem:
                subEelTexts[subelem.tag] = subelem.text
            gItems.append([elem.tag, subEelTexts])

        # print(gItems)
        # self.gScene.clear()

        for key in gItems:
            if key[0] == 'line':
                item = key[1]
                lineItem = QGraphicsLineItem(float(item['x1']), float(item['y1']),
                                             float(item['x2']), float(item['y2']))
                pen = QPen()
                r, g, b = item['color'].split(',')
                pen.setColor(QColor(int(r), int(g), int(b)))
                lineItem.setPen(pen)
                lineItem.setZValue(float(item['zValue']))
                self.gScene.addItem(lineItem)

            elif key[0] == 'ellipse':
                item = key[1]
                ellipseItem = QGraphicsEllipseItem(float(item['x']), float(item['y']),
                                                   float(item['width']), float(item['height']))

                pen = QPen()
                r, g, b = item['color_pen'].split(',')
                pen.setColor(QColor(int(r), int(g), int(b)))
                ellipseItem.setPen(pen)

                r, g, b = item['color_brush'].split(',')
                brush = QBrush(QColor(int(r), int(g), int(b)))
                ellipseItem.setBrush(brush)
                ellipseItem.setToolTip(item['toolTip'])

                ellipseItem.setZValue(float(item['zValue']))
                self.gScene.addItem(ellipseItem)

            elif key[0] == 'text':
                item = key[1]
                textItem = QGraphicsTextItem(item['PlainText'])
                textItem.setPos(float(item['x']), float(item['y']))
                r, g, b = item['color_text'].split(',')
                textItem.setDefaultTextColor(QColor(int(r), int(g), int(b)))
                font = QFont()
                font.setPointSize(int(item['font_size']))
                font.setBold(bool(item['font_bold']))
                textItem.setFont(font)
                textItem.setZValue(1)

                self.gScene.addItem(textItem)


        # file = QFile('/Users/Abbas/test.xml')
        # if (not file.open(QIODevice.ReadOnly | QIODevice.Text)):
        #     return
        #
        # xmlReader = QXmlStreamReader(file)
        #
        # while not xmlReader.atEnd():# readNextStartElement():
        #     xmlReader.readNext()
        #     # print(xmlReader.name())
        #     # print(xmlReader.tokenType())
        #     # print(xmlReader.isCharacters())
        #
        #     if xmlReader.name() == 'ellipse':
        #         xmlReader.readNextStartElement()
        #         n = xmlReader.name()
        #         while n != 'ellipse': #for i in range(6):
        #             print(xmlReader.readElementText())
        #             n = xmlReader.name()
        #             print(n)
        #
        #             xmlReader.readNextStartElement()
        #             print(xmlReader.name())
        #
        #         # print(xmlReader.tokenType())
        #         # print(xmlReader.readElementText())
        #
        #         # xmlReader.readNext()
        #         # xmlReader.readNext()
        #         # print(xmlReader.isStartElement())
        #         # print(xmlReader.readElementText())
        #         # print(xmlReader.tokenType())
        #         # print(xmlReader.name())
        #
        #         # xmlReader.readNextStartElement()
        #         # print(xmlReader.readElementText())
        #         # print(xmlReader.tokenType())
        #         # print('line: ' + str(xmlReader.lineNumber()))
        #         # print('col: ' + str(xmlReader.columnNumber()))

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


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion') #'Fusion', 'Windows', 'WindowsVista', 'Macintosh'
    player = VideoWindow()
    player.resize(640, 480)
    player.show()
    sys.exit(app.exec_())