
# ===========================================================================================

from PyQt5.QtCore import QDir, Qt, QUrl, QLineF, QPoint, QSize
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtMultimediaWidgets import QVideoWidget, QGraphicsVideoItem
from PyQt5.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QLabel,
        QPushButton, QSizePolicy, QSlider, QStyle, QVBoxLayout, QWidget, QGraphicsView, QGraphicsScene,
        QGraphicsLineItem, QGraphicsTextItem, QGridLayout, QComboBox, QOpenGLWidget, QMessageBox,
        QButtonGroup)
from PyQt5.QtWidgets import (QMainWindow, QAction, qApp, QStatusBar, QDialog,
                             QLineEdit)
from PyQt5.QtGui import QIcon, QBrush, QResizeEvent, QCursor, QPen, QFont
from PyQt5.QtOpenGL import QGLWidget

from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
from hachoir.core import config as HachoirConfig

import sys
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
            labelShape = self.scene().addEllipse(p.x(), p.y(), 10, 10,
                                                 QPen(Qt.white, 0.75), QBrush(Qt.black))
            labelShape.moveBy(-5, -5)

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
        labelFont.setPointSize(6)
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

        labelShape.setToolTip("<h3>Name: {} <hr>Type: {}</h3>"         
                        "".format(od_name, od_type))
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


        self.obsTb = ObsToolbox(self)

        self.videoStartDatetime = None
        self.videoCurrentDatetime = None

        # ===================== Setting video item ==============================
        self.videoItem = QGraphicsVideoItem()
        self.videoItem.setAspectRatioMode(Qt.KeepAspectRatio)
        self.gScene.addItem(self.videoItem)

        self.mediaPlayer = QMediaPlayer(self, QMediaPlayer.VideoSurface)
        self.mediaPlayer.setVideoOutput(self.videoItem)
        # self.mediaPlayer.stateChanged.connect(self.on_stateChanged)
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


        # Create open action
        openAction = QAction(QIcon('icons/video-file.png'), '&Open video file', self)  # QIcon('open.png'),
        # openAction.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        openAction.setShortcut('Ctrl+O')
        openAction.setStatusTip('Open video file')
        openAction.triggered.connect(self.openFile)

        # Create observation action
        obsTbAction = QAction(QIcon('icons/clipboards.png'), '&Observation toolbox', self)  # QIcon('open.png'),
        # obsTbAction.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        # obsTbAction.setShortcut('Ctrl+O')
        obsTbAction.setStatusTip('Open obseration toolbox')
        obsTbAction.triggered.connect(self.openObsToolbox)

        self.drawLineAction = QAction(QIcon('icons/pencil.png'), 'Draw line', self)
        self.drawLineAction.setToolTip('Draw line over the video')
        self.drawLineAction.setCheckable(True)
        self.drawLineAction.triggered.connect(self.drawLabelClick)

        self.labelingAction = QAction(QIcon('icons/tags.png'), 'Labeling', self)
        self.labelingAction.setToolTip('Mark ODs over the video')
        self.labelingAction.setCheckable(True)
        self.labelingAction.triggered.connect(self.drawLabelClick)


        # Create exit action
        exitAction = QAction(QIcon('icons/close.png'), '&Exit', self)
        # exitAction.setIcon(self.style().standardIcon(QStyle.SP_BrowserStop))
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(qApp.quit)  # self.exitCall

        # Create menu bar and add action
        # menuBar = self.menuBar()
        # menuBar.setNativeMenuBar(False)
        # fileMenu = menuBar.addMenu('&File')
        # fileMenu.addAction(openAction)
        # fileMenu.addAction(obsTbAction)
        # fileMenu.addAction(exitAction)

        self.toolbar = self.addToolBar('Tools')
        self.toolbar.setIconSize(QSize(24, 24))
        self.toolbar.addAction(openAction)
        self.toolbar.addAction(self.drawLineAction)
        self.toolbar.addAction(self.labelingAction)
        self.toolbar.addAction(obsTbAction)
        self.toolbar.addAction(exitAction)


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
        fileName, _ = QFileDialog.getOpenFileName(self, "Open video", QDir.homePath())

        if fileName != '':
            creation_datetime = self.getVideoMetadata(fileName)
            self.videoStartDatetime = self.videoCurrentDatetime = creation_datetime
            self.dateLabel.setText(creation_datetime.strftime('%a, %b %d, %Y'))

            self.mediaPlayer.setMedia(QMediaContent(QUrl.fromLocalFile(fileName)))
            self.playButton.setEnabled(True)
            self.setWindowTitle(fileName)
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