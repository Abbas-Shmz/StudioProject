import sys
import os
import pandas as pd
import numpy as np
import datetime
import sqlite3
import ast
from enum import Enum as eEnum
from pathlib import Path
from configparser import ConfigParser
from PyQt5.QtWidgets import (QApplication, QWidget, QGridLayout, QVBoxLayout, QHBoxLayout,
                             QToolBox, QPushButton, QTextEdit, QLineEdit, QMainWindow,
                             QComboBox, QGroupBox, QDateTimeEdit, QAction, QStyle,
                             QFileDialog, QToolBar, QMessageBox, QDialog, QLabel, QGraphicsItemGroup,
                             QSizePolicy, QStatusBar, QTableWidget, QHeaderView, QTableWidgetItem,
                             QAbstractItemView, QTableView, QListWidget, QListWidgetItem)
from PyQt5.QtGui import QColor, QIcon, QFont, QCursor
from PyQt5.QtCore import QDateTime, QSize, QDir, Qt, QAbstractTableModel, QObject, QThread, pyqtSignal

from iframework import createDatabase, connectDatabase, Person, Mode, Group, GroupBelonging, Vehicle,\
    Activity, LinePassing, ZoneCrossing, Point, Line, Zone, pointLineAssociation

import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt

from indicators import tempDistHist, stackedHist, odMatrix, pieChart, generateReport, \
    calculateNoBins, getPeakHours, getObsStartEnd, compareIndicators, calculateBinsEdges, \
    plotTrajectory, importTrajectory, speedBoxPlot, userTypeNames, userTypeColors, creatStreetusers, \
    modeShareCompChart, speedHistogram
import iframework
from trafficintelligence.storage import ProcessParameters, moving, saveTrajectoriesToSqlite
from trafficintelligence.cvutils import imageToWorldProject, worldToImageProject

from sqlalchemy import Enum, Boolean, DateTime
from sqlalchemy.inspection import inspect
from sqlalchemy import func

global session
session = None

config_object = ConfigParser()
cfg = config_object.read("config.ini")
actionTypeList = ['crossing line', 'entering zone', 'exiting zone', 'crossing zone',
                  'dwelling zone']

class ObsToolbox(QMainWindow):
    def __init__(self, parent=None):
        super(ObsToolbox, self).__init__(parent)
        self.resize(400, 650)
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.groupPersons = {} # {person_idx: [person, mode, vehicle]}
        self.groups = {}  # {group_idx: [group, {linepassings}, {ZoneCrossings}, {Activities}]}
        self.IsChangedManually = True
        self.traj_line = None

        # global session
        self.dbFilename = None #'/Users/Abbas/AAAA/Stuart2019_iframework.sqlite'

        layout = QVBoxLayout() #QGridLayout()

        #--------------------------------------------
        # self.setWindowTitle(os.path.basename(self.dbFilename))
        #
        # session = createDatabase(self.dbFilename)
        #
        # if session is None:
        #     session = connectDatabase(self.dbFilename)
        #-----------------------------------------------

        # styleSheet = """
        #                 QToolBox::tab {
        #                     border: 1px solid #C4C4C3;
        #                     border-bottom-color: RGB(0, 0, 255);
        #                 }
        #                 QToolBox::tab:selected {
        #                     background-color: #f14040;
        #                     border-bottom-style: none;
        #                 }
        #              """

        styleSheet = """
                                QToolBox::tab { color: darkblue; }
                                QToolBox::tab:selected { font: bold; }
                                QToolBox{ icon-size: 15px; }
                             """

        self.toolbox = QToolBox()
        self.toolbox.setStyleSheet(styleSheet)
        layout.addWidget(self.toolbox)#, 0, 0)

        self.openAction = QAction(QIcon('icons/database.png'), '&Create/Open iFramework database', self)
        self.openAction.setShortcut('Ctrl+O')
        self.openAction.setStatusTip('Open database file')
        self.openAction.triggered.connect(self.opendbFile)

        tempHistAction = QAction(QIcon('icons/histogram.png'), '&Temporal Histogram', self)
        # openAction.setShortcut('Ctrl+O')
        # openAction.setStatusTip('Open database file')
        tempHistAction.triggered.connect(self.tempHist)

        stackHistAction = QAction(QIcon('icons/stacked.png'), '&Stacked Histogram', self)
        stackHistAction.triggered.connect(self.stackedHist)

        speedPlotAction = QAction(QIcon('icons/speed.png'), 'Speed Plot', self)
        speedPlotAction.triggered.connect(self.speedPlot)

        odMatrixAction = QAction(QIcon('icons/grid.png'), '&OD Matrix', self)
        odMatrixAction.triggered.connect(self.odMatrix)

        pieChartAction = QAction(QIcon('icons/pie-chart.png'), '&Pie Chart', self)
        pieChartAction.triggered.connect(self.pieChart)

        modeChartAction = QAction(QIcon('icons/modes.png'), '&Mode Chart', self)
        modeChartAction.triggered.connect(self.modeChart)

        compHistAction = QAction(QIcon('icons/comparison.png'), '&Comparative Histogram', self)
        compHistAction.triggered.connect(self.compHist)

        reportAction = QAction(QIcon('icons/report.png'), '&Indicators Report', self)
        reportAction.triggered.connect(self.genReport)

        compIndAction = QAction(QIcon('icons/positive.png'), '&Before/After Comparison', self)
        compIndAction.triggered.connect(self.compIndicators)

        importTrajAction = QAction(QIcon('icons/import.png'), '&Import trajectories', self)
        importTrajAction.triggered.connect(self.importTrajectories)

        plotTrajAction = QAction(QIcon('icons/trajectory.png'), '&Plot trajectories', self)
        plotTrajAction.triggered.connect(self.plotTrajectories)

        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(24, 24))
        self.toolbar.addAction(self.openAction)
        self.toolbar.addAction(tempHistAction)
        # self.toolbar.addAction(stackHistAction)
        self.toolbar.addAction(speedPlotAction)
        # self.toolbar.addAction(odMatrixAction)
        self.toolbar.addAction(pieChartAction)
        self.toolbar.addAction(modeChartAction)
        self.toolbar.addAction(compHistAction)
        self.toolbar.addAction(reportAction)
        self.toolbar.addAction(compIndAction)
        self.toolbar.insertSeparator(tempHistAction)
        self.toolbar.addAction(importTrajAction)
        self.toolbar.addAction(plotTrajAction)
        self.toolbar.insertSeparator(importTrajAction)
        self.addToolBar(Qt.LeftToolBarArea, self.toolbar)

        # ++++++++++++++++++ Toolbox tabs +++++++++++++++++++++++++
        # =================== Road user tab =======================
        user_tab_wdgt = QWidget()
        user_tab_layout = QVBoxLayout()
        user_newBtnsLayout = QHBoxLayout()
        user_saveBtnsLayout = QHBoxLayout()

        # ----------- GROUP groupPersons box -------------
        self.group_grpBox = QGroupBox('Group')
        group_grpBox_layout = QGridLayout()
        group_newBtnsLayout = QHBoxLayout()
        group_saveBtnsLayout = QHBoxLayout()

        self.user_newGroupButton = QPushButton(QIcon('icons/group.png'), 'New group')
        self.user_newGroupButton.clicked.connect(self.user_newGroup_click)
        group_grpBox_layout.addWidget(self.user_newGroupButton, 0, 0, 1, 3)

        group_grpBox_layout.addWidget(QLabel('Group idx:'), 1, 0)
        self.group_idx_cmbBox = QComboBox()
        self.group_idx_cmbBox.currentTextChanged.connect(self.group_idx_changed)
        group_grpBox_layout.addWidget(self.group_idx_cmbBox, 1, 1)

        self.user_newRecButton = QPushButton(QIcon('icons/person.png'), 'New user')
        self.user_newRecButton.setEnabled(False)
        self.user_newRecButton.clicked.connect(self.user_newRecBtn_click)
        group_grpBox_layout.addWidget(self.user_newRecButton, 1, 2)
        # user_tab_layout.addLayout(user_newBtnsLayout)


        self.group_list_wdgt = QListWidget()
        self.group_list_wdgt.setSelectionMode(QAbstractItemView.SingleSelection)
        self.group_list_wdgt.currentRowChanged.connect(self.rowChanged)
        # group_grid_layout.addWidget(self.group_list_wdgt)
        group_grpBox_layout.addWidget(self.group_list_wdgt, 2, 0, 1, 3)

        self.group_delFromListButton = QPushButton(QIcon('icons/delete.png'), 'Delete selected user')
        self.group_delFromListButton.setEnabled(False)
        self.group_delFromListButton.clicked.connect(self.group_delFromList_click)
        group_grpBox_layout.addWidget(self.group_delFromListButton, 3, 0, 1, 2)

        self.group_delGroupButton = QPushButton(QIcon('icons/delete.png'), 'Delete group')
        self.group_delGroupButton.setEnabled(False)
        self.group_delGroupButton.clicked.connect(self.group_delGroupBtn_click)
        group_grpBox_layout.addWidget(self.group_delGroupButton, 3, 2)

        # group_grpBox_wdgt.setLayout(group_grid_layout)
        # group_grpBox_layout.addWidget(group_grpBox_wdgt)
        self.group_grpBox.setLayout(group_grpBox_layout)
        # self.group_grpBox.setEnabled(False)

        user_tab_layout.addWidget(self.group_grpBox)

        # ----------------- PERSON groupPersons box --------------------------
        self.person_grpBox = self.generateWidgets(Person, 'All', False)
        user_tab_layout.addWidget(self.person_grpBox)

        # ----------- MODE groupPersons box --------------
        self.mode_grpBox = self.generateWidgets(Mode, 'NoPrFo', True)
        user_tab_layout.addWidget(self.mode_grpBox)

        # ----------------- VEHICLE -------------------------
        self.veh_grpBox = self.generateWidgets(Vehicle, 'NoPrFo', True)
        user_tab_layout.addWidget(self.veh_grpBox)

        # ------- ROAD USER save buttons --------------
        self.user_saveButton = QPushButton(QIcon('icons/save.png'), 'Save user(s) in the group')
        self.user_saveButton.clicked.connect(self.user_saveBtn_click)
        self.user_saveButton.setEnabled(False)
        user_saveBtnsLayout.addWidget(self.user_saveButton)
        user_tab_layout.addLayout(user_saveBtnsLayout)

        user_tab_wdgt.setLayout(user_tab_layout)
        self.toolbox.addItem(user_tab_wdgt, QIcon('icons/person.png'), 'Street user')

        # ------------------ LinePassing tab --------------------------
        linepass_tab_wdgt = QWidget()
        linepass_tab_layout = QVBoxLayout()
        linepass_newBtnsLayout = QHBoxLayout()
        linepass_listGrpB_layout = QVBoxLayout()
        linepass_saveBtnsLayout = QHBoxLayout()

        self.linepass_newRecButton = QPushButton(QIcon('icons/new.png'), 'New line passing')
        self.linepass_newRecButton.clicked.connect(self.linepass_newRecBtn_click)
        linepass_newBtnsLayout.addWidget(self.linepass_newRecButton)
        linepass_tab_layout.addLayout(linepass_newBtnsLayout)

        self.linepass_listGrpBox = QGroupBox('Line passings')
        # self.linepass_listGrpBox.setEnabled(False)

        self.linepass_list_wdgt = QListWidget()
        self.linepass_list_wdgt.setSelectionMode(QAbstractItemView.SingleSelection)
        self.linepass_list_wdgt.currentRowChanged.connect(self.rowChanged)
        linepass_listGrpB_layout.addWidget(self.linepass_list_wdgt)

        self.linepass_delFromListButton = QPushButton(QIcon('icons/delete.png'), 'Delete selected linepassing')
        self.linepass_delFromListButton.setEnabled(False)
        self.linepass_delFromListButton.clicked.connect(self.linepass_delFromList_click)
        linepass_listGrpB_layout.addWidget(self.linepass_delFromListButton)

        self.linepass_listGrpBox.setLayout(linepass_listGrpB_layout)
        linepass_tab_layout.addWidget(self.linepass_listGrpBox)

        self.linepass_grpBox = self.generateWidgets(LinePassing, 'NoPrFo', False)
        linepass_tab_layout.addWidget(self.linepass_grpBox)

        self.linepass_saveButton = QPushButton(QIcon('icons/save.png'), 'Save line passings')
        self.linepass_saveButton.clicked.connect(self.linepass_saveBtn_click)
        self.linepass_saveButton.setEnabled(False)
        linepass_saveBtnsLayout.addWidget(self.linepass_saveButton)
        linepass_tab_layout.addLayout(linepass_saveBtnsLayout)

        linepass_tab_wdgt.setLayout(linepass_tab_layout)
        self.toolbox.addItem(linepass_tab_wdgt, QIcon('icons/linePassing.png'), 'Line Passing')

        # ------------------ ZoneCrossing tab --------------------------
        zonepass_tab_wdgt = QWidget()
        zonepass_tab_layout = QVBoxLayout()
        zonepass_listGrpB_layout = QVBoxLayout()
        zonepass_newBtnsLayout = QHBoxLayout()
        zonepass_saveBtnsLayout = QHBoxLayout()

        self.zonepass_newRecButton = QPushButton(QIcon('icons/new.png'), 'New zone crossing')
        self.zonepass_newRecButton.clicked.connect(self.zonepass_newRecBtn_click)
        zonepass_newBtnsLayout.addWidget(self.zonepass_newRecButton)
        zonepass_tab_layout.addLayout(zonepass_newBtnsLayout)

        self.zonepass_listGrpBox = QGroupBox('Zone crossings')
        # self.zonepass_listGrpBox.setEnabled(False)

        self.zonepass_list_wdgt = QListWidget()
        self.zonepass_list_wdgt.setSelectionMode(QAbstractItemView.SingleSelection)
        self.zonepass_list_wdgt.currentRowChanged.connect(self.rowChanged)
        zonepass_listGrpB_layout.addWidget(self.zonepass_list_wdgt)
        self.zonepass_listGrpBox.setLayout(zonepass_listGrpB_layout)
        zonepass_tab_layout.addWidget(self.zonepass_listGrpBox)

        self.zonepass_delFromListButton = QPushButton(QIcon('icons/delete.png'), 'Delete selected ZoneCrossing')
        self.zonepass_delFromListButton.setEnabled(False)
        self.zonepass_delFromListButton.clicked.connect(self.zonepass_delFromList_click)
        zonepass_listGrpB_layout.addWidget(self.zonepass_delFromListButton)

        self.zonepass_grpBox = self.generateWidgets(ZoneCrossing, 'NoPrFo', False)
        zonepass_tab_layout.addWidget(self.zonepass_grpBox)

        self.zonepass_saveButton = QPushButton(QIcon('icons/save.png'), 'Save zone crossing')
        self.zonepass_saveButton.clicked.connect(self.zonepass_saveBtn_click)
        self.zonepass_saveButton.setEnabled(False)
        zonepass_saveBtnsLayout.addWidget(self.zonepass_saveButton)
        zonepass_tab_layout.addLayout(zonepass_saveBtnsLayout)

        zonepass_tab_wdgt.setLayout(zonepass_tab_layout)
        self.toolbox.addItem(zonepass_tab_wdgt, QIcon('icons/Zonepassing.png'), 'Zone Crossing')

        # --------------------- Activity tab --------------------------
        act_tab_wdgt = QWidget()
        act_tab_layout = QVBoxLayout()
        act_listGrpB_layout = QVBoxLayout()
        act_newBtnsLayout = QHBoxLayout()
        act_saveBtnsLayout = QHBoxLayout()

        self.act_newRecButton = QPushButton(QIcon('icons/new.png'), 'New activity')
        self.act_newRecButton.clicked.connect(self.act_newRecBtn_click)
        act_newBtnsLayout.addWidget(self.act_newRecButton)
        act_tab_layout.addLayout(act_newBtnsLayout)

        self.act_listGrpBox = QGroupBox('Activities')
        # self.act_listGrpBox.setEnabled(False)

        self.act_list_wdgt = QListWidget()
        self.act_list_wdgt.setSelectionMode(QAbstractItemView.SingleSelection)
        self.act_list_wdgt.currentRowChanged.connect(self.rowChanged)
        act_listGrpB_layout.addWidget(self.act_list_wdgt)
        self.act_listGrpBox.setLayout(act_listGrpB_layout)
        act_tab_layout.addWidget(self.act_listGrpBox)

        self.act_delFromListButton = QPushButton(QIcon('icons/delete.png'), 'Delete selected activity')
        self.act_delFromListButton.setEnabled(False)
        self.act_delFromListButton.clicked.connect(self.act_delFromList_click)
        act_listGrpB_layout.addWidget(self.act_delFromListButton)

        self.act_grpBox = self.generateWidgets(Activity, 'NoPrFo', False)
        act_tab_layout.addWidget(self.act_grpBox)

        self.act_saveButton = QPushButton(QIcon('icons/save.png'), 'Save activity')
        self.act_saveButton.clicked.connect(self.act_saveBtn_click)
        self.act_saveButton.setEnabled(False)
        act_saveBtnsLayout.addWidget(self.act_saveButton)
        act_tab_layout.addLayout(act_saveBtnsLayout)

        act_tab_wdgt.setLayout(act_tab_layout)
        self.toolbox.addItem(act_tab_wdgt, QIcon('icons/activity.png'), 'Activity')

        # ---------------------------- Line tab --------------------------
        line_tab_wdgt = QWidget()
        line_tab_layout = QVBoxLayout()
        line_listGrpB_layout = QVBoxLayout()
        line_newBtnsLayout = QHBoxLayout()
        line_saveBtnsLayout = QHBoxLayout()

        self.line_newRecButton = QPushButton(QIcon('icons/drawLine.png'), 'Draw a new line over the video')
        self.line_newRecButton.setCheckable(True)
        self.line_newRecButton.clicked.connect(self.line_newRecBtn_click)
        line_newBtnsLayout.addWidget(self.line_newRecButton)
        line_tab_layout.addLayout(line_newBtnsLayout)

        self.line_listGrpBox = QGroupBox('Lines')
        # self.act_listGrpBox.setEnabled(False)

        self.line_list_wdgt = QListWidget()
        self.line_list_wdgt.setSelectionMode(QAbstractItemView.SingleSelection)
        self.line_list_wdgt.currentRowChanged.connect(self.rowChanged)
        line_listGrpB_layout.addWidget(self.line_list_wdgt)
        self.line_listGrpBox.setLayout(line_listGrpB_layout)
        line_tab_layout.addWidget(self.line_listGrpBox)

        self.line_delFromListButton = QPushButton(QIcon('icons/delete.png'), 'Delete selected line')
        self.line_delFromListButton.setEnabled(False)
        self.line_delFromListButton.clicked.connect(self.line_delFromList_click)
        line_listGrpB_layout.addWidget(self.line_delFromListButton)

        self.line_grpBox = self.generateWidgets(Line, 'NoPrFo', False)
        line_tab_layout.addWidget(self.line_grpBox)

        self.line_saveButton = QPushButton(QIcon('icons/save.png'), 'Save line(s)')
        self.line_saveButton.clicked.connect(self.line_saveBtn_click)
        self.line_saveButton.setEnabled(False)
        line_saveBtnsLayout.addWidget(self.line_saveButton)
        line_tab_layout.addLayout(line_saveBtnsLayout)

        line_tab_wdgt.setLayout(line_tab_layout)
        self.toolbox.addItem(line_tab_wdgt, QIcon('icons/line.png'), 'Line')

        # ---------------------------- Zone tab --------------------------
        zone_tab_wdgt = QWidget()
        zone_tab_layout = QVBoxLayout()
        zone_listGrpB_layout = QVBoxLayout()
        zone_newBtnsLayout = QHBoxLayout()
        zone_saveBtnsLayout = QHBoxLayout()

        self.zone_newRecButton = QPushButton(QIcon('icons/drawZone.png'), 'Draw a new zone over the video')
        self.zone_newRecButton.setCheckable(True)
        self.zone_newRecButton.clicked.connect(self.zone_newRecBtn_click)
        zone_newBtnsLayout.addWidget(self.zone_newRecButton)
        zone_tab_layout.addLayout(zone_newBtnsLayout)

        self.zone_listGrpBox = QGroupBox('Zones')
        # self.act_listGrpBox.setEnabled(False)

        self.zone_list_wdgt = QListWidget()
        self.zone_list_wdgt.setSelectionMode(QAbstractItemView.SingleSelection)
        self.zone_list_wdgt.currentRowChanged.connect(self.rowChanged)
        zone_listGrpB_layout.addWidget(self.zone_list_wdgt)
        self.zone_listGrpBox.setLayout(zone_listGrpB_layout)
        zone_tab_layout.addWidget(self.zone_listGrpBox)

        self.zone_delFromListButton = QPushButton(QIcon('icons/delete.png'), 'Delete selected zone')
        self.zone_delFromListButton.setEnabled(False)
        self.zone_delFromListButton.clicked.connect(self.zone_delFromList_click)
        zone_listGrpB_layout.addWidget(self.zone_delFromListButton)

        self.zone_grpBox = self.generateWidgets(Zone, 'NoPrFo', False)
        zone_tab_layout.addWidget(self.zone_grpBox)

        self.zone_saveButton = QPushButton(QIcon('icons/save.png'), 'Save zone(s)')
        self.zone_saveButton.clicked.connect(self.zone_saveBtn_click)
        self.zone_saveButton.setEnabled(False)
        zone_saveBtnsLayout.addWidget(self.zone_saveButton)
        zone_tab_layout.addLayout(zone_saveBtnsLayout)

        zone_tab_wdgt.setLayout(zone_tab_layout)
        self.toolbox.addItem(zone_tab_wdgt, QIcon('icons/zone.png'), 'Zone')

        # --------------------- TI Trajectory tab --------------------------
        traj_tab_wdgt = QWidget()
        traj_tab_layout = QVBoxLayout()
        traj_tab_mdbLayout = QHBoxLayout()
        traj_tab_gridLayout = QGridLayout()
        traj_tab_editLayout = QGridLayout()

        traj_tab_mdbLayout.addWidget(QLabel('Metadata:'))
        self.mdbFileLedit = QLineEdit()
        traj_tab_mdbLayout.addWidget(self.mdbFileLedit)

        self.openMdbFileBtn = QPushButton()
        self.openMdbFileBtn.setIcon(QIcon('icons/open-file.png'))
        self.openMdbFileBtn.setToolTip('Open configuration file')
        self.openMdbFileBtn.clicked.connect(self.openMdbFile)
        traj_tab_mdbLayout.addWidget(self.openMdbFileBtn)

        # traj_tab_gridLayout.addWidget(NavigationToolbar(self.canvas, self, False), 2, 0, 1, 4)  # , Qt.AlignLeft)

        traj_tab_gridLayout.addWidget(QLabel('Site:'), 0, 0)  # , Qt.AlignRight)
        self.siteNameCombobx = QComboBox()
        # self.siteNameCombobx.setMinimumWidth(120)
        self.siteNameCombobx.currentTextChanged.connect(self.siteChanged)
        traj_tab_gridLayout.addWidget(self.siteNameCombobx, 0, 1)  # , Qt.AlignLeft)

        traj_tab_gridLayout.addWidget(QLabel('Cam. view:'), 0, 2)  # , Qt.AlignRight)
        self.camViewCombobx = QComboBox()
        self.camViewCombobx.currentTextChanged.connect(self.viewChanged)
        traj_tab_gridLayout.addWidget(self.camViewCombobx, 0, 3)  # , Qt.AlignLeft)

        traj_tab_gridLayout.addWidget(QLabel('Traj DB:'), 1, 0)  # , Qt.AlignRight)
        self.trjDbCombobx = QComboBox()
        # self.trjDbCombobx.setMinimumWidth(130)
        # self.trjDbCombobx.currentTextChanged.connect(self.plotItems)
        traj_tab_gridLayout.addWidget(self.trjDbCombobx, 1, 1, 1, 2)  # , Qt.AlignLeft)

        self.plotBtn = QPushButton('Plot')
        self.plotBtn.clicked.connect(self.plotItems)
        # self.plotBtn.setEnabled(False)
        traj_tab_gridLayout.addWidget(self.plotBtn, 1, 3)

        self.prevTrjBtn = QPushButton('<<')
        self.prevTrjBtn.setFixedWidth(35)
        self.prevTrjBtn.clicked.connect(self.prevTrajectory)
        # self.prevTrjBtn.setEnabled(False)
        traj_tab_editLayout.addWidget(self.prevTrjBtn, 0, 1)

        self.trjIdxLe = QLineEdit('-1')
        # self.trjIdxLe.setMinimumWidth(35)
        self.trjIdxLe.setReadOnly(True)
        traj_tab_editLayout.addWidget(self.trjIdxLe, 0, 2)

        self.noTrjLabel = QLabel('/--')
        traj_tab_editLayout.addWidget(self.noTrjLabel, 0, 3)

        self.nextTrjBtn = QPushButton('>>')
        self.nextTrjBtn.setFixedWidth(35)
        self.nextTrjBtn.clicked.connect(self.nextTrajectory)
        # self.nextTrjBtn.setEnabled(False)
        traj_tab_editLayout.addWidget(self.nextTrjBtn, 0, 4)

        self.loadTrjBtn = QPushButton('Load traj')
        self.loadTrjBtn.clicked.connect(self.loadTrajectory)
        # self.loadTrjBtn.setEnabled(False)
        traj_tab_editLayout.addWidget(self.loadTrjBtn, 0, 5)

        traj_tab_editLayout.addWidget(QLabel('Line idx:'), 1, 0)
        self.refLineLe = QLineEdit('--')
        # self.refLineLe.setFixedWidth(50)
        self.refLineLe.setReadOnly(True)
        traj_tab_editLayout.addWidget(self.refLineLe, 1, 1, 1, 4)

        # self.delTrjBtn = QPushButton('Delete')
        # self.delTrjBtn.clicked.connect(self.delTrajectory)
        # self.delTrjBtn.setEnabled(False)
        # traj_tab_editLayout.addWidget(self.delTrjBtn, 1, 5)

        traj_tab_editLayout.addWidget(QLabel('User type:'), 2, 0)
        self.userTypeCb = QComboBox()
        self.userTypeCb.addItems(userTypeNames)
        self.userTypeCb.currentIndexChanged.connect(self.userTypeChanged)
        traj_tab_editLayout.addWidget(self.userTypeCb, 2, 1, 1, 4)

        self.groupSizeCb = QComboBox()
        self.groupSizeCb.addItems(['1', '2', '3', '4', '5', '6', '7', '8', '9'])
        self.groupSizeCb.setToolTip('Group size')
        self.groupSizeCb.currentIndexChanged.connect(self.groupSizeChanged)
        traj_tab_editLayout.addWidget(self.groupSizeCb, 2, 5)

        self.saveTrjsBtn = QPushButton('Save')
        self.saveTrjsBtn.clicked.connect(self.saveTrajectories)
        traj_tab_editLayout.addWidget(self.saveTrjsBtn, 3, 5)

        self.figure = plt.figure(tight_layout=True)
        self.canvas = FigureCanvas(self.figure)

        traj_tab_layout.addLayout(traj_tab_mdbLayout)
        traj_tab_layout.addLayout(traj_tab_gridLayout)
        traj_tab_layout.addWidget(self.canvas)
        traj_tab_layout.addLayout(traj_tab_editLayout)
        traj_tab_wdgt.setLayout(traj_tab_layout)
        self.toolbox.addItem(traj_tab_wdgt, 'TI Trajectory')

        # -------- Create a widget for window contents --------
        wid = QWidget(self)
        self.setCentralWidget(wid)

        # --------- Set widget to contain window contents -----
        wid.setLayout(layout)

    # ============== Buttons click functions ==============

    # ------------ TI Trajectory buttons ------------------
    def plotItems(self):
        if self.dbFilename == None:
            QMessageBox.information(self, 'Error!',
                'The iFramework database is not defined. First use open/create database tool.')
            return
        if self.mdbFileLedit.text() == '' or self.trjDbCombobx.currentText() == '':
            return

        self.cur.execute(
            'SELECT intrinsicCameraMatrixStr, distortionCoefficientsStr, frameRate FROM camera_types WHERE idx=?',
                         (self.cameraTypeIdx,))
        row = self.cur.fetchall()
        intrinsicCameraMatrixStr = row[0][0]
        distortionCoefficientsStr = row[0][1]
        self.intrinsicCameraMatrix = np.array(ast.literal_eval(intrinsicCameraMatrixStr))
        self.distortionCoefficients = np.array(ast.literal_eval(distortionCoefficientsStr))
        self.frameRate = row[0][2]

        mdbPath = Path(self.mdbFileLedit.text()).parent
        site_folder = mdbPath/self.siteNameCombobx.currentText()
        date_folder = site_folder/self.dateStr
        self.trjDBFile = date_folder/self.trjDbCombobx.currentText()
        self.homoFile = site_folder/self.homographyFilename

        if not self.trjDBFile.exists():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText('The trajectory database does not exist!')
            msg.exec_()
            self.figure.clear()
            self.canvas.draw()
            return

        trjDbName = self.trjDbCombobx.currentText()
        self.cur.execute('SELECT name, startTime, idx From video_sequences WHERE databaseFilename=?',
                         (self.dateStr + '/' + trjDbName,))
        row = self.cur.fetchall()
        video_name = Path(row[0][0])
        video_start_0 = datetime.datetime.strptime(row[0][1], '%Y-%m-%d %H:%M:%S.%f')
        self.video_start = video_start_0.replace(microsecond=0)
        self.trjDbIdx = row[0][2]

        video_file = site_folder/video_name
        if video_file.exists():
            self.parent().videoFile = str(video_file)
            self.parent().openVideoFile()
        else:
            QMessageBox.information(self, 'Error!', 'The corresponding video file does not exist!')
            return

        if not self.homoFile.exists():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText('The homography file does not exist!')
            msg.exec_()
            self.figure.clear()
            self.canvas.draw()
            return

        self.figure.clear()
        self.canvas.draw()

        self.ax = self.figure.add_subplot(111)

        self.traj_line = plotTrajectory(self.trjDBFile, self.intrinsicCameraMatrix, self.distortionCoefficients,
                                       self.homoFile, self.ax, session)
        for tl in self.traj_line.values():
            tl.append([-1, [], [], [], [], 1, None, []])
            #[userType, [screenLineIdxs], [crossingInstants], [speeds], [secs], groupSize, groupIdx, [rightTols]]
        self.noTrjLabel.setText('/' + str(len(self.traj_line) - 1))
        self.trjIdxLe.setText('-1')
        self.userTypeCb.setCurrentIndex(-1)
        self.refLineLe.setText('--')
        self.canvas.draw()

    def nextTrajectory(self):
        if self.traj_line == None:
            return
        traj_ids = [k for k in self.traj_line.keys()]
        if traj_ids == []:
            return
        q_line = session.query(Line)
        if q_line.all() == []:
            QMessageBox.information(self, 'Warning!', 'At least one screenline is required!')
            return

        current_idx = self.trjIdxLe.text()
        if current_idx == traj_ids[-1]:
            return
        if current_idx == '-1':
            for line in [tl[1] for tl in self.traj_line.values()]:
                line.set_visible(False)
            next_idx = traj_ids[0]
        else:
            current_line = self.traj_line[current_idx][1]
            current_line.set_visible(False)
            next_idx = traj_ids[traj_ids.index(current_idx) + 1]

        if not self.traj_line[next_idx][2][6] in [None, -1]:
            self.loadTrjBtn.setEnabled(False)
        else:
            self.loadTrjBtn.setEnabled(True)

        self.trjIdxLe.setText(next_idx)
        next_traj = self.traj_line[next_idx][0]
        next_line = self.traj_line[next_idx][1]
        next_line.set_visible(True)
        self.userTypeCb.setCurrentIndex(next_traj.userType)
        self.groupSizeCb.setCurrentIndex(next_traj.nObjects - 1)
        self.canvas.draw()

        if self.traj_line[next_idx][2][0] == -1:
            self.traj_line[next_idx][2][0] = next_traj.userType
            self.traj_line[next_idx][2][6] = -1
            homography = np.loadtxt(self.homoFile, delimiter=' ')
            for line in q_line.all():
                points = np.array([[line.points[0].x, line.points[1].x],
                                   [line.points[0].y, line.points[1].y]])
                prj_points = imageToWorldProject(points, self.intrinsicCameraMatrix, self.distortionCoefficients,
                                                 homography)
                p1 = moving.Point(prj_points[0][0], prj_points[1][0])
                p2 = moving.Point(prj_points[0][1], prj_points[1][1])

                instants_list, intersections, rightToLefts = next_traj.getInstantsCrossingLine(p1, p2, True)
                if len(instants_list) > 0:
                    secs = instants_list[0] / self.frameRate
                    instant = self.video_start + datetime.timedelta(seconds=round(secs))
                    speed = round(next_traj.getVelocityAtInstant(int(instants_list[0]))
                                  .norm2() * self.frameRate * 3.6, 1)  # km/h
                    rightToLeft = rightToLefts[0]

                    self.traj_line[next_idx][2][1].append(line)
                    self.traj_line[next_idx][2][2].append(instant)
                    self.traj_line[next_idx][2][3].append(speed)
                    self.traj_line[next_idx][2][4].append(secs)
                    self.traj_line[next_idx][2][7].append(rightToLeft)
                    # screenLine_Id = str(line.idx)
            if self.traj_line[next_idx][2][1] == []:
                secs = (next_traj.getLastInstant() / self.frameRate)
                # self.traj_line[next_idx][2][1].append('None')
                self.traj_line[next_idx][2][4].append(secs)

        self.parent().mediaPlayer.setPosition(round(self.traj_line[next_idx][2][4][0]*1000))
        if self.traj_line[next_idx][2][1] == []:
            self.refLineLe.setText('None')
        else:
            self.refLineLe.setText(str(self.traj_line[next_idx][2][1][0].idx))


        if self.traj_line[next_idx][2][6] == -1:
            self.trjIdxLe.setStyleSheet("QLineEdit { background: rgb(245, 215, 215); }")
        elif self.traj_line[next_idx][2][6] > -1:
            self.trjIdxLe.setStyleSheet("QLineEdit { background: rgb(215, 245, 215); }")


    def prevTrajectory(self):
        if self.traj_line == None:
            return
        traj_ids = [k for k in self.traj_line.keys()]
        if traj_ids == []:
            return
        current_idx = self.trjIdxLe.text()

        if current_idx == '-1':
            return
        if current_idx == '0':
            for line in [tl[1] for tl in self.traj_line.values()]:
                line.set_visible(True)
            self.trjIdxLe.setText('-1')
            self.trjIdxLe.setStyleSheet("QLineEdit { background: rgb(255, 255, 255); }")
            self.canvas.draw()
            return

        current_line = self.traj_line[current_idx][1]
        current_line.set_visible(False)

        prev_idx = traj_ids[traj_ids.index(current_idx) - 1]

        if not self.traj_line[prev_idx][2][6] in [None, -1]:
            self.loadTrjBtn.setEnabled(False)
        else:
            self.loadTrjBtn.setEnabled(True)

        self.trjIdxLe.setText(prev_idx)
        prev_traj = self.traj_line[prev_idx][0]
        prev_line = self.traj_line[prev_idx][1]
        prev_line.set_visible(True)
        self.userTypeCb.setCurrentIndex(prev_traj.userType)
        self.groupSizeCb.setCurrentIndex(self.traj_line[prev_idx][2][5] - 1)
        self.canvas.draw()

        homography = np.loadtxt(self.homoFile, delimiter=' ')
        q_line = session.query(Line)
        if q_line.all() != []:
            for line in q_line.all():
                points = np.array([[line.points[0].x, line.points[1].x],
                                   [line.points[0].y, line.points[1].y]])
                prj_points = imageToWorldProject(points, self.intrinsicCameraMatrix, self.distortionCoefficients,
                                                 homography)
                p1 = moving.Point(prj_points[0][0], prj_points[1][0])
                p2 = moving.Point(prj_points[0][1], prj_points[1][1])

                instants_list = prev_traj.getInstantsCrossingLane(p1, p2)
                if len(instants_list) > 0:
                    mil_secs = int((instants_list[0] / self.frameRate) * 1000)
                    self.refLineLe.setText(str(line.idx))
                    break
            if len(instants_list) == 0:
                mil_secs = int((prev_traj.getFirstInstant() / self.frameRate) * 1000)
                self.refLineLe.setText('None')
        else:
            mil_secs = int((prev_traj.getFirstInstant() / self.frameRate) * 1000)
            self.refLineLe.setText('None')

        self.parent().mediaPlayer.setPosition(mil_secs)

        if prev_idx != '-1':
            if self.traj_line[prev_idx][2][6] == -1:
                self.trjIdxLe.setStyleSheet("QLineEdit { background: rgb(245, 215, 215); }")
            elif self.traj_line[prev_idx][2][6] > -1:
                self.trjIdxLe.setStyleSheet("QLineEdit { background: rgb(215, 245, 215); }")

    def delTrajectory(self):
        delete_idx = int(self.trjIdxLe.text())
        delete_line = self.traj_line[delete_idx][1]
        if delete_idx == -1:
            return
        msg = QMessageBox()
        rep = msg.question(self, 'Delete trajectory',
                           'Are you sure to DELETE the current trajectory?', msg.Yes | msg.No)
        if rep == msg.No:
            return

        self.prevTrajectory()
        self.traj_line.pop(delete_idx)
        self.ax.lines.remove(delete_line)
        self.noTrjLabel.setText('/' + str(len(self.traj_line) - 1))

    def loadTrajectory(self):
        if self.mdbFileLedit.text() == '':
            return
        if self.traj_line == None:
            return

        # msg = QMessageBox()
        # rep = msg.question(self, 'Load trajectory',
        #                    'Are you sure to LOAD all trajectories to database?', msg.Yes | msg.No)
        # if rep == msg.No:
        #     return

        # streetUserObjects = []
        # no_users = 0
        # for trj_idx in range(len(self.traj_line)):
        self.loadTrjBtn.setEnabled(False)
        trj_idx = self.trjIdxLe.text()
        userType = self.traj_line[trj_idx][2][0]
        lines = self.traj_line[trj_idx][2][1]
        if userType != -1 and userType != 0:# and lines != []:
            self.user_newGroup_click()
            group_idx = int(self.group_idx_cmbBox.currentText())
            self.traj_line[trj_idx][2][6] = group_idx
            groupSize = self.traj_line[trj_idx][2][5]
            group = self.groups[group_idx][0]
            group.trajectoryDB = self.trjDbIdx
            group.trajectoryIdx = trj_idx
            for i in range(groupSize):
                self.user_newRecBtn_click()
                person_idx = int(self.group_list_wdgt.currentItem().text())
                self.mode_grpBox.setChecked(True)
                mode = self.groupPersons[person_idx][1]
                if userType != 2:
                    self.veh_grpBox.setChecked(True)
                    veh = self.groupPersons[person_idx][2]

                if userType == 1 or userType == 7:
                    mode.transport = 'cardriver'
                    veh.category = 'car'
                elif userType == 4 or userType == 3:
                    mode.transport = 'bike'
                    veh.category = 'bike'
                elif userType == 5:
                    mode.transport = 'cardriver'
                    veh.category = 'bus'
                elif userType == 6:
                    mode.transport = 'cardriver'
                    veh.category = 'truck'
                elif userType == 8:
                    mode.transport = 'scooter'
                    veh.category = 'scooter'
                elif userType == 9:
                    mode.transport = 'skating'
                    veh.category='skate'
            # if userType != 2:
            #     self.set_widget_values(self.mode_grpBox, mode)
            #     self.set_widget_values(self.veh_grpBox, veh)
            # self.group_list_wdgt.setCurrentRow(-1)
            # self.group_list_wdgt.setCurrentRow(0)
            self.user_saveBtn_click()

            for i in range(len(lines)):
                self.linepass_newRecBtn_click()
                linepass_idx = int(self.linepass_list_wdgt.currentItem().text())
                linepass = self.groups[group_idx][1][linepass_idx]
                line = lines[i]
                instant = self.traj_line[trj_idx][2][2][i]
                speed = self.traj_line[trj_idx][2][3][i]
                rightToleft = self.traj_line[trj_idx][2][7][i]

                linepass.line = line
                linepass.instant = instant
                linepass.speed = speed
                linepass.rightToLeft = rightToleft
            # self.set_widget_values(self.linepass_grpBox, linepass)
            # self.linepass_list_wdgt.setCurrentRow(-1)
            # self.linepass_list_wdgt.setCurrentRow(0)
            self.linepass_saveBtn_click()
        self.group_idx_cmbBox.setCurrentIndex(-1)
        self.group_idx_cmbBox.setCurrentText(str(group_idx))
        self.trjIdxLe.setStyleSheet("QLineEdit { background: rgb(215, 245, 215); }")


    def saveTrajectories(self):
        if self.mdbFileLedit.text() == '':
            return
        if self.traj_line == None:
            return
        trj_con = sqlite3.connect(self.trjDBFile)
        trj_cur = trj_con.cursor()
        for traj_idx in self.traj_line.keys():

            if self.traj_line[traj_idx][2][0] != -1:
                userType = self.traj_line[traj_idx][2][0]
                groupSize = self.traj_line[traj_idx][2][5]
                trj_cur.execute('UPDATE objects SET road_user_type=?, n_objects=? WHERE object_id=?',
                    (userType, groupSize, traj_idx))

            if self.traj_line[traj_idx][2][6] == -1:
                trj_cur.execute('DELETE FROM objects WHERE object_id=?', (traj_idx,))

                trj_cur.execute('SELECT trajectory_id FROM objects_features WHERE object_id=?', (traj_idx,))
                traj_id_rows = trj_cur.fetchall()
                trj_del_tuple_list = []
                for trj_id_row in traj_id_rows:
                    trj_del_tuple_list.append((trj_id_row[0],))

                trj_cur.executemany('DELETE FROM positions WHERE trajectory_id=?', trj_del_tuple_list)
                trj_cur.executemany('DELETE FROM velocities WHERE trajectory_id=?', trj_del_tuple_list)
                trj_cur.execute('DELETE FROM objects_features WHERE object_id=?', (traj_idx,))

        trj_con.commit()


    def userTypeChanged(self):
        current_idx = self.trjIdxLe.text()
        if current_idx == '-1':
            return
        user_indx = self.userTypeCb.currentIndex()
        current_traj = self.traj_line[current_idx][0]

        if user_indx != current_traj.userType:
            current_line = self.traj_line[current_idx][1]
            current_traj.setUserType(user_indx)
            self.traj_line[current_idx][2][0] = user_indx
            current_line.set_label(userTypeNames[user_indx])
            current_line.set_color(userTypeColors[user_indx])
            self.canvas.draw()

    def groupSizeChanged(self):
        current_idx = self.trjIdxLe.text()
        if current_idx == '-1':
            return
        self.traj_line[current_idx][2][5] = int(self.groupSizeCb.currentText())

    def openMdbFile(self):
        mdbFilename, _ = QFileDialog.getOpenFileName(self, "Open metadata file",
                                                     QDir.homePath(), "Sqlite files (*.sqlite)")
        if mdbFilename == '':
            return

        self.mdbFileLedit.setText(mdbFilename)

        con = sqlite3.connect(self.mdbFileLedit.text())
        self.cur = con.cursor()

        # Check if database is a metadata file
        self.cur.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='video_sequences' ''')
        if self.cur.fetchone()[0] == 0:
            QMessageBox.information(self, 'Error!',
                                    'The selected database is NOT a metadata file! Select a proper file.')
            self.mdbFileLedit.clear()
            return

        self.cur.execute('SELECT name FROM sites')
        sites = self.cur.fetchall()
        self.siteNameCombobx.clear()
        self.siteNameCombobx.addItems([s[0] for s in sites])
        # self.siteNameCombobx.setCurrentIndex(-1)

    def siteChanged(self):
        if self.siteNameCombobx.currentText() == '':
            return
        self.cur.execute('SELECT idx FROM sites WHERE name=?', (self.siteNameCombobx.currentText(),))
        siteIdx = self.cur.fetchall()[0][0]
        self.cur.execute('SELECT description FROM camera_views WHERE siteIdx=?', (siteIdx,))
        views = self.cur.fetchall()
        self.camViewCombobx.clear()
        self.camViewCombobx.addItems([v[0] for v in views])
        # self.camViewCombobx.setCurrentIndex(-1)

    def viewChanged(self):
        if self.camViewCombobx.currentText() == '':
            return
        self.cur.execute('SELECT idx FROM sites WHERE name=?', (self.siteNameCombobx.currentText(),))
        siteIdx = self.cur.fetchall()[0][0]
        self.cur.execute('SELECT idx, homographyFilename, cameraTypeIdx FROM camera_views WHERE description =? AND siteIdx=?',
                         (self.camViewCombobx.currentText(), siteIdx))
        row = self.cur.fetchall()
        viewIdx = row[0][0]
        self.homographyFilename = row[0][1]
        self.cameraTypeIdx = row[0][2]
        self.cur.execute('SELECT databaseFilename FROM video_sequences WHERE cameraViewIdx=?', (viewIdx,))
        trjDbs = self.cur.fetchall()
        self.trjDbCombobx.clear()
        if trjDbs == []:
            QMessageBox.information(self, 'Error', 'There is not any traj database name in metadata!')
            return
        else:
            self.trjDbCombobx.addItems([t[0].split('/')[-1] for t in trjDbs])
            # self.trjDbCombobx.setCurrentIndex(-1)
            self.dateStr = trjDbs[0][0].split('/')[0]


    #--------------- Road user buttons --------------------
    def user_newGroup_click(self):
        if self.dbFilename == None:
            QMessageBox.information(self, 'Error!',
                'The iFramework database is not defined. First use open/create database tool.')
            return
        self.user_newGroupButton.setEnabled(False)
        self.user_newRecButton.setEnabled(True)
        self.group_delFromListButton.setEnabled(False)
        self.group_delGroupButton.setEnabled(False)
        self.group_idx_cmbBox.setEnabled(False)

        btn_label = self.user_saveButton.text()
        self.user_saveButton.setText(btn_label.replace('Edit', 'Save'))
        self.user_saveButton.setIcon(QIcon('icons/save.png'))
        # self.groupPersons = {}
        # self.group_list_wdgt.clear()

        group = Group([])
        session.add(group)
        session.flush()

        self.groups[group.idx] = [group, {}, {}, {}]  #[group, {linePassings}, {ZoneCrossings}, {Activities}]
        self.group_idx_cmbBox.insertItem(0, str(group.idx))
        self.group_idx_cmbBox.setCurrentText(str(group.idx))

        # self.user_newRecBtn_click()

    def user_newRecBtn_click(self):
        self.person_grpBox.setEnabled(True)
        self.veh_grpBox.setEnabled(True)
        self.mode_grpBox.setEnabled(True)
        self.group_grpBox.setEnabled(True)

        self.user_saveButton.setEnabled(True)
        self.group_delFromListButton.setEnabled(True)

        group = self.groups[int(self.group_idx_cmbBox.currentText())][0]

        person = Person()
        GroupBelonging(person, group)
        session.add(person)
        session.flush()

        self.groupPersons[person.idx] = [person, None, None] # {person_idx: [person, mode, vehicle]}

        self.person_grpBox.layout().itemAtPosition(0, 1).widget().setText(str(person.idx))

        new_item = QListWidgetItem(str(person.idx))
        self.group_list_wdgt.addItem(new_item)
        self.group_list_wdgt.setCurrentItem(new_item)


    def user_saveBtn_click(self):
        if self.groupPersons == {}:
            QMessageBox.information(self, 'Error!', 'There is no person in the list!')
            return
        btn_label = self.user_saveButton.text()
        if btn_label.split(' ')[0] in ['Save', 'Update']:
            self.user_saveButton.setText(btn_label.replace(btn_label.split(' ')[0], 'Edit'))
            self.user_saveButton.setIcon(QIcon('icons/edit.png'))
            enable = False
        elif btn_label.split(' ')[0] == 'Edit':
            self.user_saveButton.setText(btn_label.replace('Edit', 'Update'))
            self.user_saveButton.setIcon(QIcon('icons/save.png'))
            enable = True

        # self.group_grpBox.setEnabled(enable)
        self.person_grpBox.setEnabled(enable)
        self.veh_grpBox.setEnabled(enable)
        self.mode_grpBox.setEnabled(enable)

        self.user_newGroupButton.setEnabled(not enable)
        self.user_newRecButton.setEnabled(enable)
        self.group_delFromListButton.setEnabled(enable)
        self.group_delGroupButton.setEnabled(not enable)
        self.group_idx_cmbBox.setEnabled(not enable)


        for inst_list in self.groupPersons.values():
            for inst in inst_list[1:3]:
                if inst != None:
                    session.add(inst)

        session.commit()

    def group_idx_changed(self):
        if self.group_idx_cmbBox.currentText() == '':
            return
        group_idx = int(self.group_idx_cmbBox.currentText())
        person_ids = [str(p.idx) for p in self.groups[group_idx][0].getPersons()]
        linepass_ids = [str(lp_id) for lp_id in self.groups[group_idx][1].keys()]
        zonepass_ids = [str(lp_id) for lp_id in self.groups[group_idx][2].keys()]
        act_ids = [str(lp_id) for lp_id in self.groups[group_idx][3].keys()]

        self.group_list_wdgt.clear()
        if len(person_ids) > 0:
            self.group_list_wdgt.addItems(person_ids)
            self.group_list_wdgt.setCurrentRow(0)

        self.linepass_list_wdgt.clear()
        if len(linepass_ids) > 0:
            self.linepass_list_wdgt.addItems(linepass_ids)
            self.linepass_list_wdgt.setCurrentRow(0)
            self.linepass_newRecButton.setEnabled(False)
            self.linepass_saveButton.setEnabled(True)
            btn_label = self.linepass_saveButton.text()
            self.linepass_saveButton.setText(btn_label.replace('Save', 'Edit'))
            self.linepass_saveButton.setIcon(QIcon('icons/edit.png'))
        else:
            self.linepass_newRecButton.setEnabled(True)
            self.linepass_saveButton.setEnabled(False)
            btn_label = self.linepass_saveButton.text()
            self.linepass_saveButton.setText(btn_label.replace('Edit', 'Save'))
            self.linepass_saveButton.setIcon(QIcon('icons/save.png'))

        self.zonepass_list_wdgt.clear()
        if len(zonepass_ids) > 0:
            self.zonepass_list_wdgt.addItems(zonepass_ids)
            self.zonepass_list_wdgt.setCurrentRow(0)
            self.zonepass_newRecButton.setEnabled(False)
            self.zonepass_saveButton.setEnabled(True)
            btn_label = self.zonepass_saveButton.text()
            self.zonepass_saveButton.setText(btn_label.replace('Save', 'Edit'))
            self.zonepass_saveButton.setIcon(QIcon('icons/edit.png'))
        else:
            self.zonepass_newRecButton.setEnabled(True)
            self.zonepass_saveButton.setEnabled(False)
            btn_label = self.zonepass_saveButton.text()
            self.zonepass_saveButton.setText(btn_label.replace('Edit', 'Save'))
            self.zonepass_saveButton.setIcon(QIcon('icons/save.png'))

        self.act_list_wdgt.clear()
        if len(act_ids) > 0:
            self.act_list_wdgt.addItems(act_ids)
            self.act_list_wdgt.setCurrentRow(0)
            self.act_newRecButton.setEnabled(False)
            self.act_saveButton.setEnabled(True)
            btn_label = self.act_saveButton.text()
            self.act_saveButton.setText(btn_label.replace('Save', 'Edit'))
            self.act_saveButton.setIcon(QIcon('icons/edit.png'))
        else:
            self.act_newRecButton.setEnabled(True)
            self.act_saveButton.setEnabled(False)
            btn_label = self.act_saveButton.text()
            self.act_saveButton.setText(btn_label.replace('Edit', 'Save'))
            self.act_saveButton.setIcon(QIcon('icons/save.png'))

    # ------------------- Group Buttons --------------
    def group_delFromList_click(self):
        if self.group_list_wdgt.count() == 1:
            self.group_delFromListButton.setEnabled(False)
            self.person_grpBox.setEnabled(False)

        current_item = self.group_list_wdgt.currentItem()
        person_idx = int(current_item.text())
        group_idx = int(self.group_idx_cmbBox.currentText())

        if self.veh_grpBox.isChecked():
            self.veh_grpBox.setChecked(False)
        if self.mode_grpBox.isChecked():
            self.mode_grpBox.setChecked(False)
        session.query(GroupBelonging).filter(GroupBelonging.personIdx == person_idx) \
            .filter(GroupBelonging.groupIdx == group_idx).delete()
        session.query(Person).filter(Person.idx == person_idx).delete()

        self.group_list_wdgt.takeItem(self.group_list_wdgt.row(current_item))
        self.groupPersons.pop(person_idx)

    def group_delGroupBtn_click(self):
        if self.act_list_wdgt.count() > 0:
            for i in range(self.act_list_wdgt.count()):
                self.act_delFromList_click()
            self.act_newRecButton.setEnabled(True)
            self.act_saveButton.setEnabled(False)
            btn_label = self.act_saveButton.text()
            self.act_saveButton.setText(btn_label.replace('Edit', 'Save'))
            self.act_saveButton.setIcon(QIcon('icons/save.png'))

        if self.zonepass_list_wdgt.count() > 0:
            for i in range(self.zonepass_list_wdgt.count()):
                self.zonepass_delFromList_click()
            self.zonepass_newRecButton.setEnabled(True)
            self.zonepass_saveButton.setEnabled(False)
            btn_label = self.zonepass_saveButton.text()
            self.zonepass_saveButton.setText(btn_label.replace('Edit', 'Save'))
            self.zonepass_saveButton.setIcon(QIcon('icons/save.png'))

        if self.linepass_list_wdgt.count() > 0:
            for i in range(self.linepass_list_wdgt.count()):
                self.linepass_delFromList_click()
            self.linepass_newRecButton.setEnabled(True)
            self.linepass_saveButton.setEnabled(False)
            btn_label = self.linepass_saveButton.text()
            self.linepass_saveButton.setText(btn_label.replace('Edit', 'Save'))
            self.linepass_saveButton.setIcon(QIcon('icons/save.png'))

        if self.group_list_wdgt.count() > 0:
            for i in range(self.group_list_wdgt.count()):
                self.group_delFromList_click()
            # self.user_newGroupButton.setEnabled(True)
            # self.user_newRecButton.setEnabled(False)
            # self.user_saveButton.setEnabled(False)
            # btn_label = self.user_saveButton.text()
            # self.user_saveButton.setText(btn_label.replace('Edit', 'Save'))
            # self.user_saveButton.setIcon(QIcon('icons/save.png'))

        if self.group_idx_cmbBox.count() > 0:
            group_idx = int(self.group_idx_cmbBox.currentText())
            group = session.query(Group).filter(Group.idx == group_idx).first()
            traj_Idx = group.trajectoryIdx
            group.delete()
            session.commit()
            self.groups.pop(group_idx)
            self.group_idx_cmbBox.removeItem(self.group_idx_cmbBox.currentIndex())
            if self.group_idx_cmbBox.count() == 0:
                self.group_delGroupButton.setEnabled(False)

        if self.traj_line != None and traj_Idx != None:
            self.traj_line[traj_Idx][2][6] = -1

    def rowChanged(self):
        current_item = self.sender().currentItem()
        if current_item == None:
            return

        if not self.sender() in [self.line_list_wdgt, self.zone_list_wdgt]:
            group_idx = int(self.group_idx_cmbBox.currentText())

        if self.sender() == self.group_list_wdgt:
            person_idx = int(current_item.text())
            person = self.groupPersons[person_idx][0]
            mode = self.groupPersons[person_idx][1]
            veh = self.groupPersons[person_idx][2]

            self.set_widget_values(self.person_grpBox, person)

            if mode == None:
                self.mode_grpBox.setChecked(False)
            else:
                self.set_widget_values(self.mode_grpBox, mode)

            if veh == None:
                self.veh_grpBox.setChecked(False)
            else:
                self.set_widget_values(self.veh_grpBox, veh)

        elif self.sender() == self.linepass_list_wdgt:
            linepass_idx = int(current_item.text())
            linepass = self.groups[group_idx][1][linepass_idx]
            self.set_widget_values(self.linepass_grpBox, linepass)

        elif self.sender() == self.zonepass_list_wdgt:
            zonepass_idx = int(current_item.text())
            zonepass = self.groups[group_idx][2][zonepass_idx]
            self.set_widget_values(self.zonepass_grpBox, zonepass)

        elif self.sender() == self.act_list_wdgt:
            act_idx = int(current_item.text())
            act = self.groups[group_idx][3][act_idx]
            self.set_widget_values(self.act_grpBox, act)

        elif self.sender() == self.line_list_wdgt:
            line_idx = int(self.line_list_wdgt.currentItem().text())
            line = session.query(Line).filter(Line.idx == line_idx).first()
            self.set_widget_values(self.line_grpBox, line)

        elif self.sender() == self.zone_list_wdgt:
            zone_idx = int(self.zone_list_wdgt.currentItem().text())
            zone = session.query(Zone).filter(Zone.idx == zone_idx).first()
            self.set_widget_values(self.zone_grpBox, zone)


    # @staticmethod
    def set_widget_values(self, grpBox, inst):
        self.IsChangedManually = False

        if grpBox.isCheckable():
            grpBox.setChecked(True)
        layout = grpBox.layout()
        for i in range(layout.rowCount()):
            attrib = layout.itemAtPosition(i, 0).widget().text()
            widg = layout.itemAtPosition(i, 1).widget()
            widg_val = getattr(inst, attrib)
            if isinstance(widg, QLineEdit):
                widg.setText(str(widg_val))
            elif isinstance(widg, QComboBox):
                if widg_val == None:
                    widg.setCurrentIndex(-1)
                else:
                    if isinstance(widg_val, eEnum):
                        widg.setCurrentText(str(widg_val.name))
                    else:
                        widg.setCurrentText(str(widg_val))
            elif isinstance(widg, QDateTimeEdit):
                if widg_val != None:
                    widg.setDateTime(QDateTime(widg_val))
        self.IsChangedManually = True


    # -------------- LinePassing buttons ------------------
    def linepass_newRecBtn_click(self):
        if len(self.groups.keys()) == 0 or self.group_list_wdgt.count() == 0:
            QMessageBox.information(self, 'Error!', 'No group or user is defined!')
            return

        btn_label = self.linepass_saveButton.text()
        self.linepass_saveButton.setText(btn_label.replace('Edit', 'Save'))
        self.linepass_saveButton.setIcon(QIcon('icons/save.png'))

        self.linepass_grpBox.setEnabled(True)
        self.linepass_saveButton.setEnabled(True)
        self.linepass_delFromListButton.setEnabled(True)

        group_idx = int(self.group_idx_cmbBox.currentText())
        group = self.groups[group_idx][0]

        linepass = LinePassing(line=None, instant=None, group=group)
        session.add(linepass)
        session.flush()

        self.groups[group_idx][1][linepass.idx] = linepass

        new_item = QListWidgetItem(str(linepass.idx))
        self.linepass_list_wdgt.addItem(new_item)
        self.linepass_list_wdgt.setCurrentItem(new_item)

        self.init_input_widgets(self.linepass_grpBox)

    def linepass_delFromList_click(self):
        if self.linepass_list_wdgt.count() == 1:
            self.linepass_delFromListButton.setEnabled(False)
            self.linepass_grpBox.setEnabled(False)

        current_item = self.linepass_list_wdgt.currentItem()
        linepass_idx = int(current_item.text())
        self.linepass_list_wdgt.takeItem(self.linepass_list_wdgt.row(current_item))
        del_obj = session.query(LinePassing).filter(LinePassing.idx == linepass_idx).first()
        session.delete(del_obj)
        group_idx = int(self.group_idx_cmbBox.currentText())
        self.groups[group_idx][1].pop(linepass_idx)

    def linepass_saveBtn_click(self):
        btn_label = self.linepass_saveButton.text()
        if btn_label.split(' ')[0] in ['Save', 'Update']:
            self.linepass_saveButton.setText(btn_label.replace(btn_label.split(' ')[0], 'Edit'))
            self.linepass_saveButton.setIcon(QIcon('icons/edit.png'))
            enable = False
        elif btn_label.split(' ')[0] == 'Edit':
            self.linepass_saveButton.setText(btn_label.replace('Edit', 'Update'))
            self.linepass_saveButton.setIcon(QIcon('icons/save.png'))
            enable = True

        self.linepass_grpBox.setEnabled(enable)
        self.linepass_delFromListButton.setEnabled(enable)
        self.linepass_newRecButton.setEnabled(enable)

        session.commit()


    # -------------- ZoneCrossing buttons ------------------
    def zonepass_newRecBtn_click(self):
        if len(self.groups.keys()) == 0 or self.group_list_wdgt.count() == 0:
            QMessageBox.information(self, 'Error!', 'No group or user is defined!')
            return

        btn_label = self.zonepass_saveButton.text()
        self.zonepass_saveButton.setText(btn_label.replace('Edit', 'Save'))
        self.zonepass_saveButton.setIcon(QIcon('icons/save.png'))

        self.zonepass_grpBox.setEnabled(True)
        self.zonepass_saveButton.setEnabled(True)
        self.zonepass_delFromListButton.setEnabled(True)

        group_idx = int(self.group_idx_cmbBox.currentText())
        group = self.groups[group_idx][0]

        zonepass = ZoneCrossing(zone=None, instant=None, entering=None, group=group)
        session.add(zonepass)
        session.flush()

        self.groups[group_idx][2][zonepass.idx] = zonepass

        new_item = QListWidgetItem(str(zonepass.idx))
        self.zonepass_list_wdgt.addItem(new_item)
        self.zonepass_list_wdgt.setCurrentItem(new_item)

        self.init_input_widgets(self.zonepass_grpBox)

    def zonepass_delFromList_click(self):
        if self.zonepass_list_wdgt.count() == 1:
            self.act_delFromListButton.setEnabled(False)
            self.zonepass_grpBox.setEnabled(False)

        current_item = self.zonepass_list_wdgt.currentItem()
        zonepass_idx = int(current_item.text())
        self.zonepass_list_wdgt.takeItem(self.zonepass_list_wdgt.row(current_item))
        del_obj = session.query(ZoneCrossing).filter(ZoneCrossing.idx == zonepass_idx).first()
        session.delete(del_obj)
        group_idx = int(self.group_idx_cmbBox.currentText())
        self.groups[group_idx][2].pop(zonepass_idx)

    def zonepass_saveBtn_click(self):
        btn_label = self.zonepass_saveButton.text()
        if btn_label.split(' ')[0] in ['Save', 'Update']:
            self.zonepass_saveButton.setText(btn_label.replace(btn_label.split(' ')[0], 'Edit'))
            self.zonepass_saveButton.setIcon(QIcon('icons/edit.png'))
            enable = False
        elif btn_label.split(' ')[0] == 'Edit':
            self.zonepass_saveButton.setText(btn_label.replace('Edit', 'Update'))
            self.zonepass_saveButton.setIcon(QIcon('icons/save.png'))
            enable = True

        self.zonepass_grpBox.setEnabled(enable)
        self.zonepass_delFromListButton.setEnabled(enable)
        self.zonepass_newRecButton.setEnabled(enable)

        session.commit()

    # -------------- Activity buttons ------------------
    def act_newRecBtn_click(self):
        if len(self.groups.keys()) == 0 or self.group_list_wdgt.count() == 0:
            QMessageBox.information(self, 'Error!', 'No group or user is defined!')
            return

        btn_label = self.act_saveButton.text()
        self.act_saveButton.setText(btn_label.replace('Edit', 'Save'))
        self.act_saveButton.setIcon(QIcon('icons/save.png'))

        self.act_grpBox.setEnabled(True)
        self.act_saveButton.setEnabled(True)
        self.act_delFromListButton.setEnabled(True)

        group_idx = int(self.group_idx_cmbBox.currentText())
        group = self.groups[group_idx][0]

        act = Activity(startTime=None, endTime=None, zone=None, group=group)
        session.add(act)
        session.flush()

        self.groups[group_idx][3][act.idx] = act

        new_item = QListWidgetItem(str(act.idx))
        self.act_list_wdgt.addItem(new_item)
        self.act_list_wdgt.setCurrentItem(new_item)

        self.init_input_widgets(self.act_grpBox)

    def act_delFromList_click(self):
        if self.act_list_wdgt.count() == 1:
            self.act_delFromListButton.setEnabled(False)
            self.act_grpBox.setEnabled(False)

        current_item = self.act_list_wdgt.currentItem()
        act_idx = int(current_item.text())
        self.act_list_wdgt.takeItem(self.act_list_wdgt.row(current_item))
        del_obj = session.query(Activity).filter(Activity.idx == act_idx).first()
        session.delete(del_obj)
        group_idx = int(self.group_idx_cmbBox.currentText())
        self.groups[group_idx][3].pop(act_idx)

    def act_saveBtn_click(self):
        btn_label = self.act_saveButton.text()
        if btn_label.split(' ')[0] in ['Save', 'Update']:
            self.act_saveButton.setText(btn_label.replace(btn_label.split(' ')[0], 'Edit'))
            self.act_saveButton.setIcon(QIcon('icons/edit.png'))
            enable = False
        elif btn_label.split(' ')[0] == 'Edit':
            self.act_saveButton.setText(btn_label.replace('Edit', 'Update'))
            self.act_saveButton.setIcon(QIcon('icons/save.png'))
            enable = True

        self.act_grpBox.setEnabled(enable)
        self.act_delFromListButton.setEnabled(enable)
        self.act_newRecButton.setEnabled(enable)

        session.commit()

    # -------------- Line buttons ------------------
    def line_newRecBtn_click(self):
        if session == None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText('The database file is not defined.')
            msg.setInformativeText('Use Creat/Open iFramework database tool')
            msg.setIcon(QMessageBox.Critical)
            msg.exec_()
            return

        if not self.sender().isChecked():
            self.parent().gView.unsetCursor()
            return

        cursor = QCursor(Qt.CrossCursor)
        self.parent().gView.setCursor(cursor)
        self.parent().raise_()
        self.parent().activateWindow()

        btn_label = self.line_saveButton.text()
        self.line_saveButton.setText(btn_label.replace('Edit', 'Save'))
        self.line_saveButton.setIcon(QIcon('icons/save.png'))

        self.line_grpBox.setEnabled(True)
        self.line_saveButton.setEnabled(True)
        self.line_delFromListButton.setEnabled(True)

    def line_delFromList_click(self):
        if self.line_list_wdgt.count() == 1:
            self.line_delFromListButton.setEnabled(False)
            self.line_grpBox.setEnabled(False)

        current_item = self.line_list_wdgt.currentItem()
        line_idx = int(current_item.text())
        self.line_list_wdgt.takeItem(self.line_list_wdgt.row(current_item))
        del_line = session.query(Line).filter(Line.idx == line_idx).first()
        del_points = del_line.points
        session.delete(del_line)
        for del_point in del_points:
            session.query(Point).filter(Point.idx == del_point.idx).delete()

        session.commit()

        for gitem in self.parent().gView.scene().items():
            if isinstance(gitem, QGraphicsItemGroup):
                if gitem.toolTip().split(':')[0] == 'L' + current_item.text():
                    self.parent().gView.scene().removeItem(gitem)

    def line_saveBtn_click(self):
        btn_label = self.line_saveButton.text()
        if btn_label.split(' ')[0] in ['Save', 'Update']:
            self.line_saveButton.setText(btn_label.replace(btn_label.split(' ')[0], 'Edit'))
            self.line_saveButton.setIcon(QIcon('icons/edit.png'))
            enable = False
        elif btn_label.split(' ')[0] == 'Edit':
            self.line_saveButton.setText(btn_label.replace('Edit', 'Update'))
            self.line_saveButton.setIcon(QIcon('icons/save.png'))
            enable = True

        self.line_grpBox.setEnabled(enable)
        self.line_delFromListButton.setEnabled(enable)
        self.line_newRecButton.setEnabled(enable)

        session.commit()

    # -------------- Zone buttons ------------------
    def zone_newRecBtn_click(self):
        if session == None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText('The database file is not defined.')
            msg.setInformativeText('Use Creat/Open iFramework database tool')
            msg.setIcon(QMessageBox.Critical)
            msg.exec_()
            return

        if not self.sender().isChecked():
            self.parent().gView.unsetCursor()
            return

        cursor = QCursor(Qt.CrossCursor)
        self.parent().gView.setCursor(cursor)
        self.parent().raise_()
        self.parent().activateWindow()

        btn_label = self.zone_saveButton.text()
        self.zone_saveButton.setText(btn_label.replace('Edit', 'Save'))
        self.zone_saveButton.setIcon(QIcon('icons/save.png'))

        self.zone_grpBox.setEnabled(True)
        self.zone_saveButton.setEnabled(True)
        self.zone_delFromListButton.setEnabled(True)

    def zone_delFromList_click(self):
        if self.zone_list_wdgt.count() == 1:
            self.zone_delFromListButton.setEnabled(False)
            self.zone_grpBox.setEnabled(False)

        current_item = self.zone_list_wdgt.currentItem()
        zone_idx = int(current_item.text())
        self.zone_list_wdgt.takeItem(self.zone_list_wdgt.row(current_item))
        del_zone = session.query(Zone).filter(Zone.idx == zone_idx).first()
        del_points = del_zone.points
        session.delete(del_zone)
        for del_point in del_points:
            session.query(Point).filter(Point.idx == del_point.idx).delete()

        session.commit()

        for gitem in self.parent().gView.scene().items():
            if isinstance(gitem, QGraphicsItemGroup):
                if gitem.toolTip().split(':')[0] == 'Z' + current_item.text():
                    self.parent().gView.scene().removeItem(gitem)

    def zone_saveBtn_click(self):
        btn_label = self.zone_saveButton.text()
        if btn_label.split(' ')[0] in ['Save', 'Update']:
            self.zone_saveButton.setText(btn_label.replace(btn_label.split(' ')[0], 'Edit'))
            self.zone_saveButton.setIcon(QIcon('icons/edit.png'))
            enable = False
        elif btn_label.split(' ')[0] == 'Edit':
            self.zone_saveButton.setText(btn_label.replace('Edit', 'Update'))
            self.zone_saveButton.setIcon(QIcon('icons/save.png'))
            enable = True

        self.zone_grpBox.setEnabled(enable)
        self.zone_delFromListButton.setEnabled(enable)
        self.zone_newRecButton.setEnabled(enable)

        session.commit()

    # =====================================================
    def init_input_widgets(self, grpBox):
        class_ = getattr(iframework, grpBox.title())
        grid_lyt = grpBox.layout()
        grid_labels = [grid_lyt.itemAtPosition(i, 0).widget() for i in range(grid_lyt.rowCount())]

        i = 0
        for label in grid_labels:
            input_wdgt = grid_lyt.itemAtPosition(i, 1).widget()
            if isinstance(input_wdgt, QComboBox):
                if len(getattr(class_, label.text()).foreign_keys) > 0:
                    fk_set = getattr(class_, label.text()).foreign_keys
                    fk = next(iter(fk_set))
                    fk_items = [input_wdgt.itemText(i) for i in range(input_wdgt.count())]

                    items = [i[0] for i in session.query(fk.column).all()]
                    items.sort(reverse=True)
                    items = [str(i) for i in items]

                    # if fk_items != items:
                    input_wdgt.clear()
                    input_wdgt.addItems(items)
                    input_wdgt.setCurrentIndex(-1)

            elif isinstance(input_wdgt, QDateTimeEdit):
                input_wdgt.setDateTime(datetime.datetime(2000,1,1))
                if self.parent() == None or self.parent().videoCurrentDatetime == None:
                    input_wdgt.setDateTime(QDateTime.currentDateTime())
                else:
                    input_wdgt.setDateTime(QDateTime(self.parent().videoCurrentDatetime))
            i = i + 1


    def getRelatedTable(self, grpBx):
        grid_wdgt = grpBx.layout().itemAt(1).widget()
        class_ = getattr(iframework, grpBx.title())

        grid_lyt = grid_wdgt.layout()
        grid_labels = [grid_lyt.itemAtPosition(i, 0).widget() for i in range(grid_lyt.rowCount())]

        relatedTables = []
        i = 0
        for label in grid_labels:
            input_wdgt = grid_lyt.itemAtPosition(i, 1).widget()
            if isinstance(input_wdgt, QComboBox):
                if len(getattr(class_, label.text()).foreign_keys) > 0:
                    fk_set = getattr(class_, label.text()).foreign_keys
                    fk = next(iter(fk_set))
                    fkTableName = fk.column.table.name
                    fkColumnName = label.text()
                    for indx in range(self.toolbox.count()):
                        tabLayout = self.toolbox.widget(indx).layout()
                        for itmIndx in range(tabLayout.count()):
                            groupBox = tabLayout.itemAt(itmIndx).widget()
                            if groupBox.title().lower() == fkTableName:
                                relatedTables.append([fkColumnName, groupBox])
            i = i + 1

        return relatedTables

    @staticmethod
    def toBool(s):
        if s == 'True':
            return True
        else:
            return False

    @staticmethod
    def getTableColumns(TableCls):
        pk_list = [key.name for key in inspect(TableCls).primary_key]
        columnsList = []
        for column in TableCls.__table__.columns:
            if isinstance(column.type, Enum):
                e = column.type.enums
            elif isinstance(column.type, Boolean):
                e = ['True', 'False']
            else:
                e = None

            columnsList.append({'name':column.name,
                                'enum': e,
                                'default': column.default.arg if column.default != None else None,
                                'is_primary_key': True if column.name in pk_list else False,
                                'is_foreign_key': False if len(column.foreign_keys) == 0 else True,
                                'is_datetime': True if isinstance(column.type, DateTime) else False})
        return columnsList


    def generateWidgets(self, tableClass, fieldConst, checkable):
        groupBox = QGroupBox(tableClass.__name__)
        if checkable:
            groupBox.setCheckable(True)
            groupBox.setChecked(False)
            groupBox.toggled.connect(self.grpBoxToggled)
        groupBox_layout = QGridLayout()

        # gridLayout = QGridLayout()
        # gridWidget = QWidget()
        # gridWidget.setEnabled(False)

        i = 0
        for column in self.getTableColumns(tableClass):
            if (fieldConst == 'NoPr' or fieldConst == 'NoPrFo') and column['is_primary_key']:
                continue
            elif (fieldConst == 'NoFo' or fieldConst == 'NoPrFo') and column['is_foreign_key'] and \
                not column['name'] in ['pointIdx', 'lineIdx', 'zoneIdx']:
                continue
            label = QLabel(column['name'])
            groupBox_layout.addWidget(label, i, 0)

            if column['enum'] != None:
                wdgt = QComboBox()
                wdgt.addItems(column['enum'])
                wdgt.setCurrentIndex(-1)
                wdgt.currentTextChanged.connect(self.wdgtValueChanged)
            elif column['is_foreign_key']:
                wdgt = QComboBox()
                wdgt.currentTextChanged.connect(self.wdgtValueChanged)
            elif column['is_datetime']:
                wdgt = QDateTimeEdit()
                wdgt.setDisplayFormat('yyyy-MM-dd hh:mm:ss')
                wdgt.dateTimeChanged.connect(self.wdgtValueChanged)
                # wdgt.setCalendarPopup(True)
            else:
                wdgt = QLineEdit()
                if column['is_primary_key']:
                    wdgt.setReadOnly(True) #.setEnabled(False)
                else:
                    wdgt.editingFinished.connect(self.wdgtValueChanged)

            groupBox_layout.addWidget(wdgt, i, 1)
            i += 1

        # gridWidget.setLayout(gridLayout)

        # groupBox_layout.addWidget(gridWidget)

        # groupBox.setAlignment(Qt.AlignHCenter)
        groupBox.setLayout(groupBox_layout)

        groupBox.setEnabled(False)
        return  groupBox

    def wdgtValueChanged(self):
        if self.IsChangedManually == False:
            return
        grpBox = self.sender().parentWidget()
        layout = grpBox.layout()
        wdgt_idx = layout.indexOf(self.sender())
        attrib = layout.itemAt(wdgt_idx - 1).widget().text()

        if grpBox.title() == 'Person':
            person_idx = int(self.group_list_wdgt.currentItem().text())
            inst = self.groupPersons[person_idx][0]

        elif grpBox.title() == 'Mode':
            person_idx = int(self.group_list_wdgt.currentItem().text())
            inst = self.groupPersons[person_idx][1]

        elif grpBox.title() == 'Vehicle':
            person_idx = int(self.group_list_wdgt.currentItem().text())
            inst = self.groupPersons[person_idx][2]

        elif grpBox.title() == 'LinePassing':
            group_idx = int(self.group_idx_cmbBox.currentText())
            if self.linepass_list_wdgt.count() > 0:
                linepass_idx = int(self.linepass_list_wdgt.currentItem().text())
                inst = self.groups[group_idx][1][linepass_idx]
            else:
                return

        elif grpBox.title() == 'ZoneCrossing':
            group_idx = int(self.group_idx_cmbBox.currentText())
            if self.zonepass_list_wdgt.count() > 0:
                zonepass_idx = int(self.zonepass_list_wdgt.currentItem().text())
                inst = self.groups[group_idx][2][zonepass_idx]
            else:
                return

        elif grpBox.title() == 'Activity':
            group_idx = int(self.group_idx_cmbBox.currentText())
            if self.act_list_wdgt.count() > 0:
                act_idx = int(self.act_list_wdgt.currentItem().text())
                inst = self.groups[group_idx][3][act_idx]
            else:
                return

        elif grpBox.title() == 'Line':
            if self.line_list_wdgt.count() > 0:
                line_idx = int(self.line_list_wdgt.currentItem().text())
                inst = session.query(Line).filter(Line.idx == line_idx).first()
            else:
                return

        elif grpBox.title() == 'Zone':
            if self.zone_list_wdgt.count() > 0:
                zone_idx = int(self.zone_list_wdgt.currentItem().text())
                inst = session.query(Zone).filter(Zone.idx == zone_idx).first()
            else:
                return

        else:
            return

        if isinstance(self.sender(), QLineEdit):
            setattr(inst, attrib, self.sender().text())
        elif isinstance(self.sender(), QComboBox):
            new_val = self.sender().currentText()
            if new_val in ['True', 'False']:
                new_val = self.toBool(new_val)
            elif self.sender().currentIndex() == -1:
                new_val = None
            setattr(inst, attrib, new_val)
        elif isinstance(self.sender(), QDateTimeEdit):
            setattr(inst, attrib, self.sender().dateTime().toPyDateTime())

    def grpBoxToggled(self, on):
        title = self.sender().title()
        person_idx = int(self.group_list_wdgt.currentItem().text())
        person0 = self.groupPersons[person_idx][0]
        mode0 = self.groupPersons[person_idx][1]
        veh0 = self.groupPersons[person_idx][2]
        if title == 'Mode':
            if mode0 == None and on:
                person = self.groupPersons[person_idx][0]
                mode = Mode('walking', person)
                self.groupPersons[person_idx][1] = mode
                self.init_input_widgets(self.mode_grpBox)
                self.set_widget_values(self.mode_grpBox, mode)
            elif not on:
                self.veh_grpBox.setChecked(False)
                mode0_obj = session.query(Mode).filter(Mode.personIdx == person_idx).all()
                if len(mode0_obj) > 0:
                    session.delete(mode0_obj[0])
                    session.commit()
                self.groupPersons[person_idx][1] = None

        if title == 'Vehicle':
            if mode0 != None and veh0 == None and on:
                veh = Vehicle('car')
                mode0.vehicle = veh
                self.groupPersons[person_idx][2] = veh
                self.set_widget_values(self.veh_grpBox, veh)
            elif mode0 == None and on:
                QMessageBox.information(self, 'Error', 'The mode is not specified!')
                self.sender().setChecked(False)
                return
            elif mode0 != None and not on:
                if mode0.vehicle != None:
                    veh0_idx = mode0.vehicle.idx
                    mode0.vehicle = None
                    session.query(Vehicle).filter(Vehicle.idx == veh0_idx).delete()
                    session.commit()
                self.groupPersons[person_idx][2] = None

    def newRecord(self, grpBx, fieldVals = {}):
        newRecBtn = grpBx.layout().itemAt(0).layout().itemAt(0).widget()
        newObjBtn = grpBx.layout().itemAt(0).layout().itemAt(1).widget()
        saveBtn = grpBx.layout().itemAt(2).layout().itemAt(2).widget()
        editBtn = grpBx.layout().itemAt(2).layout().itemAt(1).widget()
        grid_wdgt = grpBx.layout().itemAt(1).widget()

        if self.sender() == newRecBtn:
            self.sender().setEnabled(False)
        grid_wdgt.setEnabled(True)
        saveBtn.setEnabled(True)
        editBtn.setEnabled(False)

        class_ = getattr(iframework, grpBx.title())
        instance = class_()
        session.add(instance)
        session.flush()

        pk_list = [key.name for key in inspect(class_).primary_key]
        grid_lyt = grid_wdgt.layout()
        grid_labels = [grid_lyt.itemAtPosition(i, 0).widget() for i in range(grid_lyt.rowCount())]

        i = 0
        for label in grid_labels:
            input_wdgt = grid_lyt.itemAtPosition(i, 1).widget()
            if  isinstance(input_wdgt, QLineEdit) and label.text() in pk_list:
                pk_val = str(getattr(instance, label.text()))
                input_wdgt.setText(pk_val)
            elif isinstance(input_wdgt, QComboBox):
                if len(getattr(class_, label.text()).foreign_keys) > 0:
                    fk_set = getattr(class_, label.text()).foreign_keys
                    fk = next(iter(fk_set))
                    fk_items = [input_wdgt.itemText(i) for i in range(input_wdgt.count())]

                    items = [i[0] for i in session.query(fk.column).all()]
                    items.sort(reverse=True)
                    items = [str(i) for i in items]

                    if fk_items != items:
                        input_wdgt.clear()
                        input_wdgt.addItems(items)

                        if len(fieldVals.keys()) > 0:
                            fldName = next(iter(fieldVals.keys()))
                            if fldName == label.text():
                                input_wdgt.setCurrentText(str(fieldVals[fldName]))
            elif  isinstance(input_wdgt, QDateTimeEdit):
                if self.parent() == None or self.parent().videoCurrentDatetime == None:
                    input_wdgt.setDateTime(QDateTime.currentDateTime())
                else:
                    input_wdgt.setDateTime(QDateTime(self.parent().videoCurrentDatetime))
            i = i + 1

        msg = 'New: {}({})'.format(grpBx.title(), pk_val)
        self.statusBar.showMessage(msg, 120000)

        return pk_val
        # grid_wdgt.repaint()


        # session.commit()

        # rels = inspect(class_).relationships
        # clss = [rel.mapper.class_ for rel in rels]
        # print(clss)

        # fk_set = inspect(class_).columns.personId.foreign_keys
        # fk = next(iter(fk_set))
        # print(fk.column)
        # print([i[0] for i in session.query(fk.column).all()])

    def newObject(self, grpBx):
        grid_wdgt = grpBx.layout().itemAt(1).widget()
        grid_lyt = grid_wdgt.layout()
        grid_labels = [grid_lyt.itemAtPosition(i, 0).widget() for i in range(grid_lyt.rowCount())]
        i = 0
        for label in grid_labels:
            input_wdgt = grid_lyt.itemAtPosition(i, 1).widget()
            if isinstance(input_wdgt, QDateTimeEdit):
                input_wdgt_val = input_wdgt.dateTime().toPyDateTime()
                if self.parent() != None:
                    if self.parent().videoCurrentDatetime == input_wdgt_val:
                        msg = QMessageBox()
                        rep = msg.question(self, 'Duplicate object',
                                           'Are you sure to duplicate the current object?', msg.Yes | msg.No)
                        if rep == msg.No:
                            return
                        elif rep == msg.Yes:
                            break
            i =+ 1

        relatedTables = []
        grpBoxToCheck = grpBx
        msg = 'New: '

        while True:
            relTable = self.getRelatedTable(grpBoxToCheck)
            if relTable != []:
                relatedTables.insert(0,[grpBoxToCheck, relTable[0][0]])
                grpBoxToCheck = relTable[0][1]
            else:
                relatedTables.insert(0, [grpBoxToCheck, None])
                break

        for tbl in relatedTables:
            if tbl[1] == None:
                pk_id = self.newRecord(tbl[0])
            else:
                pk_id = self.newRecord(tbl[0], {tbl[1]:pk_id})
            self.saveRecord(tbl[0])
            msg = msg + '{}({}), '.format(tbl[0].title(), pk_id)

        self.statusBar.showMessage(msg[:-2], 120000)


    def saveRecord(self, grpBx):
        newBtn = grpBx.layout().itemAt(0).layout().itemAt(0).widget()
        grid_wdgt = grpBx.layout().itemAt(1).widget()
        delBtn = grpBx.layout().itemAt(2).layout().itemAt(0).widget()
        editBtn = grpBx.layout().itemAt(2).layout().itemAt(1).widget()
        saveBtn = grpBx.layout().itemAt(2).layout().itemAt(2).widget()

        newBtn.setEnabled(True)
        editBtn.setEnabled(True)
        delBtn.setEnabled(True)
        grid_wdgt.setEnabled(False)
        saveBtn.setEnabled(False)
        if saveBtn.text() == 'Update':
            saveBtn.setText('Save')

        class_ = getattr(iframework, grpBx.title())
        pk_list = [key.name for key in inspect(class_).primary_key]
        grid_lyt = grid_wdgt.layout()
        grid_labels = [grid_lyt.itemAtPosition(i, 0).widget() for i in range(grid_lyt.rowCount())]

        i = 0
        for label in grid_labels:
            input_wdgt = grid_lyt.itemAtPosition(i, 1).widget()
            if label.text() in pk_list:
                pk_name = label.text()
                pk_val = input_wdgt.text()
                break
            i = i + 1

        instance = session.query(class_).filter(getattr(class_, pk_name) == pk_val).first()
        # obs_instance = session.query(Study_site).first()
        # if obs_instance == None:
        #     msg = QMessageBox()
        #     msg.setIcon(QMessageBox.Critical)
        #     msg.setText('The observatoin start time is not set!')
        #     msg.exec_()
        #     return
        # current_obs_end = obs_instance.obsEnd

        i = 0
        for label in grid_labels:
            input_wdgt = grid_lyt.itemAtPosition(i, 1).widget()
            if isinstance(input_wdgt, QLineEdit):
                if  label.text() == pk_name:
                    i = i + 1
                    continue
                else:
                    input_wdgt_val = input_wdgt.text()
            elif isinstance(input_wdgt, QComboBox):
                if input_wdgt.currentText() == '':
                    i = i + 1
                    continue
                if input_wdgt.currentText() == 'True':
                    input_wdgt_val = True
                elif input_wdgt.currentText() == 'False':
                    input_wdgt_val = False
                else:
                    input_wdgt_val = input_wdgt.currentText()
            elif isinstance(input_wdgt, QDateTimeEdit):
                input_wdgt_val = input_wdgt.dateTime().toPyDateTime()
                input_wdgt_val = input_wdgt_val.replace(microsecond=0)
                if current_obs_end != None:
                    if current_obs_end < input_wdgt_val:
                        obs_instance.obsEnd = input_wdgt_val
                else:
                    obs_instance.obsEnd = input_wdgt_val

            setattr(instance, label.text(), input_wdgt_val)
            i = i + 1

        session.commit()

        self.statusBar.showMessage('Save/Update is done!', 10000)
        # grid_wdgt.repaint()

    def editObject(self, grpBx, grid_wdgt, newBtn, addBtn):
        grid_wdgt.setEnabled(True)
        addBtn.setEnabled(True)
        addBtn.setText('Update')
        self.sender().setEnabled(False)

    def deleteObject(self, grpBx, grid_wdgt, newBtn, editBtn):
        msg = QMessageBox()
        rep = msg.question(self, 'Delete', 'Are you sure to delete the record?', msg.Yes | msg.No)

        if rep == msg.No:
            return

        self.sender().setEnabled(False)
        editBtn.setEnabled(False)
        newBtn.setEnabled(True)

        class_ = getattr(iframework, grpBx.title())
        pk_list = [key.name for key in inspect(class_).primary_key]
        grid_lyt = grid_wdgt.layout()
        grid_labels = [grid_lyt.itemAtPosition(i, 0).widget() for i in range(grid_lyt.rowCount())]

        i = 0
        for label in grid_labels:
            input_wdgt = grid_lyt.itemAtPosition(i, 1).widget()
            if label.text() in pk_list and isinstance(input_wdgt, QLineEdit):
                pk_name = label.text()
                pk_val = input_wdgt.text()
            if isinstance(input_wdgt, QLineEdit):
                input_wdgt.setText('')
            elif isinstance(input_wdgt, QComboBox):
                input_wdgt.setCurrentIndex(-1)
            i = i + 1

        session.query(class_).filter(getattr(class_, pk_name) == pk_val).delete()
        session.commit()

        self.statusBar.showMessage('Record deleted!', 5000)

    def newTab(self, classList, fieldConstList, checkableList, tabName, iconFilename):
        wdgt = QWidget()
        layout = QVBoxLayout()

        for className, fieldConst, checkable in zip(classList, fieldConstList, checkableList):
            layout.addWidget(self.generateWidgets(className, fieldConst, checkable))
        wdgt.setLayout(layout)
        self.toolbox.addItem(wdgt, QIcon(iconFilename), tabName)


    def opendbFile(self):
        global session
        if self.sender() == self.openAction:
            self.dbFilename, _ = QFileDialog.getSaveFileName(self, "Open database file",
                                                  QDir.homePath(), "Sqlite files (*.sqlite)")
            if self.dbFilename != '':
                for item in self.parent().gScene.items()[:-1]:
                    self.parent().gScene.removeItem(item)
                # self.parent().loadGraphics()

        if self.dbFilename != '':
            if self.parent() != None:
                self.setWindowTitle('{} - {}'.format(os.path.basename(self.dbFilename),
                                                     os.path.basename(self.parent().projectFile)))
            else:
                self.setWindowTitle(os.path.basename(self.dbFilename))

            # self.dbFilename = fileName

            session = createDatabase(self.dbFilename)
            if session is None:
                session = connectDatabase(self.dbFilename)

    def tempHist(self):
        if session == None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText('The database file is not defined.')
            msg.exec_()
            return
        tempHistWin = TempHistWindow(self)
        # tempHistWin.setModal(True)
        # tempHistWin.setAttribute(Qt.WA_DeleteOnClose)

        tempHistWin.exec_()


    def stackedHist(self):
        if session == None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText('The database file is not defined.')
            msg.exec_()
            return
        stackHistWin = StackHistWindow(self)
        # tempHistWin.setModal(True)
        # tempHistWin.setAttribute(Qt.WA_DeleteOnClose)

        stackHistWin.exec_()

    def speedPlot(self):
        if session == None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText('The database file is not defined.')
            msg.exec_()
            return
        speedPlotWin = SpeedPlotWindow(self)
        # tempHistWin.setModal(True)
        # tempHistWin.setAttribute(Qt.WA_DeleteOnClose)

        speedPlotWin.exec_()

    def odMatrix(self):
        if session == None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText('The database file is not defined.')
            msg.exec_()
            return
        odMtrxWin = OdMatrixWindow(self)
        # tempHistWin.setModal(True)
        # tempHistWin.setAttribute(Qt.WA_DeleteOnClose)

        odMtrxWin.exec_()

    def pieChart(self):
        if session == None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText('The database file is not defined.')
            msg.exec_()
            return
        pieChartWin = PieChartWindow(self)
        # tempHistWin.setModal(True)
        # tempHistWin.setAttribute(Qt.WA_DeleteOnClose)
        pieChartWin.exec_()

    def modeChart(self):
        if session == None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText('The database file is not defined.')
            msg.exec_()
            return
        modeChartWin = ModeChartWindow(self)
        # modeChartWin.setModal(True)
        # modeChartWin.setAttribute(Qt.WA_DeleteOnClose)
        modeChartWin.exec_()

    def compHist(self):
        if session == None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText('The database file is not defined.')
            msg.exec_()
            return
        compHistWin = CompHistWindow(self)

        # tempHistWin.setModal(True)
        # tempHistWin.setAttribute(Qt.WA_DeleteOnClose)

        compHistWin.exec_()

    def genReport(self):
        if session == None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText('The database file is not defined.')
            msg.exec_()
            return
        genRepWin = genReportWindow(self)
        genRepWin.setGeometry(200, 200, 800, 480)

        # tempHistWin.setModal(True)
        # tempHistWin.setAttribute(Qt.WA_DeleteOnClose)
        genRepWin.exec_()

    def compIndicators(self):
        if session == None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText('The database file is not defined.')
            msg.exec_()
            return
        compIndWin = compIndicatorsWindow(self)
        compIndWin.setGeometry(200, 100, 900, 600)

        # tempHistWin.setModal(True)
        # tempHistWin.setAttribute(Qt.WA_DeleteOnClose)
        compIndWin.exec_()

    def importTrajectories(self):
        if session == None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText('The database file is not defined.')
            msg.exec_()
            return

        importTrajWin = importTrajWindow(self)

        # tempHistWin.setModal(True)
        # tempHistWin.setAttribute(Qt.WA_DeleteOnClose)

        importTrajWin.exec_()

    def plotTrajectories(self):
        if session == None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText('The database file is not defined.')
            msg.exec_()
            return

        plotTrajWin = plotTrajWindow(self)

        # tempHistWin.setModal(True)
        # tempHistWin.setAttribute(Qt.WA_DeleteOnClose)

        plotTrajWin.exec_()

class TempHistWindow(QDialog):
    def __init__(self, parent=None):
        super(TempHistWindow, self).__init__(parent)

        self.setWindowTitle('Temporal Distribution Histogram')

        self.figure = plt.figure(tight_layout=True)

        self.canvas = FigureCanvas(self.figure)

        winLayout = QVBoxLayout()
        gridLayout = QGridLayout()

        gridLayout.addWidget(NavigationToolbar(self.canvas, self), 1, 0, 1, 7, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Transport:'), 0, 0, Qt.AlignRight)
        self.transportCombobx = QComboBox()
        self.transportCombobx.addItems(inspect(Mode).columns['transport'].type.enums)
        gridLayout.addWidget(self.transportCombobx, 0, 1, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Action type:'), 0, 2, Qt.AlignRight)
        self.actionTypeCombobx = QComboBox()
        self.actionTypeCombobx.addItems(actionTypeList)
        self.actionTypeCombobx.setCurrentIndex(-1)
        self.actionTypeCombobx.currentTextChanged.connect(self.actionTypeChanged)
        gridLayout.addWidget(self.actionTypeCombobx, 0, 3, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Unit Idx:'), 0, 4, Qt.AlignRight)
        self.unitIdxCombobx = QComboBox()
        gridLayout.addWidget(self.unitIdxCombobx, 0, 5, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Interval:'), 0, 6, Qt.AlignRight)
        self.intervaLe = QLineEdit('10')
        self.intervaLe.setFixedWidth(35)
        gridLayout.addWidget(self.intervaLe, 0, 7)#, Qt.AlignLeft)
        gridLayout.addWidget(QLabel('(min.)'), 0, 8, Qt.AlignLeft)

        self.plotBtn = QPushButton('Plot')
        self.plotBtn.clicked.connect(self.plotTHist)
        self.plotBtn.setEnabled(False)
        gridLayout.addWidget(self.plotBtn, 1, 7, 1, 2)

        # self.saveBtn = QPushButton()
        # self.saveBtn.setIcon(QIcon('icons/save.png'))
        # self.saveBtn.setToolTip('Save plot')
        # self.saveBtn.clicked.connect(self.saveTHist)
        # gridLayout.addWidget(self.saveBtn, 0, 7)

        # winLayout.addWidget(self.toolbar)
        winLayout.addLayout(gridLayout)
        winLayout.addWidget(self.canvas)

        self.setLayout(winLayout)

    def plotTHist(self):
        self.figure.clear()
        self.canvas.draw()

        ax = self.figure.add_subplot(111)

        # plot data
        transport = self.transportCombobx.currentText()
        actionType = self.actionTypeCombobx.currentText()
        unitIdx = self.unitIdxCombobx.currentText()
        interval = int(self.intervaLe.text())

        start_obs_time, end_obs_time = getObsStartEnd(session)
        if None in [start_obs_time, end_obs_time]:
            QMessageBox.information(self, 'Error!', 'There is no observation!')
            return
        bins = calculateBinsEdges(start_obs_time, end_obs_time, interval)

        # if len(bins) < 3:
        #     QMessageBox.information(self, 'Error!',
        #                             'The observation duration is not enough for the selected interval!')
        #     return
        err = tempDistHist(transport, actionType, unitIdx, ax, session, bins=bins)
        if err != None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText(err)
            msg.exec_()
        else:
            # refresh canvas
            self.canvas.draw()

    def saveTHist(self):
        fileName, _ = QFileDialog.getSaveFileName(self, "Open database file",
                                                  QDir.homePath(), "PNG files (*.png)")
        if fileName != '':
            self.canvas.print_png(fileName)

    def actionTypeChanged(self):
        actionType = self.actionTypeCombobx.currentText()

        self.unitIdxCombobx.clear()
        if 'line' in actionType.split(' '):
            self.unitIdxCombobx.addItems([str(id[0]) for id in session.query(Line.idx).all()])
        elif 'zone' in actionType.split(' '):
            self.unitIdxCombobx.addItems([str(id[0]) for id in session.query(Zone.idx).all()])

        self.plotBtn.setEnabled(True)

class StackHistWindow(QDialog):
    def __init__(self, parent=None):
        super(StackHistWindow, self).__init__(parent)

        self.setWindowTitle('Stacked Histogram')

        self.figure = plt.figure(tight_layout=True)

        self.canvas = FigureCanvas(self.figure)

        # self.toolbar = NavigationToolbar(self.canvas, self)

        winLayout = QVBoxLayout()
        gridLayout = QGridLayout()

        gridLayout.addWidget(NavigationToolbar(self.canvas, self), 1, 0, 1, 5, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Road user:'), 0, 0, Qt.AlignRight)
        self.userCombobx = QComboBox()
        self.userCombobx.addItems(['pedestrian', 'vehicle', 'activities'])
        gridLayout.addWidget(self.userCombobx, 0, 1, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Attribute:'), 0, 2, Qt.AlignRight)
        self.attrCombobx = QComboBox()
        self.attrCombobx.addItems(['age', 'gender', 'vehicleType', 'activityType'])
        gridLayout.addWidget(self.attrCombobx, 0, 3, Qt.AlignLeft)

        self.plotBtn = QPushButton('Plot')
        self.plotBtn.clicked.connect(self.plotSHist)
        gridLayout.addWidget(self.plotBtn, 0, 4)

        # self.saveBtn = QPushButton()
        # self.saveBtn.setIcon(QIcon('icons/save.png'))
        # self.saveBtn.setToolTip('Save plot')
        # self.saveBtn.clicked.connect(self.saveSHist)
        # gridLayout.addWidget(self.saveBtn, 0, 5)

        # winLayout.addWidget(self.toolbar)
        winLayout.addLayout(gridLayout)
        winLayout.addWidget(self.canvas)

        self.setLayout(winLayout)

    def plotSHist(self):
        self.figure.clear()
        self.canvas.draw()

        ax = self.figure.add_subplot(111)

        # plot data
        roadUser = self.userCombobx.currentText()
        attr = self.attrCombobx.currentText()

        # start_obs_time, end_obs_time = getObsStartEnd(session)
        bins = calculateNoBins(session)

        err = stackedHist(roadUser, attr, ax, session, bins)
        if err != None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText(err)
            msg.exec_()
        else:
            # refresh canvas
            self.canvas.draw()

    # def saveSHist(self):
    #     fileName, _ = QFileDialog.getSaveFileName(self, "Open database file",
    #                                               QDir.homePath(), "PNG files (*.png)")
    #     if fileName != '':
    #         self.canvas.print_png(fileName)


class SpeedPlotWindow(QDialog):
    def __init__(self, parent=None):
        super(SpeedPlotWindow, self).__init__(parent)

        self.setWindowTitle('Speed Diagram')

        self.figure = plt.figure(tight_layout=True)

        self.canvas = FigureCanvas(self.figure)

        winLayout = QVBoxLayout()
        dbLayout1 = QHBoxLayout()
        dbLayout2 = QHBoxLayout()
        gridLayout = QGridLayout()

        dbLayout1.addWidget(QLabel('Database file (Before):'))
        self.dbFile1Ledit = QLineEdit()
        dbLayout1.addWidget(self.dbFile1Ledit)

        self.openDbFileBtn1 = QPushButton()
        self.openDbFileBtn1.setIcon(QIcon('icons/database.png'))
        self.openDbFileBtn1.setToolTip('Open (before) database file')
        self.openDbFileBtn1.clicked.connect(self.opendbFile1)
        dbLayout1.addWidget(self.openDbFileBtn1)

        dbLayout2.addWidget(QLabel('Database file (After):'))
        self.dbFile2Ledit = QLineEdit()
        self.dbFile2Ledit.setText(self.parent().dbFilename)
        dbLayout2.addWidget(self.dbFile2Ledit)

        self.openDbFileBtn2 = QPushButton()
        self.openDbFileBtn2.setIcon(QIcon('icons/database.png'))
        self.openDbFileBtn2.setToolTip('Open (after) database file')
        self.openDbFileBtn2.clicked.connect(self.opendbFile2)
        dbLayout2.addWidget(self.openDbFileBtn2)

        gridLayout.addWidget(NavigationToolbar(self.canvas, self), 1, 0, 1, 5, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Plot type:'), 0, 0, Qt.AlignRight)
        self.plotTypeCmbx = QComboBox()
        self.plotTypeCmbx.addItems(['Box plot', 'Histogram'])
        self.plotTypeCmbx.currentIndexChanged.connect(self.plotTypeChanged)
        gridLayout.addWidget(self.plotTypeCmbx, 0, 1, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Transport:'), 0, 2, Qt.AlignRight)
        self.transportCombobx = QComboBox()
        self.transportCombobx.addItems(inspect(Mode).columns['transport'].type.enums)
        gridLayout.addWidget(self.transportCombobx, 0, 3, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Action type:'), 0, 4, Qt.AlignRight)
        self.actionTypeCombobx = QComboBox()
        self.actionTypeCombobx.addItems(actionTypeList)
        self.actionTypeCombobx.setCurrentIndex(-1)
        self.actionTypeCombobx.currentTextChanged.connect(self.actionTypeChanged)
        gridLayout.addWidget(self.actionTypeCombobx, 0, 5, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Unit Index:'), 0, 6, 1, 2, Qt.AlignRight)
        self.unitIdxCombobx = QComboBox()
        gridLayout.addWidget(self.unitIdxCombobx, 0, 8, Qt.AlignLeft)

        self.intervalType = QLabel('Time interval:')
        gridLayout.addWidget(self.intervalType, 1, 5, Qt.AlignRight)
        self.intervaLe = QLineEdit('30')
        self.intervaLe.setFixedWidth(35)
        gridLayout.addWidget(self.intervaLe, 1, 6)  # , Qt.AlignLeft)
        self.intervalUnit = QLabel('(min.)')
        gridLayout.addWidget(self.intervalUnit, 1, 7, Qt.AlignLeft)

        self.plotBtn = QPushButton('Plot')
        self.plotBtn.clicked.connect(self.plotSpeed)
        self.plotBtn.setEnabled(False)
        gridLayout.addWidget(self.plotBtn, 1, 8)

        winLayout.addLayout(dbLayout1)
        winLayout.addLayout(dbLayout2)
        winLayout.addLayout(gridLayout)
        winLayout.addWidget(self.canvas)

        self.setLayout(winLayout)

    def plotTypeChanged(self):
        if self.plotTypeCmbx.currentText() == 'Box plot':
            self.intervalType.setText('Time interval')
            self.intervaLe.setText('30')
            self.intervalUnit.setText('(min.)')
        elif self.plotTypeCmbx.currentText() == 'Histogram':
            self.intervalType.setText('Speed interval')
            self.intervaLe.setText('5')
            self.intervalUnit.setText('(km/h)')

    def plotSpeed(self):
        self.figure.clear()
        self.canvas.draw()

        ax = self.figure.add_subplot(111)

        # plot data
        transport = self.transportCombobx.currentText()
        actionType = self.actionTypeCombobx.currentText()
        unitIdx = self.unitIdxCombobx.currentText()
        interval = int(self.intervaLe.text())

        dbFilename1 = self.dbFile1Ledit.text()
        dbFilename2 = self.dbFile2Ledit.text()

        if dbFilename1 == '' or dbFilename2 == '':
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText('The database file is not defined!')
            msg.exec_()
            return

        self.session1 = createDatabase(dbFilename1)
        if self.session1 is None:
            self.session1 = connectDatabase(dbFilename1)

        self.session2 = createDatabase(dbFilename2)
        if self.session2 is None:
            self.session2 = connectDatabase(dbFilename2)
        if self.plotTypeCmbx.currentText() == 'Box plot':
            cls_obs = LinePassing
            first_obs_time1 = self.session1.query(func.min(cls_obs.instant)).all()[0][0]
            last_obs_time1 = self.session1.query(func.max(cls_obs.instant)).all()[0][0]

            first_obs_time2 = self.session2.query(func.min(cls_obs.instant)).all()[0][0]
            last_obs_time2 = self.session2.query(func.max(cls_obs.instant)).all()[0][0]

            if first_obs_time1.time() >= first_obs_time2.time():
                bins_start = first_obs_time1
            else:
                bins_start = first_obs_time2

            if last_obs_time1.time() <= last_obs_time2.time():
                bins_end = last_obs_time1
            else:
                bins_end = last_obs_time2

            start = datetime.datetime(2000, 1, 1, bins_start.hour, bins_start.minute, bins_start.second)
            end = datetime.datetime(2000, 1, 1, bins_end.hour, bins_end.minute, bins_end.second)

            bins = calculateBinsEdges(start, end, interval)
            if len(bins) < 2:
                QMessageBox.information(self, 'Error!',
                                        'The common observation duration is too short!')
                return
            times = [b.time() for b in bins]
            err = speedBoxPlot(transport, actionType, unitIdx, times, ax, [self.session1, self.session2])
            if err != None:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Information)
                msg.setText(err)
                msg.exec_()
            else:
                # refresh canvas
                self.canvas.draw()
        elif self.plotTypeCmbx.currentText() == 'Histogram':
            err = speedHistogram(transport, actionType, unitIdx, interval, ax,
                                 [self.session1, self.session2])
            if err != None:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Information)
                msg.setText(err)
                msg.exec_()
            else:
                # refresh canvas
                self.canvas.draw()

    def opendbFile1(self):
        dbFilename, _ = QFileDialog.getOpenFileName(self, "Open database file",
                                                    QDir.homePath(), "Sqlite files (*.sqlite)")
        if dbFilename != '':
            self.dbFile1Ledit.setText(dbFilename)

    def opendbFile2(self):
        dbFilename, _ = QFileDialog.getOpenFileName(self, "Open database file",
                                                    QDir.homePath(), "Sqlite files (*.sqlite)")
        if dbFilename != '':
            self.dbFile2Ledit.setText(dbFilename)

    def actionTypeChanged(self):
        actionType = self.actionTypeCombobx.currentText()

        self.unitIdxCombobx.clear()
        if 'line' in actionType.split(' '):
            self.unitIdxCombobx.addItems([str(id[0]) for id in session.query(Line.idx).all()])
        elif 'zone' in actionType.split(' '):
            self.unitIdxCombobx.addItems([str(id[0]) for id in session.query(Zone.idx).all()])

        self.plotBtn.setEnabled(True)


class OdMatrixWindow(QDialog):
    def __init__(self, parent=None):
        super(OdMatrixWindow, self).__init__(parent)

        self.setWindowTitle('OD Matrix')

        self.figure = plt.figure(tight_layout=True)

        self.canvas = FigureCanvas(self.figure)

        # self.toolbar = NavigationToolbar(self.canvas, self)

        winLayout = QVBoxLayout()
        gridLayout = QGridLayout()

        gridLayout.addWidget(NavigationToolbar(self.canvas, self), 1, 0, 1, 7, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Road user:'), 0, 0, Qt.AlignRight)
        self.userCombobx = QComboBox()
        self.userCombobx.addItems(['pedestrian', 'vehicle', 'cyclist'])
        gridLayout.addWidget(self.userCombobx, 0, 1, Qt.AlignLeft)

        self.plotBtn = QPushButton('Plot')
        self.plotBtn.clicked.connect(self.plotOdMtrx)
        gridLayout.addWidget(self.plotBtn, 0, 2)

        # self.saveBtn = QPushButton()
        # self.saveBtn.setIcon(QIcon('icons/save.png'))
        # self.saveBtn.setToolTip('Save plot')
        # self.saveBtn.clicked.connect(self.saveOdMtrx)
        # gridLayout.addWidget(self.saveBtn, 0, 3)

        # winLayout.addWidget(self.toolbar)
        winLayout.addLayout(gridLayout)
        winLayout.addWidget(self.canvas)

        self.setLayout(winLayout)

    def plotOdMtrx(self):
        self.figure.clear()
        self.canvas.draw()

        ax = self.figure.add_subplot(111)

        # plot data
        roadUser = self.userCombobx.currentText()

        # start_obs_time, end_obs_time = getObsStartEnd(session)

        err = odMatrix(roadUser, ax, session)
        if err != None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText(err)
            msg.exec_()
        else:
            # refresh canvas
            self.canvas.draw()

    # def saveOdMtrx(self):
    #     fileName, _ = QFileDialog.getSaveFileName(self, "Open database file",
    #                                               QDir.homePath(), "PNG files (*.png)")
    #     if fileName != '':
    #         self.canvas.print_png(fileName)


class PieChartWindow(QDialog):
    def __init__(self, parent=None):
        super(PieChartWindow, self).__init__(parent)

        self.setWindowTitle('Pie Chart')

        self.figure = plt.figure(tight_layout=True)

        self.canvas = FigureCanvas(self.figure)

        # self.toolbar = NavigationToolbar(self.canvas, self)

        winLayout = QVBoxLayout()
        gridLayout = QGridLayout()

        gridLayout.addWidget(NavigationToolbar(self.canvas, self), 1, 0, 1, 7, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Transport:'), 0, 0, Qt.AlignRight)
        self.transportCombobx = QComboBox()
        self.transportCombobx.addItems(['all types', 'walking', 'cardriver'])
        self.transportCombobx.currentTextChanged.connect(self.getAttrList)
        gridLayout.addWidget(self.transportCombobx, 0, 1, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Attribute:'), 0, 2, Qt.AlignRight)
        self.attrCombobx = QComboBox()
        self.attrCombobx.addItems(['transport'])
        gridLayout.addWidget(self.attrCombobx, 0, 3, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Time span:'), 0, 4, Qt.AlignRight)
        self.timeSpanCombobx = QComboBox()

        start_obs_time, end_obs_time = getObsStartEnd(session)
        if start_obs_time != None:
            bins = calculateBinsEdges(start_obs_time, end_obs_time)
            if len(bins) > 1:
                start_time = bins[0]
                end_time = bins[-1]

                peakHours = getPeakHours(session, start_time, end_time)
                timeSpans = ['{} - {}'.format(start_time.strftime('%I:%M %p'),
                                              end_time.strftime('%I:%M %p'))]
                for pVal in peakHours.values():
                    if pVal != None:
                        ts = '{} - {}'.format(pVal[0].strftime('%I:%M %p'), pVal[1].strftime('%I:%M %p'))
                        if ts != timeSpans[0]:
                            timeSpans.append(ts)
            else:
                timeSpans = ['Too short observation!']
        else:
            timeSpans = ['No observation!']


        self.timeSpanCombobx.addItems(timeSpans)
        self.timeSpanCombobx.currentTextChanged.connect(self.plotPieChart)
        gridLayout.addWidget(self.timeSpanCombobx, 0, 5, Qt.AlignLeft)

        self.plotBtn = QPushButton('Plot')
        self.plotBtn.clicked.connect(self.plotPieChart)
        gridLayout.addWidget(self.plotBtn, 0, 6)

        # self.saveBtn = QPushButton()
        # self.saveBtn.setIcon(QIcon('icons/save.png'))
        # self.saveBtn.setToolTip('Save plot')
        # self.saveBtn.clicked.connect(self.savePieChart)
        # gridLayout.addWidget(self.saveBtn, 0, 7)

        # winLayout.addWidget(self.toolbar)
        winLayout.addLayout(gridLayout)
        winLayout.addWidget(self.canvas)

        self.setLayout(winLayout)

    def plotPieChart(self):
        if self.timeSpanCombobx.currentText() == 'No observation!':
            QMessageBox.information(self, 'Error!', 'There is no observation!')
            return
        elif self.timeSpanCombobx.currentText() == 'Too short observation!':
            QMessageBox.information(self, 'Error!', 'The observation duration is too short!')
            return
        self.figure.clear()
        self.canvas.draw()

        ax = self.figure.add_subplot(111)

        # plot data
        transport = self.transportCombobx.currentText()
        attr = self.attrCombobx.currentText()

        sTimeText = self.timeSpanCombobx.currentText().split(' - ')[0]
        sTime = datetime.datetime.strptime(sTimeText, '%I:%M %p').time()

        eTimeText = self.timeSpanCombobx.currentText().split(' - ')[1]
        eTime = datetime.datetime.strptime(eTimeText, '%I:%M %p').time()

        err = pieChart(transport, attr, sTime, eTime, ax, session)
        if err != None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText(err)
            msg.exec_()
        else:
            # refresh canvas
            self.canvas.draw()

    def savePieChart(self):
        fileName, _ = QFileDialog.getSaveFileName(self, "Save image file",
                                                  QDir.homePath(), "PNG files (*.png)")
        if fileName != '':
            self.canvas.print_png(fileName)

    def getAttrList(self):
        self.attrCombobx.clear()
        if self.transportCombobx.currentText() == 'all types':
            self.attrCombobx.addItems(['transport'])
        elif self.transportCombobx.currentText() == 'walking':
            self.attrCombobx.addItems(['age', 'gender'])
        elif self.transportCombobx.currentText() == 'cardriver':
            self.attrCombobx.addItems(['category'])
        # elif self.siteNameCombobx.currentText() == 'Bike':
        #     self.attrCombobx.addItems(['bikeType', 'wearHelmet'])
        # elif self.siteNameCombobx.currentText() == 'Activity':
        #     self.attrCombobx.addItems(['activityType'])


class ModeChartWindow(QDialog):
    def __init__(self, parent=None):
        super(ModeChartWindow, self).__init__(parent)

        self.setWindowTitle('Comparative Mode Share Chart')
        self.setMinimumHeight(550)

        self.figure = plt.figure(tight_layout=True)

        self.canvas = FigureCanvas(self.figure)

        # self.toolbar = NavigationToolbar(self.canvas, self)

        winLayout = QVBoxLayout()
        dbLayout1 = QHBoxLayout()
        dbLayout2 = QHBoxLayout()
        gridLayout = QGridLayout()

        dbLayout1.addWidget(QLabel('Database file (Before):'))
        self.dbFile1Ledit = QLineEdit()
        dbLayout1.addWidget(self.dbFile1Ledit)

        self.openDbFileBtn1 = QPushButton()
        self.openDbFileBtn1.setIcon(QIcon('icons/database.png'))
        self.openDbFileBtn1.setToolTip('Open (before) database file')
        self.openDbFileBtn1.clicked.connect(self.opendbFile1)
        dbLayout1.addWidget(self.openDbFileBtn1)

        dbLayout2.addWidget(QLabel('Database file (After):'))
        self.dbFile2Ledit = QLineEdit()
        self.dbFile2Ledit.setText(self.parent().dbFilename)
        dbLayout2.addWidget(self.dbFile2Ledit)

        self.openDbFileBtn2 = QPushButton()
        self.openDbFileBtn2.setIcon(QIcon('icons/database.png'))
        self.openDbFileBtn2.setToolTip('Open (after) database file')
        self.openDbFileBtn2.clicked.connect(self.opendbFile2)
        dbLayout2.addWidget(self.openDbFileBtn2)

        gridLayout.addWidget(NavigationToolbar(self.canvas, self), 0, 0, 1, 5, Qt.AlignLeft)

        # gridLayout.addWidget(QLabel('Action type:'), 0, 0, Qt.AlignRight)
        # self.actionTypeCombobx = QComboBox()
        # self.actionTypeCombobx.addItems(actionTypeList)
        # self.actionTypeCombobx.setCurrentIndex(-1)
        # self.actionTypeCombobx.currentTextChanged.connect(self.actionTypeChanged)
        # gridLayout.addWidget(self.actionTypeCombobx, 0, 1, Qt.AlignLeft)
        #
        # gridLayout.addWidget(QLabel('Unit Idx:'), 0, 2, Qt.AlignRight)
        # self.unitIdxCombobx = QComboBox()
        # gridLayout.addWidget(self.unitIdxCombobx, 0, 3, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Interval:'), 0, 5, Qt.AlignRight)
        self.intervalLe = QLineEdit('60')
        self.intervalLe.setFixedWidth(35)
        gridLayout.addWidget(self.intervalLe, 0, 6)#, Qt.AlignRight)
        gridLayout.addWidget(QLabel('(min.)'), 0, 7)#, Qt.AlignLeft)

        self.plotBtn = QPushButton('Plot')
        self.plotBtn.clicked.connect(self.plotModeChart)
        gridLayout.addWidget(self.plotBtn, 0, 8)

        # winLayout.addWidget(self.toolbar)
        winLayout.addLayout(dbLayout1)
        winLayout.addLayout(dbLayout2)
        winLayout.addLayout(gridLayout)
        winLayout.addWidget(self.canvas)

        self.setLayout(winLayout)

    def plotModeChart(self):
        self.figure.clear()
        self.canvas.draw()

        ax = self.figure.subplots(2, 2, sharex=True, sharey='row')

        dbFilename1 = self.dbFile1Ledit.text()
        dbFilename2 = self.dbFile2Ledit.text()

        if dbFilename1 == '' or dbFilename2 == '':
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText('The database file is not defined!')
            msg.exec_()
            return

        self.session1 = createDatabase(dbFilename1)
        if self.session1 is None:
            self.session1 = connectDatabase(dbFilename1)

        self.session2 = createDatabase(dbFilename2)
        if self.session2 is None:
            self.session2 = connectDatabase(dbFilename2)

        # actionType = self.actionTypeCombobx.currentText()
        # unitIdx = self.unitIdxCombobx.currentText()

        # if 'line' in actionType.split(' '):
        #     cls_obs = LinePassing
        # elif 'zone' in actionType.split(' '):
        #     cls_obs = ZoneCrossing
        cls_obs = LinePassing
        first_obs_time1 = self.session1.query(func.min(cls_obs.instant)).all()[0][0]
        last_obs_time1 = self.session1.query(func.max(cls_obs.instant)).all()[0][0]

        first_obs_time2 = self.session2.query(func.min(cls_obs.instant)).all()[0][0]
        last_obs_time2 = self.session2.query(func.max(cls_obs.instant)).all()[0][0]

        if first_obs_time1.time() >= first_obs_time2.time():
            bins_start = first_obs_time1
        else:
            bins_start = first_obs_time2

        if last_obs_time1.time() <= last_obs_time2.time():
            bins_end = last_obs_time1
        else:
            bins_end = last_obs_time2

        start = datetime.datetime(2000, 1, 1, bins_start.hour, bins_start.minute, bins_start.second)
        end = datetime.datetime(2000, 1, 1, bins_end.hour, bins_end.minute, bins_end.second)

        duration = end - start
        duration_in_s = duration.total_seconds()

        timeInterval = int(self.intervalLe.text())
        bins = calculateBinsEdges(start, end, timeInterval)
        if len(bins) < 2:
            QMessageBox.information(self, 'Error!',
                    'The common observation duration is too short!')
            return

        label1 = self.session1.query(LinePassing.instant).first()[0].strftime('%a, %b %d, %Y')
        label2 = self.session2.query(LinePassing.instant).first()[0].strftime('%a, %b %d, %Y')

        times = [b.time() for b in bins]

        modeShareCompChart(times, ax, [label1, label2], [self.session1, self.session2])
        self.canvas.draw()
        # err = tempDistHist(transport, actionType, unitIdx, ax, [self.session1, self.session2],
        #                    bins=bins, alpha=0.7, color=['skyblue', 'red'], ec='grey',
        #                    label=[label1, label2], rwidth=0.9)
        # plt.legend(loc='upper right', fontsize=6)
        # if err != None:
        #     msg = QMessageBox()
        #     msg.setIcon(QMessageBox.Information)
        #     msg.setText(err)
        #     msg.exec_()
        # else:
        #     # refresh canvas
        #     self.canvas.draw()

    def opendbFile1(self):
        dbFilename, _ = QFileDialog.getOpenFileName(self, "Open database file",
                                                    QDir.homePath(), "Sqlite files (*.sqlite)")
        if dbFilename != '':
            self.dbFile1Ledit.setText(dbFilename)

    def opendbFile2(self):
        dbFilename, _ = QFileDialog.getOpenFileName(self, "Open database file",
                                                    QDir.homePath(), "Sqlite files (*.sqlite)")
        if dbFilename != '':
            self.dbFile2Ledit.setText(dbFilename)

    def actionTypeChanged(self):
        actionType = self.actionTypeCombobx.currentText()

        self.unitIdxCombobx.clear()
        if 'line' in actionType.split(' '):
            self.unitIdxCombobx.addItems([str(id[0]) for id in session.query(Line.idx).all()])
        elif 'zone' in actionType.split(' '):
            self.unitIdxCombobx.addItems([str(id[0]) for id in session.query(Zone.idx).all()])

        self.plotBtn.setEnabled(True)



class CompHistWindow(QDialog):
    def __init__(self, parent=None):
        super(CompHistWindow, self).__init__(parent)

        self.setWindowTitle('Comparative Temporal Distribution Plot')

        self.figure = plt.figure(tight_layout=True)

        self.canvas = FigureCanvas(self.figure)

        # self.toolbar = NavigationToolbar(self.canvas, self)

        winLayout = QVBoxLayout()
        dbLayout1 = QHBoxLayout()
        dbLayout2 = QHBoxLayout()
        gridLayout = QGridLayout()

        dbLayout1.addWidget(QLabel('Database file (Before):'))
        self.dbFile1Ledit = QLineEdit()
        dbLayout1.addWidget(self.dbFile1Ledit)

        self.openDbFileBtn1 = QPushButton()
        self.openDbFileBtn1.setIcon(QIcon('icons/database.png'))
        self.openDbFileBtn1.setToolTip('Open (before) database file')
        self.openDbFileBtn1.clicked.connect(self.opendbFile1)
        dbLayout1.addWidget(self.openDbFileBtn1)

        dbLayout2.addWidget(QLabel('Database file (After):'))
        self.dbFile2Ledit = QLineEdit()
        self.dbFile2Ledit.setText(self.parent().dbFilename)
        dbLayout2.addWidget(self.dbFile2Ledit)

        self.openDbFileBtn2 = QPushButton()
        self.openDbFileBtn2.setIcon(QIcon('icons/database.png'))
        self.openDbFileBtn2.setToolTip('Open (after) database file')
        self.openDbFileBtn2.clicked.connect(self.opendbFile2)
        dbLayout2.addWidget(self.openDbFileBtn2)

        gridLayout.addWidget(NavigationToolbar(self.canvas, self), 1, 0, 1, 7, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Plot type:'), 0, 0, Qt.AlignRight)
        self.plotTypeCmbx = QComboBox()
        self.plotTypeCmbx.addItems(['Line plot', 'Scatter plot'])
        # self.plotTypeCmbx.currentIndexChanged.connect(self.plotTypeChanged)
        gridLayout.addWidget(self.plotTypeCmbx, 0, 1, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Transport:'), 0, 2, Qt.AlignRight)
        self.transportCombobx = QComboBox()
        self.transportCombobx.addItems(inspect(Mode).columns['transport'].type.enums)
        gridLayout.addWidget(self.transportCombobx, 0, 3, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Action type:'), 0, 4, Qt.AlignRight)
        self.actionTypeCombobx = QComboBox()
        self.actionTypeCombobx.addItems(actionTypeList)
        self.actionTypeCombobx.setCurrentIndex(-1)
        self.actionTypeCombobx.currentTextChanged.connect(self.actionTypeChanged)
        gridLayout.addWidget(self.actionTypeCombobx, 0, 5, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Unit Idx:'), 0, 6, Qt.AlignRight)
        self.unitIdxCombobx = QComboBox()
        gridLayout.addWidget(self.unitIdxCombobx, 0, 7, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Interval:'), 0, 8, Qt.AlignRight)
        self.intervaLe = QLineEdit('10')
        self.intervaLe.setFixedWidth(35)
        gridLayout.addWidget(self.intervaLe, 0, 9)  # , Qt.AlignLeft)
        gridLayout.addWidget(QLabel('(min.)'), 0, 10, Qt.AlignLeft)

        self.plotBtn = QPushButton('Plot')
        self.plotBtn.clicked.connect(self.plotCompHist)
        self.plotBtn.setEnabled(False)
        gridLayout.addWidget(self.plotBtn, 1, 9, 1 ,2)

        # self.saveBtn = QPushButton()
        # self.saveBtn.setIcon(QIcon('icons/save.png'))
        # self.saveBtn.setToolTip('Save plot')
        # self.saveBtn.clicked.connect(self.saveCompHist)
        # gridLayout.addWidget(self.saveBtn, 0, 7)

        # winLayout.addWidget(self.toolbar)
        winLayout.addLayout(dbLayout1)
        winLayout.addLayout(dbLayout2)
        winLayout.addLayout(gridLayout)
        winLayout.addWidget(self.canvas)

        self.setLayout(winLayout)

    def plotCompHist(self):
        self.figure.clear()
        self.canvas.draw()

        ax = self.figure.add_subplot(111)

        dbFilename1 = self.dbFile1Ledit.text()
        dbFilename2 = self.dbFile2Ledit.text()

        if dbFilename1 == '' or dbFilename2 == '':
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText('The database file is not defined!')
            msg.exec_()
            return

        self.session1 = createDatabase(dbFilename1)
        if self.session1 is None:
            self.session1 = connectDatabase(dbFilename1)

        self.session2 = createDatabase(dbFilename2)
        if self.session2 is None:
            self.session2 = connectDatabase(dbFilename2)

        transport = self.transportCombobx.currentText()
        actionType = self.actionTypeCombobx.currentText()
        unitIdx = self.unitIdxCombobx.currentText()
        interval = int(self.intervaLe.text())
        plotType = self.plotTypeCmbx.currentText()

        if 'line' in actionType.split(' '):
            cls_obs = LinePassing
        elif 'zone' in actionType.split(' '):
            cls_obs = ZoneCrossing

        first_obs_time1 = self.session1.query(func.min(cls_obs.instant)).all()[0][0]
        last_obs_time1 = self.session1.query(func.max(cls_obs.instant)).all()[0][0]

        first_obs_time2 = self.session2.query(func.min(cls_obs.instant)).all()[0][0]
        last_obs_time2 = self.session2.query(func.max(cls_obs.instant)).all()[0][0]

        if first_obs_time1.time() >= first_obs_time2.time():
            bins_start = first_obs_time1
        else:
            bins_start = first_obs_time2

        if last_obs_time1.time() <= last_obs_time2.time():
            bins_end = last_obs_time1
        else:
            bins_end = last_obs_time2

        start = datetime.datetime(2000, 1, 1, bins_start.hour, bins_start.minute, bins_start.second)
        end = datetime.datetime(2000, 1, 1, bins_end.hour, bins_end.minute, bins_end.second)

        duration = end - start
        duration_in_s = duration.total_seconds()

        bins = calculateBinsEdges(start, end, interval)
        if len(bins) < 2:
            QMessageBox.information(self, 'Error!',
                    'The common observation duration is too short!')
            return
        # label1 = os.path.basename(self.parent().dbFilename).split('.')[0]
        # label2 = os.path.basename(self.dbFile2Ledit.text()).split('.')[0]
        label1 = self.session1.query(LinePassing.instant).first()[0].strftime('%a, %b %d, %Y')
        label2 = self.session2.query(LinePassing.instant).first()[0].strftime('%a, %b %d, %Y')

        err = tempDistHist(transport, actionType, unitIdx, ax, [self.session1, self.session2],
                           bins=bins, alpha=0.7, color=['skyblue', 'red'],
                           label=[label1, label2], plotType=plotType)

        if err != None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText(err)
            msg.exec_()
        else:
            # refresh canvas
            self.canvas.draw()

    # def saveCompHist(self):
    #     fileName, _ = QFileDialog.getSaveFileName(self, "Save image file",
    #                                               QDir.homePath(), "PNG files (*.png)")
    #     if fileName != '':
    #         self.canvas.print_png(fileName)

    def opendbFile1(self):
        dbFilename, _ = QFileDialog.getOpenFileName(self, "Open database file",
                                                    QDir.homePath(), "Sqlite files (*.sqlite)")
        if dbFilename != '':
            self.dbFile1Ledit.setText(dbFilename)

    def opendbFile2(self):
        dbFilename, _ = QFileDialog.getOpenFileName(self, "Open database file",
                                                    QDir.homePath(), "Sqlite files (*.sqlite)")
        if dbFilename != '':
            self.dbFile2Ledit.setText(dbFilename)

    def actionTypeChanged(self):
        actionType = self.actionTypeCombobx.currentText()

        self.unitIdxCombobx.clear()
        if 'line' in actionType.split(' '):
            self.unitIdxCombobx.addItems([str(id[0]) for id in session.query(Line.idx).all()])
        elif 'zone' in actionType.split(' '):
            self.unitIdxCombobx.addItems([str(id[0]) for id in session.query(Zone.idx).all()])

        self.plotBtn.setEnabled(True)


class genReportWindow(QDialog):
    def __init__(self, parent=None):
        super(genReportWindow, self).__init__(parent)

        self.setWindowTitle('List of indicators')
        self.setWindowIcon(QIcon('icons/report.png'))
        self.table = QTableView()
        # self.table.horizontalHeader().setStretchLastSection(True)
        # self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # self.table.verticalHeader().hide()
        self.indicatorsDf = None


        winLayout = QVBoxLayout()
        gridLayout = QGridLayout()

        gridLayout.addWidget(QLabel('Transport:'), 0, 0, Qt.AlignRight)
        self.transportCombobx = QComboBox()
        self.transportCombobx.addItems(inspect(Mode).columns['transport'].type.enums)
        # self.siteNameCombobx.currentTextChanged.connect(self.genReport)
        gridLayout.addWidget(self.transportCombobx, 0, 1, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Action type:'), 0, 2, Qt.AlignRight)
        self.actionTypeCombobx = QComboBox()
        self.actionTypeCombobx.addItems(actionTypeList)
        self.actionTypeCombobx.setCurrentIndex(-1)
        self.actionTypeCombobx.currentTextChanged.connect(self.actionTypeChanged)
        gridLayout.addWidget(self.actionTypeCombobx, 0, 3, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Unit Idx:'), 0, 4, Qt.AlignRight)
        self.unitIdxCombobx = QComboBox()
        gridLayout.addWidget(self.unitIdxCombobx, 0, 5, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Time interval:'), 0, 6, Qt.AlignRight)
        self.intervalCombobx = QComboBox()
        self.intervalCombobx.addItems(['5', '10', '15', '20', '30', '60', '90', '120'])
        gridLayout.addWidget(self.intervalCombobx, 0, 7)#, Qt.AlignLeft)
        gridLayout.addWidget(QLabel('(min.)'), 0, 8, Qt.AlignLeft)


        self.genRepBtn = QPushButton('Generate report')
        self.genRepBtn.clicked.connect(self.genReport)
        gridLayout.addWidget(self.genRepBtn, 0, 9)

        self.saveBtn = QPushButton()
        self.saveBtn.setIcon(QIcon('icons/save.png'))
        self.saveBtn.setToolTip('Save report')
        self.saveBtn.clicked.connect(self.saveReport)
        gridLayout.addWidget(self.saveBtn, 0, 10)

        # winLayout.addWidget(self.toolbar)
        winLayout.addLayout(gridLayout)
        winLayout.addWidget(self.table)

        self.setLayout(winLayout)

    def genReport(self):

        transport = self.transportCombobx.currentText()
        actionType = self.actionTypeCombobx.currentText()
        unitIdx = self.unitIdxCombobx.currentText()
        interval = int(self.intervalCombobx.currentText())


        # bins = calculateBinsEdges(start_obs_time, end_obs_time)
        # if len(bins) < 2:
        #     QMessageBox.information(self, 'Error!', 'The observation duration is too short!')
        #     return
        # else:
        #     start_time = bins[0]
        #     end_time = bins[-1]
        self.indicatorsDf = generateReport(transport, actionType, unitIdx, interval, session)

        norm_indDf = pd.DataFrame()
        for i in range(self.indicatorsDf.shape[0]):
            for j in range(self.indicatorsDf.shape[1]):
                if j == 0:
                    norm_indDf.loc[i, j] = None
                    continue
                val_str = str(self.indicatorsDf.iloc[i, j]).split(' ')[0]
                if val_str.isdigit():
                    value = int(val_str)
                elif val_str.replace('.', '', 1).isdigit():
                    value = float(val_str)
                else:
                    value = None
                norm_indDf.loc[i, j] = value
            min_val = np.nanmin(norm_indDf.loc[i, :])
            max_val = np.nanmax(norm_indDf.loc[i, :])
            range_val = max_val - min_val
            if range_val != 0:
                norm_indDf.loc[i, :] = norm_indDf.loc[i, :].apply(lambda x: (x - min_val)/range_val)
            else:
                norm_indDf.loc[i, :] = 0

        model = dfTableModel(self.indicatorsDf, norm_indDf)
        self.table.setModel(model)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)#.Stretch)

    def saveReport(self):
        if not self.indicatorsDf is None:
            self.indicatorsDf.to_clipboard()
            msg = QMessageBox()
            msg.setText('The table is copied to the clipboard.')
            msg.exec_()

    def actionTypeChanged(self):
        actionType = self.actionTypeCombobx.currentText()

        self.unitIdxCombobx.clear()
        if 'line' in actionType.split(' '):
            self.unitIdxCombobx.addItems([str(id[0]) for id in session.query(Line.idx).all()])
        elif 'zone' in actionType.split(' '):
            self.unitIdxCombobx.addItems([str(id[0]) for id in session.query(Zone.idx).all()])

        # self.genRepBtn.setEnabled(True)


class compIndicatorsWindow(QDialog):
    def __init__(self, parent=None):
        super(compIndicatorsWindow, self).__init__(parent)

        self.setWindowTitle('Comparison of indicators')
        self.setWindowIcon(QIcon('icons/positive.png'))
        self.table = QTableView()
        # self.table.horizontalHeader().setStretchLastSection(True)
        # self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # self.table.verticalHeader().hide()
        self.indicatorsDf = None
        self.session1 = None
        self.session2 = None

        winLayout = QVBoxLayout()
        dbLayout1 = QHBoxLayout()
        dbLayout2 = QHBoxLayout()
        gridLayout = QGridLayout()

        dbLayout1.addWidget(QLabel('Database file (Before):'))
        self.dbFile1Ledit = QLineEdit()
        dbLayout1.addWidget(self.dbFile1Ledit)

        self.openDbFileBtn1 = QPushButton()
        self.openDbFileBtn1.setIcon(QIcon('icons/database.png'))
        self.openDbFileBtn1.setToolTip('Open database file')
        self.openDbFileBtn1.clicked.connect(self.opendbFile1)
        dbLayout1.addWidget(self.openDbFileBtn1)


        dbLayout2.addWidget(QLabel('Database file (After):'))
        self.dbFile2Ledit = QLineEdit()
        self.dbFile2Ledit.setText(self.parent().dbFilename)
        dbLayout2.addWidget(self.dbFile2Ledit)

        self.openDbFileBtn2 = QPushButton()
        self.openDbFileBtn2.setIcon(QIcon('icons/database.png'))
        self.openDbFileBtn2.setToolTip('Open database file')
        self.openDbFileBtn2.clicked.connect(self.opendbFile2)
        dbLayout2.addWidget(self.openDbFileBtn2)

        gridLayout.addWidget(QLabel('Transport:'), 0, 0, Qt.AlignRight)
        self.transportCombobx = QComboBox()
        self.transportCombobx.addItems(inspect(Mode).columns['transport'].type.enums)
        # self.siteNameCombobx.currentTextChanged.connect(self.compIndicators)
        gridLayout.addWidget(self.transportCombobx, 0, 1, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Action type:'), 0, 2, Qt.AlignRight)
        self.actionTypeCombobx = QComboBox()
        self.actionTypeCombobx.addItems(actionTypeList)
        self.actionTypeCombobx.setCurrentIndex(-1)
        self.actionTypeCombobx.currentTextChanged.connect(self.actionTypeChanged)
        gridLayout.addWidget(self.actionTypeCombobx, 0, 3, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Unit Idx:'), 0, 4, Qt.AlignRight)
        self.unitIdxCombobx = QComboBox()
        gridLayout.addWidget(self.unitIdxCombobx, 0, 5, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Time interval:'), 0, 6, Qt.AlignRight)
        self.intervalCombobx = QComboBox()
        self.intervalCombobx.addItems(['5', '10', '15', '20', '30', '60', '90', '120'])
        gridLayout.addWidget(self.intervalCombobx, 0, 7)  # , Qt.AlignLeft)
        gridLayout.addWidget(QLabel('(min.)'), 0, 8, Qt.AlignLeft)

        self.genRepBtn = QPushButton('Compare Indicators')
        self.genRepBtn.clicked.connect(self.compIndicators)
        gridLayout.addWidget(self.genRepBtn, 0, 9)

        self.saveBtn = QPushButton()
        self.saveBtn.setIcon(QIcon('icons/save.png'))
        self.saveBtn.setToolTip('Save results to clipboard')
        self.saveBtn.setFixedWidth(75)
        self.saveBtn.clicked.connect(self.saveReport)
        gridLayout.addWidget(self.saveBtn, 0, 10)

        # winLayout.addWidget(self.toolbar)
        winLayout.addLayout(dbLayout1)
        winLayout.addLayout(dbLayout2)
        winLayout.addLayout(gridLayout)
        winLayout.addWidget(self.table)

        self.setLayout(winLayout)

    def compIndicators(self):
        dbFilename1 = self.dbFile1Ledit.text()
        dbFilename2 = self.dbFile2Ledit.text()

        if dbFilename1 == '' or dbFilename2 == '':
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText('The database file is not defined!')
            msg.exec_()
            return

        self.session1 = createDatabase(dbFilename1)
        if self.session1 is None:
            self.session1 = connectDatabase(dbFilename1)

        self.session2 = createDatabase(dbFilename2)
        if self.session2 is None:
            self.session2 = connectDatabase(dbFilename2)

        transport = self.transportCombobx.currentText()
        actionType = self.actionTypeCombobx.currentText()
        unitIdx = self.unitIdxCombobx.currentText()
        interval = int(self.intervalCombobx.currentText())

        self.indicatorsDf = compareIndicators(transport, actionType, unitIdx, interval,
                                              self.session1, self.session2)

        model = dfTableModel(self.indicatorsDf)
        self.table.setModel(model)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)#.Stretch)

    def saveReport(self):
        if not self.indicatorsDf is None:
            self.indicatorsDf.to_clipboard()
            msg = QMessageBox()
            msg.setText('The table is copied to the clipboard.')
            msg.exec_()

    def opendbFile1(self):
        dbFilename, _ = QFileDialog.getOpenFileName(self, "Open database file",
                                                    QDir.homePath(), "Sqlite files (*.sqlite)")
        if dbFilename != '':
            self.dbFile1Ledit.setText(dbFilename)

    def opendbFile2(self):
        dbFilename, _ = QFileDialog.getOpenFileName(self, "Open database file",
                                                    QDir.homePath(), "Sqlite files (*.sqlite)")
        if dbFilename != '':
            self.dbFile2Ledit.setText(dbFilename)

    def actionTypeChanged(self):
        actionType = self.actionTypeCombobx.currentText()

        self.unitIdxCombobx.clear()
        if 'line' in actionType.split(' '):
            self.unitIdxCombobx.addItems([str(id[0]) for id in session.query(Line.idx).all()])
        elif 'zone' in actionType.split(' '):
            self.unitIdxCombobx.addItems([str(id[0]) for id in session.query(Zone.idx).all()])

class plotTrajWindow(QDialog):
    def __init__(self, parent=None):
        super(plotTrajWindow, self).__init__(parent)

        self.setWindowTitle('Trajectories, screenlines and zones')
        self.setGeometry(100, 100, 275, 550)

        self.cur = None
        self.homographyFilename = None
        # self.trjDBFile = None
        self.cameraTypeIdx = None
        self.dateStr = None
        self.traj_line = None
        self.ax = None
        self.figure = plt.figure(tight_layout=True)
        self.canvas = FigureCanvas(self.figure)

        winLayout = QVBoxLayout()
        mdbLayout = QHBoxLayout()
        gridLayout = QGridLayout()
        editLayout = QGridLayout()

        mdbLayout.addWidget(QLabel('Metadata file:'))
        self.mdbFileLedit = QLineEdit()
        mdbLayout.addWidget(self.mdbFileLedit)

        self.openMdbFileBtn = QPushButton()
        self.openMdbFileBtn.setIcon(QIcon('icons/open-file.png'))
        self.openMdbFileBtn.setToolTip('Open configuration file')
        self.openMdbFileBtn.clicked.connect(self.openMdbFile)
        mdbLayout.addWidget(self.openMdbFileBtn)

        gridLayout.addWidget(NavigationToolbar(self.canvas, self, False), 2, 0, 1, 4)#, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Site name:'), 0, 0)#, Qt.AlignRight)
        self.siteNameCombobx = QComboBox()
        # self.siteNameCombobx.setMinimumWidth(120)
        self.siteNameCombobx.currentTextChanged.connect(self.siteChanged)
        gridLayout.addWidget(self.siteNameCombobx, 0, 1)#, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Camera view:'), 0, 2)#, Qt.AlignRight)
        self.camViewCombobx = QComboBox()
        self.camViewCombobx.currentTextChanged.connect(self.viewChanged)
        gridLayout.addWidget(self.camViewCombobx, 0, 3)#, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Traj database:'), 1, 0)#, Qt.AlignRight)
        self.trjDbCombobx = QComboBox()
        # self.trjDbCombobx.setMinimumWidth(130)
        # self.trjDbCombobx.currentTextChanged.connect(self.plotItems)
        gridLayout.addWidget(self.trjDbCombobx, 1, 1, 1, 2)#, Qt.AlignLeft)

        self.plotBtn = QPushButton('Plot')
        self.plotBtn.clicked.connect(self.plotItems)
        # self.plotBtn.setEnabled(False)
        gridLayout.addWidget(self.plotBtn, 1, 3)

        self.prevTrjBtn = QPushButton('<<')
        self.prevTrjBtn.clicked.connect(self.prevTrajectory)
        # self.prevTrjBtn.setEnabled(False)
        editLayout.addWidget(self.prevTrjBtn, 0, 1)

        self.trjIdxLe = QLineEdit('-1')
        self.trjIdxLe.setMinimumWidth(35)
        self.trjIdxLe.setReadOnly(True)
        editLayout.addWidget(self.trjIdxLe, 0, 2)

        self.noTrjLabel = QLabel('/--')
        editLayout.addWidget(self.noTrjLabel, 0, 3)

        self.nextTrjBtn = QPushButton('>>')
        self.nextTrjBtn.clicked.connect(self.nextTrajectory)
        # self.nextTrjBtn.setEnabled(False)
        editLayout.addWidget(self.nextTrjBtn, 0, 4)

        editLayout.addWidget(QLabel('Line index:'), 1, 0)
        self.refLineLe = QLineEdit('--')
        # self.refLineLe.setFixedWidth(50)
        self.refLineLe.setReadOnly(True)
        editLayout.addWidget(self.refLineLe, 1, 1, 1, 4)

        self.delTrjBtn = QPushButton('Delete')
        self.delTrjBtn.clicked.connect(self.delTrajectory)
        # self.delTrjBtn.setEnabled(False)
        editLayout.addWidget(self.delTrjBtn, 1, 5)

        editLayout.addWidget(QLabel('User type:'), 2, 0)
        self.userTypeCb = QComboBox()
        self.userTypeCb.addItems(userTypeNames)
        self.userTypeCb.currentIndexChanged.connect(self.userTypeChanged)
        editLayout.addWidget(self.userTypeCb, 2, 1, 1, 4)

        self.groupSizeCb = QComboBox()
        self.groupSizeCb.addItems(['1', '2', '3', '4', '5', '6'])
        self.groupSizeCb.currentIndexChanged.connect(self.groupSizeChanged)
        editLayout.addWidget(self.groupSizeCb, 2, 5)

        self.saveTrjBtn = QPushButton('Load trajs')
        self.saveTrjBtn.clicked.connect(self.saveTrajectories)
        # self.loadTrjBtn.setEnabled(False)
        editLayout.addWidget(self.saveTrjBtn, 3, 0)

        # winLayout.addWidget(self.toolbar)
        winLayout.addLayout(mdbLayout)
        winLayout.addLayout(gridLayout)
        winLayout.addWidget(self.canvas)
        winLayout.addLayout(editLayout)

        self.setLayout(winLayout)

    def plotItems(self):
        if self.mdbFileLedit.text() == '':
            return

        self.cur.execute(
            'SELECT intrinsicCameraMatrixStr, distortionCoefficientsStr, frameRate FROM camera_types WHERE idx=?',
                         (self.cameraTypeIdx,))
        row = self.cur.fetchall()
        intrinsicCameraMatrixStr = row[0][0]
        distortionCoefficientsStr = row[0][1]
        self.intrinsicCameraMatrix = np.array(ast.literal_eval(intrinsicCameraMatrixStr))
        self.distortionCoefficients = np.array(ast.literal_eval(distortionCoefficientsStr))
        self.frameRate = row[0][2]

        mdbPath = Path(self.mdbFileLedit.text()).parent
        site_folder = mdbPath/self.siteNameCombobx.currentText()
        date_folder = site_folder/self.dateStr
        self.trjDBFile = date_folder/self.trjDbCombobx.currentText()
        self.homoFile = site_folder/self.homographyFilename

        if not self.trjDBFile.exists():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText('The trajectory database does not exist!')
            msg.exec_()
            self.figure.clear()
            self.canvas.draw()
            return

        trjDbName = self.trjDbCombobx.currentText()
        self.cur.execute('SELECT name, startTime From video_sequences WHERE databaseFilename=?',
                         (self.dateStr + '/' + trjDbName,))
        row = self.cur.fetchall()
        video_name = Path(row[0][0])
        video_start_0 = datetime.datetime.strptime(row[0][1], '%Y-%m-%d %H:%M:%S.%f')
        self.video_start = video_start_0.replace(microsecond=0)

        video_file = site_folder/video_name
        if video_file.exists():
            self.parent().parent().videoFile = str(video_file)
            self.parent().parent().openVideoFile()
        else:
            QMessageBox.information(self, 'Error!', 'The corresponding video file does not exist!')
            return

        if not self.homoFile.exists():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText('The homography file does not exist!')
            msg.exec_()
            self.figure.clear()
            self.canvas.draw()
            return

        self.figure.clear()
        self.canvas.draw()

        self.ax = self.figure.add_subplot(111)

        self.traj_line = plotTrajectory(self.trjDBFile, self.intrinsicCameraMatrix, self.distortionCoefficients,
                                       self.homoFile, self.ax, session)
        for tl in self.traj_line:
            tl.append([-1, [], [], [], [], 1])
            #[userType, [screenLineIdxs], [crossingInstants], [speeds], [secs], groupSize]
        self.noTrjLabel.setText('/' + str(len(self.traj_line) - 1))
        self.trjIdxLe.setText('-1')
        self.userTypeCb.setCurrentIndex(-1)
        self.refLineLe.setText('--')
        self.canvas.draw()

    def nextTrajectory(self):
        if self.traj_line == None:
            return
        q_line = session.query(Line)
        if q_line.all() == []:
            QMessageBox.information(self, 'Warning!', 'At least one screenline is required!')
            return

        current_idx = int(self.trjIdxLe.text())
        if current_idx == len(self.traj_line) -1:
            return
        if current_idx == -1:
            for line in [tl[1] for tl in self.traj_line]:
                line.set_visible(False)

        current_line = self.traj_line[current_idx][1]
        current_line.set_visible(False)

        next_idx = current_idx + 1
        self.trjIdxLe.setText(str(next_idx))
        next_traj = self.traj_line[next_idx][0]
        next_line = self.traj_line[next_idx][1]
        next_line.set_visible(True)
        self.userTypeCb.setCurrentIndex(next_traj.userType)
        self.groupSizeCb.setCurrentIndex(self.traj_line[next_idx][2][5] - 1)
        self.canvas.draw()

        if self.traj_line[next_idx][2][0] == -1:
            self.traj_line[next_idx][2][0] = next_traj.userType
            homography = np.loadtxt(self.homoFile, delimiter=' ')
            for line in q_line.all():
                points = np.array([[line.points[0].x, line.points[1].x],
                                   [line.points[0].y, line.points[1].y]])
                prj_points = imageToWorldProject(points, self.intrinsicCameraMatrix, self.distortionCoefficients,
                                                 homography)
                p1 = moving.Point(prj_points[0][0], prj_points[1][0])
                p2 = moving.Point(prj_points[0][1], prj_points[1][1])

                instants_list = next_traj.getInstantsCrossingLane(p1, p2)
                if len(instants_list) > 0:
                    secs = instants_list[0] / self.frameRate
                    instant = self.video_start + datetime.timedelta(seconds=round(secs))
                    speed = round(next_traj.getVelocityAtInstant(int(instants_list[0]))
                                  .norm2() * self.frameRate * 3.6, 1)  # km/h

                    self.traj_line[next_idx][2][1].append(line)
                    self.traj_line[next_idx][2][2].append(instant)
                    self.traj_line[next_idx][2][3].append(speed)
                    self.traj_line[next_idx][2][4].append(secs)
                    # screenLine_Id = str(line.idx)
            if self.traj_line[next_idx][2][1] == []:
                secs = (next_traj.getLastInstant() / self.frameRate)
                # self.traj_line[next_idx][2][1].append('None')
                self.traj_line[next_idx][2][4].append(secs)

        self.parent().parent().mediaPlayer.setPosition(round(self.traj_line[next_idx][2][4][0]*1000))
        if self.traj_line[next_idx][2][1] == []:
            self.refLineLe.setText('None')
        else:
            self.refLineLe.setText(str(self.traj_line[next_idx][2][1][0].idx))

    def prevTrajectory(self):
        if self.traj_line == None:
            return
        current_idx = int(self.trjIdxLe.text())
        if current_idx == -1:
            return
        prev_idx = current_idx - 1
        if current_idx == 0:
            for line in [tl[1] for tl in self.traj_line]:
                line.set_visible(True)
            self.trjIdxLe.setText(str(prev_idx))
            self.canvas.draw()
            return

        current_line = self.traj_line[current_idx][1]
        current_line.set_visible(False)

        self.trjIdxLe.setText(str(prev_idx))
        prev_traj = self.traj_line[prev_idx][0]
        prev_line = self.traj_line[prev_idx][1]
        prev_line.set_visible(True)
        self.userTypeCb.setCurrentIndex(prev_traj.userType)
        self.groupSizeCb.setCurrentIndex(self.traj_line[prev_idx][2][5] - 1)
        self.canvas.draw()

        homography = np.loadtxt(self.homoFile, delimiter=' ')
        q_line = session.query(Line)
        if q_line.all() != []:
            for line in q_line.all():
                points = np.array([[line.points[0].x, line.points[1].x],
                                   [line.points[0].y, line.points[1].y]])
                prj_points = imageToWorldProject(points, self.intrinsicCameraMatrix, self.distortionCoefficients,
                                                 homography)
                p1 = moving.Point(prj_points[0][0], prj_points[1][0])
                p2 = moving.Point(prj_points[0][1], prj_points[1][1])

                instants_list = prev_traj.getInstantsCrossingLane(p1, p2)
                if len(instants_list) > 0:
                    mil_secs = int((instants_list[0] / self.frameRate) * 1000)
                    self.refLineLe.setText(str(line.idx))
                    break
            if len(instants_list) == 0:
                mil_secs = int((prev_traj.getFirstInstant() / self.frameRate) * 1000)
                self.refLineLe.setText('None')
        else:
            mil_secs = int((prev_traj.getFirstInstant() / self.frameRate) * 1000)
            self.refLineLe.setText('None')

        self.parent().parent().mediaPlayer.setPosition(mil_secs)

    def delTrajectory(self):
        delete_idx = int(self.trjIdxLe.text())
        delete_line = self.traj_line[delete_idx][1]
        if delete_idx == -1:
            return
        msg = QMessageBox()
        rep = msg.question(self, 'Delete trajectory',
                           'Are you sure to DELETE the current trajectory?', msg.Yes | msg.No)
        if rep == msg.No:
            return

        self.prevTrajectory()
        self.traj_line.pop(delete_idx)
        self.ax.lines.remove(delete_line)
        self.noTrjLabel.setText('/' + str(len(self.traj_line) - 1))

    def saveTrajectories(self):
        if self.mdbFileLedit.text() == '':
            return

        msg = QMessageBox()
        rep = msg.question(self, 'Load trajectory',
                           'Are you sure to LOAD all trajectories to database?', msg.Yes | msg.No)
        if rep == msg.No:
            return

        streetUserObjects = []
        no_users = 0
        for trj_idx in range(len(self.traj_line)):
            userType = self.traj_line[trj_idx][2][0]
            lines = self.traj_line[trj_idx][2][1]
            if userType != -1 and userType != 0 and lines != []:
                instants = self.traj_line[trj_idx][2][2]
                speeds = self.traj_line[trj_idx][2][3]
                groupSize = self.traj_line[trj_idx][2][5]
                streetUserObjects = streetUserObjects + creatStreetusers(userType, lines, instants, speeds, groupSize)
                no_users += 1

        session.add_all(streetUserObjects)
        session.commit()
        session.close()

        QMessageBox.information(self, 'Import!', 'No. of imported street users: {}'.format(no_users))


    def userTypeChanged(self):
        current_idx = int(self.trjIdxLe.text())
        if current_idx == -1:
            return
        user_indx = self.userTypeCb.currentIndex()
        current_traj = self.traj_line[current_idx][0]

        if user_indx != current_traj.userType:
            current_line = self.traj_line[current_idx][1]
            current_traj.setUserType(user_indx)
            self.traj_line[current_idx][2][0] = user_indx
            current_line.set_label(userTypeNames[user_indx])
            current_line.set_color(userTypeColors[user_indx])
            self.canvas.draw()

    def groupSizeChanged(self):
        current_idx = int(self.trjIdxLe.text())
        if current_idx == -1:
            return
        self.traj_line[current_idx][2][5] = int(self.groupSizeCb.currentText())

    def openMdbFile(self):
        mdbFilename, _ = QFileDialog.getOpenFileName(self, "Open metadata file",
                                                     QDir.homePath(), "Sqlite files (*.sqlite)")
        if mdbFilename == '':
            return

        self.mdbFileLedit.setText(mdbFilename)

        con = sqlite3.connect(self.mdbFileLedit.text())
        self.cur = con.cursor()

        # Check if database is a metadata file
        self.cur.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='video_sequences' ''')
        if self.cur.fetchone()[0] == 0:
            QMessageBox.information(self, 'Error!',
                                    'The selected database is NOT a metadata file! Select a proper file.')
            self.mdbFileLedit.clear()
            return

        self.cur.execute('SELECT name FROM sites')
        sites = self.cur.fetchall()
        self.siteNameCombobx.clear()
        self.siteNameCombobx.addItems([s[0] for s in sites])
        # self.siteNameCombobx.setCurrentIndex(-1)

    def siteChanged(self):
        if self.siteNameCombobx.currentText() == '':
            return
        self.cur.execute('SELECT idx FROM sites WHERE name=?', (self.siteNameCombobx.currentText(),))
        siteIdx = self.cur.fetchall()[0][0]
        self.cur.execute('SELECT description FROM camera_views WHERE siteIdx=?', (siteIdx,))
        views = self.cur.fetchall()
        self.camViewCombobx.clear()
        self.camViewCombobx.addItems([v[0] for v in views])
        # self.camViewCombobx.setCurrentIndex(-1)

    def viewChanged(self):
        if self.camViewCombobx.currentText() == '':
            return
        self.cur.execute('SELECT idx FROM sites WHERE name=?', (self.siteNameCombobx.currentText(),))
        siteIdx = self.cur.fetchall()[0][0]
        self.cur.execute('SELECT idx, homographyFilename, cameraTypeIdx FROM camera_views WHERE description =? AND siteIdx=?',
                         (self.camViewCombobx.currentText(), siteIdx))
        row = self.cur.fetchall()
        viewIdx = row[0][0]
        self.homographyFilename = row[0][1]
        self.cameraTypeIdx = row[0][2]
        self.cur.execute('SELECT databaseFilename FROM video_sequences WHERE cameraViewIdx=?', (viewIdx,))
        trjDbs = self.cur.fetchall()
        self.trjDbCombobx.clear()
        self.trjDbCombobx.addItems([t[0].split('/')[-1] for t in trjDbs])
        # self.trjDbCombobx.setCurrentIndex(-1)
        self.dateStr = trjDbs[0][0].split('/')[0]



class importTrajWindow(QDialog):
    def __init__(self, parent=None):
        super(importTrajWindow, self).__init__(parent)

        self.cur = None
        self.homographyFilename = None
        self.cameraTypeIdx = None
        self.dateStr = None

        self.setWindowTitle('Import trajectories')

        winLayout = QVBoxLayout()
        mdbLayout = QHBoxLayout()
        gridLayout = QGridLayout()

        mdbLayout.addWidget(QLabel('Metadata file:'))
        self.mdbFileLedit = QLineEdit()
        mdbLayout.addWidget(self.mdbFileLedit)

        self.openMdbFileBtn = QPushButton()
        self.openMdbFileBtn.setIcon(QIcon('icons/open-file.png'))
        self.openMdbFileBtn.setToolTip('Open configuration file')
        self.openMdbFileBtn.clicked.connect(self.openMdbFile)
        mdbLayout.addWidget(self.openMdbFileBtn)

        gridLayout.addWidget(QLabel('Site name:'), 0, 0, Qt.AlignRight)
        self.siteNameCombobx = QComboBox()
        # self.siteNameCombobx.setMinimumWidth(120)
        self.siteNameCombobx.currentTextChanged.connect(self.siteChanged)
        gridLayout.addWidget(self.siteNameCombobx, 0, 1)#, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Camera view:'), 0, 2, Qt.AlignRight)
        self.camViewCombobx = QComboBox()
        self.camViewCombobx.currentTextChanged.connect(self.viewChanged)
        gridLayout.addWidget(self.camViewCombobx, 0, 3)#, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Trajectory database:'), 1, 0, Qt.AlignRight)
        self.trjDbCombobx = QComboBox()
        # self.trjDbCombobx.setMinimumWidth(130)
        # self.trjDbCombobx.currentTextChanged.connect(self.plotItems)
        gridLayout.addWidget(self.trjDbCombobx, 1, 1, 1, 2)#, Qt.AlignLeft)

        self.importBtn = QPushButton('Import')
        self.importBtn.clicked.connect(self.importTrajs)
        # self.importBtn.setEnabled(False)
        gridLayout.addWidget(self.importBtn, 1, 3)

        self.summary_list_wdgt = QListWidget()
        gridLayout.addWidget(self.summary_list_wdgt, 2, 0, 1, 4)

        self.closeBtn = QPushButton('Close')
        self.closeBtn.clicked.connect(self.closeImportWin)
        gridLayout.addWidget(self.closeBtn, 3, 0, 1, 4)


        winLayout.addLayout(mdbLayout)
        winLayout.addLayout(gridLayout)

        self.setLayout(winLayout)


    def importTrajs(self):
        if self.mdbFileLedit.text() == '':
            return

        self.thread = QThread()
        self.worker = Worker(self.cameraTypeIdx, self.dateStr, self.homographyFilename, self.mdbFileLedit,
                             self.siteNameCombobx, self.trjDbCombobx)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.progress.connect(self.reportProgress)
        self.thread.start()

        self.closeBtn.setText('Processing ...')
        self.importBtn.setEnabled(False)
        self.closeBtn.setEnabled(False)

        self.thread.finished.connect(lambda: self.closeBtn.setText('Close'))
        self.thread.finished.connect(lambda: self.importBtn.setEnabled(True))
        self.thread.finished.connect(lambda: self.closeBtn.setEnabled(True))


        # self.importBtn.setText('Processing ...')
        # self.importBtn.setEnabled(False)
        #
        # self.cur.execute(
        #     'SELECT frameRate, intrinsicCameraMatrixStr, distortionCoefficientsStr FROM camera_types WHERE idx=?',
        #                  (self.cameraTypeIdx,))
        # row = self.cur.fetchall()
        # frameRate = row[0][0]
        # intrinsicCameraMatrixStr = row[0][1]
        # distortionCoefficientsStr = row[0][2]
        # intrinsicCameraMatrix = np.array(ast.literal_eval(intrinsicCameraMatrixStr))
        # distortionCoefficients = np.array(ast.literal_eval(distortionCoefficientsStr))
        #
        # mdbPath = Path(self.mdbFileLedit.text()).parent
        #
        # homoFile = mdbPath / self.siteNameCombobx.currentText() / self.homographyFilename
        #
        # if self.trjDbCombobx.currentText() == '--All databases--':
        #     for trjDbName in [self.trjDbCombobx.itemText(i) for i in range(1, self.trjDbCombobx.count())]:
        #         trjDBFile = mdbPath / self.siteNameCombobx.currentText() / self.dateStr / trjDbName
        #         self.cur.execute('SELECT startTime From video_sequences WHERE databaseFilename=?',
        #                          (self.dateStr + '/' + trjDbName,))
        #         row = self.cur.fetchall()
        #         video_start = datetime.datetime.strptime(row[0][0], '%Y-%m-%d %H:%M:%S.%f')
        #         video_start = video_start.replace(microsecond=0)
        #         log = importTrajectory(trjDBFile, intrinsicCameraMatrix, distortionCoefficients, homoFile,
        #                                video_start, frameRate, session)
        #         self.reportProgress(log, trjDbName)
        # else:
        #     trjDBFile = mdbPath / self.siteNameCombobx.currentText() / self.dateStr / self.trjDbCombobx.currentText()
        #     self.cur.execute('SELECT startTime From video_sequences WHERE databaseFilename=?',
        #                      (self.dateStr + '/' + self.trjDbCombobx.currentText(),))
        #     row = self.cur.fetchall()
        #     video_start = datetime.datetime.strptime(row[0][0], '%Y-%m-%d %H:%M:%S.%f')
        #     video_start = video_start.replace(microsecond=0)
        #     log = importTrajectory(trjDBFile, intrinsicCameraMatrix, distortionCoefficients, homoFile,
        #                                video_start, frameRate, session)
        #     self.reportProgress(log, self.trjDbCombobx.currentText())
        # self.importBtn.setText('Import')
        # self.importBtn.setEnabled(True)


    def openMdbFile(self):
        mdbFilename, _ = QFileDialog.getOpenFileName(self, "Open metadata file",
                                                     QDir.homePath(), "Sqlite files (*.sqlite)")
        if mdbFilename == '':
            return

        self.mdbFileLedit.setText(mdbFilename)

        con = sqlite3.connect(self.mdbFileLedit.text())
        self.cur = con.cursor()

        # Check if database is a metadata file
        self.cur.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='video_sequences' ''')
        if self.cur.fetchone()[0] == 0:
            QMessageBox.information(self, 'Error!', 'The selected database is NOT a metadata file! Select a proper file.')
            self.mdbFileLedit.clear()
            return

        self.cur.execute('SELECT name FROM sites')
        sites = self.cur.fetchall()
        self.siteNameCombobx.clear()
        self.siteNameCombobx.addItems([s[0] for s in sites])
        # self.siteNameCombobx.setCurrentIndex(-1)

    def siteChanged(self):
        if self.siteNameCombobx.currentText() == '':
            return
        self.cur.execute('SELECT idx FROM sites WHERE name=?', (self.siteNameCombobx.currentText(),))
        siteIdx = self.cur.fetchall()[0][0]
        self.cur.execute('SELECT description FROM camera_views WHERE siteIdx=?', (siteIdx,))
        views = self.cur.fetchall()
        self.camViewCombobx.clear()
        self.camViewCombobx.addItems([v[0] for v in views])
        # self.camViewCombobx.setCurrentIndex(-1)

    def viewChanged(self):
        if self.camViewCombobx.currentText() == '':
            return
        self.cur.execute('SELECT idx FROM sites WHERE name=?', (self.siteNameCombobx.currentText(),))
        siteIdx = self.cur.fetchall()[0][0]
        self.cur.execute('SELECT idx, homographyFilename, cameraTypeIdx FROM camera_views WHERE description =? AND siteIdx=?',
                         (self.camViewCombobx.currentText(), siteIdx))
        row = self.cur.fetchall()
        viewIdx = row[0][0]
        self.homographyFilename = row[0][1]
        self.cameraTypeIdx = row[0][2]
        self.cur.execute('SELECT databaseFilename FROM video_sequences WHERE cameraViewIdx=?', (viewIdx,))
        trjDbs = self.cur.fetchall()
        self.trjDbCombobx.clear()
        trjList = [t[0].split('/')[-1] for t in trjDbs]
        trjList.insert(0, '--All databases--')
        self.trjDbCombobx.addItems(trjList)
        # self.trjDbCombobx.setCurrentIndex(-1)
        self.dateStr = trjDbs[0][0].split('/')[0]

    def closeImportWin(self):
        self.close()

    def reportProgress(self, log, trjDbName):
        self.summary_list_wdgt.addItem(trjDbName + ':')
        for key, val in log.items():
            self.summary_list_wdgt.addItem('    - {}:  {}'.format(key, val))
        self.summary_list_wdgt.addItem('--------------------')

class Worker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(dict, str)

    def __init__(self, cameraTypeIdx, dateStr, homographyFilename, mdbFileLedit, siteNameCombobx, trjDbCombobx):
        super().__init__()
        self.cameraTypeIdx = cameraTypeIdx
        self.dateStr = dateStr
        self.homographyFilename = homographyFilename
        self.mdbFileLedit = mdbFileLedit
        self.siteNameCombobx = siteNameCombobx
        self.trjDbCombobx = trjDbCombobx
        self.cur = None

    def run(self):
        con = sqlite3.connect(self.mdbFileLedit.text())
        self.cur = con.cursor()
        self.cur.execute(
            'SELECT frameRate, intrinsicCameraMatrixStr, distortionCoefficientsStr FROM camera_types WHERE idx=?',
            (self.cameraTypeIdx,))
        row = self.cur.fetchall()
        frameRate = row[0][0]
        intrinsicCameraMatrixStr = row[0][1]
        distortionCoefficientsStr = row[0][2]
        intrinsicCameraMatrix = np.array(ast.literal_eval(intrinsicCameraMatrixStr))
        distortionCoefficients = np.array(ast.literal_eval(distortionCoefficientsStr))

        mdbPath = Path(self.mdbFileLedit.text()).parent

        homoFile = mdbPath / self.siteNameCombobx.currentText() / self.homographyFilename

        if self.trjDbCombobx.currentText() == '--All databases--':
            for trjDbName in [self.trjDbCombobx.itemText(i) for i in range(1, self.trjDbCombobx.count())]:
                trjDBFile = mdbPath / self.siteNameCombobx.currentText() / self.dateStr / trjDbName
                self.cur.execute('SELECT startTime From video_sequences WHERE databaseFilename=?',
                                 (self.dateStr + '/' + trjDbName,))
                row = self.cur.fetchall()
                video_start = datetime.datetime.strptime(row[0][0], '%Y-%m-%d %H:%M:%S.%f')
                video_start = video_start.replace(microsecond=0)
                log = importTrajectory(trjDBFile, intrinsicCameraMatrix, distortionCoefficients, homoFile,
                                       video_start, frameRate, session)
                self.progress.emit(log, trjDbName)
        else:
            trjDBFile = mdbPath / self.siteNameCombobx.currentText() / self.dateStr / self.trjDbCombobx.currentText()
            self.cur.execute('SELECT startTime From video_sequences WHERE databaseFilename=?',
                             (self.dateStr + '/' + self.trjDbCombobx.currentText(),))
            row = self.cur.fetchall()
            video_start = datetime.datetime.strptime(row[0][0], '%Y-%m-%d %H:%M:%S.%f')
            video_start = video_start.replace(microsecond=0)
            log = importTrajectory(trjDBFile, intrinsicCameraMatrix, distortionCoefficients, homoFile,
                                   video_start, frameRate, session)
            self.progress.emit(log, self.trjDbCombobx.currentText())
        self.finished.emit()



class dfTableModel(QAbstractTableModel):

    def __init__(self, data, n_data=None, cmap='Wistia'):
        QAbstractTableModel.__init__(self)
        self._data = data
        self.norm_data = n_data
        self.cmap = matplotlib.cm.get_cmap(cmap)

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parnet=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid():
            if role == Qt.DisplayRole:
                return str(self._data.iloc[index.row(), index.column()])
            if role == Qt.TextAlignmentRole:
                return Qt.AlignCenter
            if role == Qt.BackgroundRole:
                value = str(self._data.iloc[index.row(), index.column()])
                if value[0] == '-':
                    return QColor(255, 204, 204)
                elif value[0] == '+':
                    return QColor(204, 255, 204)
                elif value[0:3] == '0 [' or value[0:5] == '0.0 [':
                    return QColor(255, 255, 204)
                elif value[0] == 'x':
                    return QColor(244, 244, 244)

                if not self.norm_data is None and index.column() > 0:
                    norm_val = self.norm_data.iloc[index.row(), index.column()]
                    if norm_val != None:
                        rgba = self.cmap(norm_val)
                        c = QColor()
                        c.setRedF(rgba[0])
                        c.setGreenF(rgba[1])
                        c.setBlueF(rgba[2])
                        return c

            if role == Qt.FontRole:
                if index.column() == 0:
                    font = QFont()
                    font.setBold(True)
                    return font
        return None

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._data.columns[section]
        if orientation == Qt.Vertical and role == Qt.DisplayRole:
            return self._data.index[section]
        return None


if __name__ == '__main__':
    app = QApplication(sys.argv)

    obsTb = ObsToolbox()
    obsTb.show()

    sys.exit(app.exec_())