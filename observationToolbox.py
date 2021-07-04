import sys
import os
import pandas as pd
import numpy as np
import datetime
import sqlite3
import ast
from pathlib import Path
from configparser import ConfigParser
from PyQt5.QtWidgets import (QApplication, QWidget, QGridLayout, QVBoxLayout, QHBoxLayout,
                             QToolBox, QPushButton, QTextEdit, QLineEdit, QMainWindow,
                             QComboBox, QGroupBox, QDateTimeEdit, QAction, QStyle,
                             QFileDialog, QToolBar, QMessageBox, QDialog, QLabel,
                             QSizePolicy, QStatusBar, QTableWidget, QHeaderView, QTableWidgetItem,
                             QAbstractItemView, QTableView, QListWidget)
from PyQt5.QtGui import QColor, QIcon, QFont
from PyQt5.QtCore import QDateTime, QSize, QDir, Qt, QAbstractTableModel, QObject, QThread, pyqtSignal

from iframework import createDatabase, connectDatabase, Person, Mode, Group, GroupBelonging, Vehicle,\
    Activity, LinePassing, ZonePassing, Point, Line, Zone

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt

from indicators import tempDistHist, stackedHist, odMatrix, pieChart, generateReport, \
    calculateNoBins, getPeakHours, getObsStartEnd, compareIndicators, calculateBinsEdges, \
    plotTrajectory, importTrajectory
import iframework
from trafficintelligence.storage import ProcessParameters

from sqlalchemy import Enum, Boolean, DateTime
from sqlalchemy.inspection import inspect
from sqlalchemy import func

session = None

config_object = ConfigParser()
cfg = config_object.read("config.ini")
actionTypeList = ['passing line', 'entering zone', 'exiting zone', 'passing zone',
                  'dwelling zone']

class ObsToolbox(QMainWindow):
    def __init__(self, parent=None):
        super(ObsToolbox, self).__init__(parent)
        self.resize(400, 650)
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.person = None
        self.groupPersons = {}
        self.group = None

        global session
        self.dbFilename = '/Users/Abbas/AAAA/Stuart2019_iframework.sqlite'

        layout = QVBoxLayout() #QGridLayout()

        #--------------------------------------------
        self.setWindowTitle(os.path.basename(self.dbFilename))

        session = createDatabase(self.dbFilename)

        if session is None:
            session = connectDatabase(self.dbFilename)
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
                                QToolBox::tab {
                                    font: bold;
                                    color: darkblue;
                                }
                                QToolBox{ icon-size: 24px; }
                             """

        self.toolbox = QToolBox()
        self.toolbox.setStyleSheet(styleSheet)
        layout.addWidget(self.toolbox)#, 0, 0)

        self.openAction = QAction(QIcon('icons/database.png'), '&Open database file', self)
        self.openAction.setShortcut('Ctrl+O')
        self.openAction.setStatusTip('Open database file')
        self.openAction.triggered.connect(self.opendbFile)

        tempHistAction = QAction(QIcon('icons/histogram.png'), '&Temporal Histogram', self)
        # openAction.setShortcut('Ctrl+O')
        # openAction.setStatusTip('Open database file')
        tempHistAction.triggered.connect(self.tempHist)

        stackHistAction = QAction(QIcon('icons/stacked.png'), '&Stacked Histogram', self)
        stackHistAction.triggered.connect(self.stackedHist)

        odMatrixAction = QAction(QIcon('icons/grid.png'), '&OD Matrix', self)
        odMatrixAction.triggered.connect(self.odMatrix)

        pieChartAction = QAction(QIcon('icons/pie-chart.png'), '&Pie Chart', self)
        pieChartAction.triggered.connect(self.pieChart)

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
        self.toolbar.addAction(stackHistAction)
        self.toolbar.addAction(odMatrixAction)
        self.toolbar.addAction(pieChartAction)
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

        self.user_newGroupButton = QPushButton(QIcon('icons/group.png'), 'New group')
        self.user_newGroupButton.clicked.connect(self.user_newGroup_click)
        user_newBtnsLayout.addWidget(self.user_newGroupButton)
        self.user_newRecButton = QPushButton(QIcon('icons/person.png'), 'New user')
        self.user_newRecButton.setEnabled(False)
        self.user_newRecButton.clicked.connect(self.user_newRecBtn_click)
        user_newBtnsLayout.addWidget(self.user_newRecButton)
        user_tab_layout.addLayout(user_newBtnsLayout)

        # ----------------- PERSON groupPersons box --------------------------
        self.person_grpBox = self.generateWidgets(Person, 'All', True)
        user_tab_layout.addWidget(self.person_grpBox)

        # ----------------- VEHICLE -------------------------
        self.veh_grpBox = self.generateWidgets(Vehicle, 'NoPrFo', True)
        user_tab_layout.addWidget(self.veh_grpBox)

        # ----------- MODE groupPersons box --------------
        self.mode_grpBox = self.generateWidgets(Mode, 'NoPrFo', False)
        user_tab_layout.addWidget(self.mode_grpBox)

        # ----------- GROUP groupPersons box -------------
        self.group_grpBox = QGroupBox('Group')
        # group_grpBox_wdgt = QWidget()
        # group_grpBox_wdgt.setEnabled(False)
        group_grpBox_layout = QVBoxLayout()
        # group_grid_layout = QVBoxLayout()
        group_newBtnsLayout = QHBoxLayout()
        group_saveBtnsLayout = QHBoxLayout()

        self.group_addToListButton = QPushButton(QIcon('icons/new.png'), 'Add user to list')
        self.group_addToListButton.clicked.connect(self.group_AddToList_click)
        # group_newBtnsLayout.addWidget(self.group_addToListButton)
        # group_grid_layout.addLayout(group_newBtnsLayout)
        group_grpBox_layout.addWidget(self.group_addToListButton)

        self.group_list_wdgt = QListWidget()
        # group_grid_layout.addWidget(self.group_list_wdgt)
        group_grpBox_layout.addWidget(self.group_list_wdgt)

        # group_grpBox_wdgt.setLayout(group_grid_layout)
        # group_grpBox_layout.addWidget(group_grpBox_wdgt)
        self.group_grpBox.setLayout(group_grpBox_layout)
        self.group_grpBox.setEnabled(False)

        user_tab_layout.addWidget(self.group_grpBox)

        # ------- ROAD USER save buttons --------------
        self.user_saveButton = QPushButton(QIcon('icons/save.png'), 'Make group and save user(s)')
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
        linepass_saveBtnsLayout = QHBoxLayout()

        self.linepass_newRecButton = QPushButton(QIcon('icons/new.png'), 'New line passing')
        self.linepass_newRecButton.clicked.connect(self.linepass_newRecBtn_click)

        linepass_newBtnsLayout.addWidget(self.linepass_newRecButton)
        linepass_tab_layout.addLayout(linepass_newBtnsLayout)

        self.linepass_grpBox = self.generateWidgets(LinePassing, 'NoPrFo', False)
        linepass_tab_layout.addWidget(self.linepass_grpBox)

        self.linepass_saveButton = QPushButton(QIcon('icons/save.png'), 'Save line passing')
        self.linepass_saveButton.clicked.connect(self.linepass_saveBtn_click)
        self.linepass_saveButton.setEnabled(False)
        linepass_saveBtnsLayout.addWidget(self.linepass_saveButton)
        linepass_tab_layout.addLayout(linepass_saveBtnsLayout)

        linepass_tab_wdgt.setLayout(linepass_tab_layout)
        self.toolbox.addItem(linepass_tab_wdgt, QIcon('icons/linePassing.png'), 'Line Passing')

        # ------------------ ZonePassing tab --------------------------
        zonepass_tab_wdgt = QWidget()
        zonepass_tab_layout = QVBoxLayout()
        zonepass_newBtnsLayout = QHBoxLayout()
        zonepass_saveBtnsLayout = QHBoxLayout()

        self.zonepass_newRecButton = QPushButton(QIcon('icons/new.png'), 'New zone passing')
        self.zonepass_newRecButton.clicked.connect(self.zonepass_newRecBtn_click)
        zonepass_newBtnsLayout.addWidget(self.zonepass_newRecButton)
        zonepass_tab_layout.addLayout(zonepass_newBtnsLayout)

        self.zonepass_grpBox = self.generateWidgets(ZonePassing, 'NoPrFo', False)
        zonepass_tab_layout.addWidget(self.zonepass_grpBox)

        self.zonepass_saveButton = QPushButton(QIcon('icons/save.png'), 'Save zone passing')
        self.zonepass_saveButton.clicked.connect(self.zonepass_saveBtn_click)
        self.zonepass_saveButton.setEnabled(False)
        zonepass_saveBtnsLayout.addWidget(self.zonepass_saveButton)
        zonepass_tab_layout.addLayout(zonepass_saveBtnsLayout)

        zonepass_tab_wdgt.setLayout(zonepass_tab_layout)
        self.toolbox.addItem(zonepass_tab_wdgt, QIcon('icons/zonePassing.png'), 'Zone Passing')

        # ------------------ Activity tab --------------------------
        act_tab_wdgt = QWidget()
        act_tab_layout = QVBoxLayout()
        act_newBtnsLayout = QHBoxLayout()
        act_saveBtnsLayout = QHBoxLayout()

        self.act_newRecButton = QPushButton(QIcon('icons/new.png'), 'New activity')
        self.act_newRecButton.clicked.connect(self.act_newRecBtn_click)
        act_newBtnsLayout.addWidget(self.act_newRecButton)
        act_tab_layout.addLayout(act_newBtnsLayout)

        self.act_grpBox = self.generateWidgets(Activity, 'NoPrFo', False)
        act_tab_layout.addWidget(self.act_grpBox)

        self.act_saveButton = QPushButton(QIcon('icons/save.png'), 'Save activity')
        self.act_saveButton.clicked.connect(self.act_saveBtn_click)
        self.act_saveButton.setEnabled(False)
        act_saveBtnsLayout.addWidget(self.act_saveButton)
        act_tab_layout.addLayout(act_saveBtnsLayout)

        act_tab_wdgt.setLayout(act_tab_layout)
        self.toolbox.addItem(act_tab_wdgt, QIcon('icons/activity.png'), 'Activity')

        # -------- Create a widget for window contents --------
        wid = QWidget(self)
        self.setCentralWidget(wid)

        # --------- Set widget to contain window contents -----
        wid.setLayout(layout)

    # ============== Buttons click functions ==============
    #--------------- Road user buttons --------------------
    def user_newGroup_click(self):
        self.user_newGroupButton.setEnabled(False)
        self.user_newRecBtn_click()
        self.group_list_wdgt.clear()
        self.groupPersons = {}
        self.group = None

    def user_newRecBtn_click(self):

        self.person_grpBox.setEnabled(True)
        self.veh_grpBox.setEnabled(True)
        self.mode_grpBox.setEnabled(True)
        self.group_grpBox.setEnabled(True)

        self.user_saveButton.setEnabled(True)
        self.group_addToListButton.setEnabled(True)
        self.user_newRecButton.setEnabled(False)

        self.init_input_widgets(self.mode_grpBox)

        self.person = Person()
        session.add(self.person)
        session.flush()

        self.person_grpBox.layout().itemAtPosition(0, 1).widget().setText(str(self.person.idx))


    def user_saveBtn_click(self):
        if self.groupPersons == {}:
            QMessageBox.information(self, 'Error!', 'There is no person in the list!')
            return

        self.person_grpBox.setEnabled(False)
        self.veh_grpBox.setEnabled(False)
        self.mode_grpBox.setEnabled(False)
        self.group_grpBox.setEnabled(False)

        self.user_saveButton.setEnabled(False)
        self.user_newGroupButton.setEnabled(True)
        self.user_newRecButton.setEnabled(False)

        self.group = Group(self.groupPersons.values())

        session.commit()

    # ------------------- Group Buttons --------------
    def group_AddToList_click(self):
        self.person_grpBox.setEnabled(False)
        self.veh_grpBox.setEnabled(False)
        self.mode_grpBox.setEnabled(False)

        self.group_addToListButton.setEnabled(False)
        self.user_newRecButton.setEnabled(True)

        if self.person_grpBox.isChecked():
            person_layout = self.person_grpBox.layout()
            self.person.age = person_layout.itemAtPosition(1, 1).widget().text()
            self.person.gender = person_layout.itemAtPosition(2, 1).widget().currentText()
            self.person.disability = person_layout.itemAtPosition(3, 1).widget().text()
            self.person.stroller = self.toBool(person_layout.itemAtPosition(4, 1).widget().currentText())
            self.person.bag = self.toBool(person_layout.itemAtPosition(5, 1).widget().currentText())
            self.person.animal = self.toBool(person_layout.itemAtPosition(6, 1).widget().currentText())

        if self.veh_grpBox.isChecked():
            vehicle_layout = self.veh_grpBox.layout()
            category = vehicle_layout.itemAtPosition(0, 1).widget().currentText()
            trailer = self.toBool(vehicle_layout.itemAtPosition(1, 1).widget().currentText())
            vehicle = Vehicle(category=category, trailer=trailer)
        else:
            vehicle = None

        mode_layout = self.mode_grpBox.layout()
        transport = mode_layout.itemAtPosition(0, 1).widget().currentText()
        startTime_wdgt = mode_layout.itemAtPosition(1, 1).widget()
        input_wdgt_val = startTime_wdgt.dateTime().toPyDateTime()
        startTime = input_wdgt_val.replace(microsecond=0)
        self.mode = Mode(transport=transport, person=self.person, vehicle=vehicle, startTime=None)

        if not self.person.idx in self.groupPersons.keys():
            self.groupPersons[self.person.idx] = self.person
            self.group_list_wdgt.addItem(str(self.person.idx))

    # -------------- LinePassing buttons ------------------
    def linepass_newRecBtn_click(self):
        if self.group is None:
            QMessageBox.information(self, 'Error!', 'No user group is defined or saved!')
            return
        self.linepass_grpBox.setEnabled(True)

        self.linepass_saveButton.setEnabled(True)
        self.linepass_newRecButton.setEnabled(False)

        self.init_input_widgets(self.linepass_grpBox)

    def linepass_saveBtn_click(self):
        self.linepass_grpBox.setEnabled(False)

        self.linepass_saveButton.setEnabled(False)
        self.linepass_newRecButton.setEnabled(True)

        linepass_layout = self.linepass_grpBox.layout()
        lineIdx = linepass_layout.itemAtPosition(0, 1).widget().currentText()
        line = session.query(Line).filter(Line.idx == lineIdx).first()
        instant_wdgt = linepass_layout.itemAtPosition(2, 1).widget()
        input_wdgt_val = instant_wdgt.dateTime().toPyDateTime()
        instant = input_wdgt_val.replace(microsecond=0)
        speed_text = linepass_layout.itemAtPosition(3, 1).widget().text()
        if speed_text != '':
            speed = float(speed_text)
        else:
            speed = None
        wrongDirection = self.toBool(linepass_layout.itemAtPosition(4, 1).widget().currentText())

        linepass = LinePassing(line=line, instant=instant, speed=speed, wrongDirection=wrongDirection,
                               group=self.group)
        session.add(linepass)
        session.commit()


    # -------------- ZonePassing buttons ------------------
    def zonepass_newRecBtn_click(self):
        if self.group is None:
            QMessageBox.information(self, 'Error!', 'No user group is defined or saved!')
            return
        self.zonepass_grpBox.setEnabled(True)

        self.zonepass_saveButton.setEnabled(True)
        self.zonepass_newRecButton.setEnabled(False)

        self.init_input_widgets(self.zonepass_grpBox)

    def zonepass_saveBtn_click(self):
        self.zonepass_grpBox.setEnabled(False)

        self.zonepass_saveButton.setEnabled(False)
        self.zonepass_newRecButton.setEnabled(True)

        zonepass_layout = self.zonepass_grpBox.layout()
        zoneIdx = zonepass_layout.itemAtPosition(0, 1).widget().currentText()
        zone = session.query(Zone).filter(Zone.idx == zoneIdx).first()
        instant_wdgt = zonepass_layout.itemAtPosition(2, 1).widget()
        input_wdgt_val = instant_wdgt.dateTime().toPyDateTime()
        instant = input_wdgt_val.replace(microsecond=0)
        entering = self.toBool(zonepass_layout.itemAtPosition(3, 1).widget().currentText())

        zonepass = ZonePassing(zone=zone, instant=instant, entering=entering, group=self.group)
        session.add(zonepass)
        session.commit()

    # -------------- Activity buttons ------------------
    def act_newRecBtn_click(self):
        self.act_grpBox.setEnabled(True)

        self.act_saveButton.setEnabled(True)
        self.act_newRecButton.setEnabled(False)

        self.init_input_widgets(self.act_grpBox)

    def act_saveBtn_click(self):
        self.act_grpBox.setEnabled(False)

        self.act_saveButton.setEnabled(False)
        self.act_newRecButton.setEnabled(True)

        act_layout = self.act_grpBox.layout()
        activity = act_layout.itemAtPosition(0, 1).widget().text()

        start_wdgt = act_layout.itemAtPosition(1, 1).widget()
        start_wdgt_val = start_wdgt.dateTime().toPyDateTime()
        startTime = start_wdgt_val.replace(microsecond=0)

        end_wdgt = act_layout.itemAtPosition(2, 1).widget()
        end_wdgt_val = end_wdgt.dateTime().toPyDateTime()
        endTime = end_wdgt_val.replace(microsecond=0)

        zoneIdx = act_layout.itemAtPosition(3, 1).widget().currentText()
        zone = session.query(Zone).filter(Zone.idx == zoneIdx).first()

        activity = Activity(activity=activity, startTime=startTime, endTime=endTime,
                            zone=zone, group=self.group)
        session.add(activity)
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

                    if fk_items != items:
                        input_wdgt.clear()
                        input_wdgt.addItems(items)

            elif isinstance(input_wdgt, QDateTimeEdit):
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
            elif column['is_foreign_key']:
                wdgt = QComboBox()
            elif column['is_datetime']:
                wdgt = QDateTimeEdit()
                wdgt.setDisplayFormat('yyyy-MM-dd hh:mm:ss')
                # wdgt.setCalendarPopup(True)
            else:
                wdgt = QLineEdit()
                if column['is_primary_key']:
                    wdgt.setReadOnly(True) #.setEnabled(False)

            groupBox_layout.addWidget(wdgt, i, 1)
            i += 1

        # gridWidget.setLayout(gridLayout)

        # groupBox_layout.addWidget(gridWidget)

        # groupBox.setAlignment(Qt.AlignHCenter)
        groupBox.setLayout(groupBox_layout)

        groupBox.setCheckable(checkable)
        groupBox.setEnabled(False)
        return  groupBox

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

        self.figure = plt.figure(tight_layout=False)

        self.canvas = FigureCanvas(self.figure)

        # self.ods_dict = getOdNamesDirections(session)

        winLayout = QVBoxLayout()
        gridLayout = QGridLayout()

        gridLayout.addWidget(NavigationToolbar(self.canvas, self), 1, 0, 1, 7, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('transport:'), 0, 0, Qt.AlignRight)
        self.transportCombobx = QComboBox()
        self.transportCombobx.addItems(inspect(Mode).columns['transport'].type.enums)
        gridLayout.addWidget(self.transportCombobx, 0, 1, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('action type:'), 0, 2, Qt.AlignRight)
        self.actionTypeCombobx = QComboBox()
        self.actionTypeCombobx.addItems(actionTypeList)
        self.actionTypeCombobx.setCurrentIndex(-1)
        self.actionTypeCombobx.currentTextChanged.connect(self.actionTypeChanged)
        gridLayout.addWidget(self.actionTypeCombobx, 0, 3, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('unit Idx:'), 0, 4, Qt.AlignRight)
        self.unitIdxCombobx = QComboBox()
        gridLayout.addWidget(self.unitIdxCombobx, 0, 5, Qt.AlignLeft)

        self.plotBtn = QPushButton('Plot')
        self.plotBtn.clicked.connect(self.plotTHist)
        self.plotBtn.setEnabled(False)
        gridLayout.addWidget(self.plotBtn, 0, 6)

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

        start_obs_time, end_obs_time = getObsStartEnd(session)
        if None in [start_obs_time, end_obs_time]:
            QMessageBox.information(self, 'Error!', 'There is no observation!')
            return
        bins = calculateBinsEdges(start_obs_time, end_obs_time)

        if len(bins) < 2:
            QMessageBox.information(self, 'Error!', 'The observation duration is too short!')
            return
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

        self.figure = plt.figure(tight_layout=False)

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

        self.figure = plt.figure(tight_layout=False)

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
                start_time = bins[0].to_pydatetime()
                end_time = bins[-1].to_pydatetime()

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


class CompHistWindow(QDialog):
    def __init__(self, parent=None):
        super(CompHistWindow, self).__init__(parent)

        self.setWindowTitle('Comparative Temporal Distribution Histogram')

        self.figure = plt.figure(tight_layout=False)

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

        gridLayout.addWidget(QLabel('transport:'), 0, 0, Qt.AlignRight)
        self.transportCombobx = QComboBox()
        self.transportCombobx.addItems(inspect(Mode).columns['transport'].type.enums)
        gridLayout.addWidget(self.transportCombobx, 0, 1, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('action type:'), 0, 2, Qt.AlignRight)
        self.actionTypeCombobx = QComboBox()
        self.actionTypeCombobx.addItems(actionTypeList)
        self.actionTypeCombobx.setCurrentIndex(-1)
        self.actionTypeCombobx.currentTextChanged.connect(self.actionTypeChanged)
        gridLayout.addWidget(self.actionTypeCombobx, 0, 3, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('unit Idx:'), 0, 4, Qt.AlignRight)
        self.unitIdxCombobx = QComboBox()
        gridLayout.addWidget(self.unitIdxCombobx, 0, 5, Qt.AlignLeft)

        self.plotBtn = QPushButton('Plot')
        self.plotBtn.clicked.connect(self.plotCompHist)
        self.plotBtn.setEnabled(False)
        gridLayout.addWidget(self.plotBtn, 0, 6)

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

        if 'line' in actionType.split(' '):
            cls_obs = LinePassing
        elif 'zone' in actionType.split(' '):
            cls_obs = ZonePassing

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

        bins = calculateBinsEdges(start, end)
        if len(bins) < 2:
            QMessageBox.information(self, 'Error!',
                    'The common observation duration is too short!')
            return
        # label1 = os.path.basename(self.parent().dbFilename).split('.')[0]
        # label2 = os.path.basename(self.dbFile2Ledit.text()).split('.')[0]
        label1 = self.session1.query(LinePassing.instant).first()[0].strftime('%a, %b %d, %Y')
        label2 = self.session2.query(LinePassing.instant).first()[0].strftime('%a, %b %d, %Y')

        err = tempDistHist(transport, actionType, unitIdx, ax, [self.session1, self.session2],
                           bins=bins, alpha=0.7, color=['skyblue', 'red'], ec='grey',
                           label=[label1, label2], rwidth=0.9)
        plt.legend(loc='upper right', fontsize=6)
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

        gridLayout.addWidget(QLabel('transport:'), 0, 0, Qt.AlignRight)
        self.transportCombobx = QComboBox()
        self.transportCombobx.addItems(inspect(Mode).columns['transport'].type.enums)
        # self.siteNameCombobx.currentTextChanged.connect(self.genReport)
        gridLayout.addWidget(self.transportCombobx, 0, 1, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('action type:'), 0, 2, Qt.AlignRight)
        self.actionTypeCombobx = QComboBox()
        self.actionTypeCombobx.addItems(actionTypeList)
        self.actionTypeCombobx.setCurrentIndex(-1)
        # self.camViewCombobx.currentTextChanged.connect(self.actionTypeChanged)
        gridLayout.addWidget(self.actionTypeCombobx, 0, 3, Qt.AlignLeft)

        self.genRepBtn = QPushButton('Generate report')
        self.genRepBtn.clicked.connect(self.genReport)
        gridLayout.addWidget(self.genRepBtn, 0, 4)

        self.saveBtn = QPushButton()
        self.saveBtn.setIcon(QIcon('icons/save.png'))
        self.saveBtn.setToolTip('Save report')
        self.saveBtn.clicked.connect(self.saveReport)
        gridLayout.addWidget(self.saveBtn, 0, 5)

        # winLayout.addWidget(self.toolbar)
        winLayout.addLayout(gridLayout)
        winLayout.addWidget(self.table)

        self.setLayout(winLayout)

    def genReport(self):

        transport = self.transportCombobx.currentText()
        actionType = self.actionTypeCombobx.currentText()

        start_obs_time, end_obs_time = getObsStartEnd(session)
        bins = calculateBinsEdges(start_obs_time, end_obs_time)
        if len(bins) < 2:
            QMessageBox.information(self, 'Error!', 'The observation duration is too short!')
            return
        else:
            start_time = bins[0].to_pydatetime()
            end_time = bins[-1].to_pydatetime()
        self.indicatorsDf = generateReport(transport, actionType, start_time, end_time, session)

        model = dfTableModel(self.indicatorsDf)
        self.table.setModel(model)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def saveReport(self):
        if not self.indicatorsDf is None:
            self.indicatorsDf.to_clipboard()
            msg = QMessageBox()
            msg.setText('The table is copied to the clipboard.')
            msg.exec_()


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

        gridLayout.addWidget(QLabel('transport:'), 0, 0, Qt.AlignRight)
        self.transportCombobx = QComboBox()
        self.transportCombobx.addItems(inspect(Mode).columns['transport'].type.enums)
        # self.siteNameCombobx.currentTextChanged.connect(self.compIndicators)
        gridLayout.addWidget(self.transportCombobx, 0, 1, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('action type:'), 0, 2, Qt.AlignRight)
        self.actionTypeCombobx = QComboBox()
        self.actionTypeCombobx.addItems(actionTypeList)
        self.actionTypeCombobx.setCurrentIndex(-1)
        # self.camViewCombobx.currentTextChanged.connect(self.actionTypeChanged)
        gridLayout.addWidget(self.actionTypeCombobx, 0, 3, Qt.AlignLeft)

        self.genRepBtn = QPushButton('Compare Indicators')
        self.genRepBtn.clicked.connect(self.compIndicators)
        gridLayout.addWidget(self.genRepBtn, 0, 4)

        self.saveBtn = QPushButton()
        self.saveBtn.setIcon(QIcon('icons/save.png'))
        self.saveBtn.setToolTip('Save results to clipboard')
        self.saveBtn.setFixedWidth(75)
        self.saveBtn.clicked.connect(self.saveReport)
        gridLayout.addWidget(self.saveBtn, 0, 5)

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

        first_obs_time1, last_obs_time1 = getObsStartEnd(self.session1)
        first_obs_time2, last_obs_time2 = getObsStartEnd(self.session2)

        if first_obs_time1.time() >= first_obs_time2.time():
            bins_start = first_obs_time1
        else:
            bins_start = first_obs_time2

        if last_obs_time1.time() <= last_obs_time2.time():
            bins_end = last_obs_time1
        else:
            bins_end = last_obs_time2

        bins = calculateBinsEdges(bins_start, bins_end)
        if len(bins) > 1:
            start_time = bins[0].time()
            end_time = bins[-1].time()
        else:
            QMessageBox.information(self, 'Error!', 'The common observaion duration is too short!')

        self.indicatorsDf = compareIndicators(transport, actionType, start_time, end_time,
                                              self.session1, self.session2)

        model = dfTableModel(self.indicatorsDf)
        self.table.setModel(model)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

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

class plotTrajWindow(QDialog):
    def __init__(self, parent=None):
        super(plotTrajWindow, self).__init__(parent)

        self.setWindowTitle('Trajectories, screenlines and zones')

        self.cur = None
        self.homographyFilename = None
        self.cameraTypeIdx = None
        self.dateStr = None
        self.figure = plt.figure(tight_layout=False)
        self.canvas = FigureCanvas(self.figure)

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

        gridLayout.addWidget(NavigationToolbar(self.canvas, self), 1, 0, 1, 7, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Site name:'), 0, 0, Qt.AlignRight)
        self.siteNameCombobx = QComboBox()
        self.siteNameCombobx.setMinimumWidth(120)
        self.siteNameCombobx.currentTextChanged.connect(self.siteChanged)
        gridLayout.addWidget(self.siteNameCombobx, 0, 1, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Camera view:'), 0, 2, Qt.AlignRight)
        self.camViewCombobx = QComboBox()
        self.camViewCombobx.currentTextChanged.connect(self.viewChanged)
        gridLayout.addWidget(self.camViewCombobx, 0, 3, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Trajectory database:'), 0, 4, Qt.AlignRight)
        self.trjDbCombobx = QComboBox()
        self.trjDbCombobx.setMinimumWidth(130)
        # self.trjDbCombobx.currentTextChanged.connect(self.plotItems)
        gridLayout.addWidget(self.trjDbCombobx, 0, 5, Qt.AlignLeft)

        self.plotBtn = QPushButton('Plot')
        self.plotBtn.clicked.connect(self.plotItems)
        # self.plotBtn.setEnabled(False)
        gridLayout.addWidget(self.plotBtn, 0, 6)

        # winLayout.addWidget(self.toolbar)
        winLayout.addLayout(mdbLayout)
        winLayout.addLayout(gridLayout)
        winLayout.addWidget(self.canvas)

        self.setLayout(winLayout)

    def plotItems(self):
        self.cur.execute('SELECT intrinsicCameraMatrixStr, distortionCoefficientsStr FROM camera_types WHERE idx=?',
                         (self.cameraTypeIdx,))
        row = self.cur.fetchall()
        intrinsicCameraMatrixStr = row[0][0]
        distortionCoefficientsStr = row[0][1]
        intrinsicCameraMatrix = np.array(ast.literal_eval(intrinsicCameraMatrixStr))
        distortionCoefficients = np.array(ast.literal_eval(distortionCoefficientsStr))

        mdbPath = Path(self.mdbFileLedit.text()).parent

        trjDBFile = mdbPath/self.siteNameCombobx.currentText()/self.dateStr/self.trjDbCombobx.currentText()
        homoFile = mdbPath/self.siteNameCombobx.currentText()/self.homographyFilename

        if not trjDBFile.exists():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText('The trajectory database does not exist!')
            msg.exec_()
            self.figure.clear()
            self.canvas.draw()
            return

        if not homoFile.exists():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText('The homography file does not exist!')
            msg.exec_()
            self.figure.clear()
            self.canvas.draw()
            return

        self.figure.clear()
        self.canvas.draw()

        ax = self.figure.add_subplot(111)

        plotTrajectory(trjDBFile, intrinsicCameraMatrix, distortionCoefficients, homoFile, ax, session)

        # if err != None:
        #     msg = QMessageBox()
        #     msg.setIcon(QMessageBox.Information)
        #     msg.setText(err)
        #     msg.exec_()
        # else:
            # refresh canvas
        self.canvas.draw()


    def openMdbFile(self):
        mdbFilename, _ = QFileDialog.getOpenFileName(self, "Open metadata file",
                                                     QDir.homePath(), "Sqlite files (*.sqlite)")
        if mdbFilename == '':
            return

        self.mdbFileLedit.setText(mdbFilename)

        con = sqlite3.connect(self.mdbFileLedit.text())
        self.cur = con.cursor()

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

    def __init__(self, data):
        QAbstractTableModel.__init__(self)
        self._data = data

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
                if str(self._data.iloc[index.row(), index.column()])[0] == '-':
                    return QColor(255, 204, 204)
                elif str(self._data.iloc[index.row(), index.column()])[0] == '+':
                    return QColor(204, 255, 204)
                elif str(self._data.iloc[index.row(), index.column()])[0:3] == '0 [' or \
                     str(self._data.iloc[index.row(), index.column()])[0:5] == '0.0 [':
                    return QColor(255, 255, 204)
                elif str(self._data.iloc[index.row(), index.column()])[0] == 'x':
                    return QColor(244, 244, 244)
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