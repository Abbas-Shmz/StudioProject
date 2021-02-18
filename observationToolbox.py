import sys
import os
import pandas as pd
import datetime
from PyQt5.QtWidgets import (QApplication, QWidget, QGridLayout, QVBoxLayout, QHBoxLayout,
                             QToolBox, QPushButton, QTextEdit, QLineEdit, QMainWindow,
                             QComboBox, QGroupBox, QDateTimeEdit, QAction, QStyle,
                             QFileDialog, QToolBar, QMessageBox, QDialog, QLabel,
                             QSizePolicy, QStatusBar, QTableWidget, QHeaderView, QTableWidgetItem,
                             QAbstractItemView, QTableView)
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtCore import QDateTime, QSize, QDir, Qt, QAbstractTableModel

from framework.dbSchema import createDatabase, connectDatabase, \
    Study_site, Site_ODs, Person, Pedestrian, Vehicle, Bike, \
    Activity, Group, Pedestrian_obs, Vehicle_obs, Bike_obs, \
    GroupBelongings  #Passenger

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt

from framework.indicators import tempDistHist, stackedHist, odMatrix, pieChart, generateReport
from framework import dbSchema

from sqlalchemy import Enum, Boolean, DateTime
from sqlalchemy.inspection import inspect
from sqlalchemy import func

session = None
morningPeakStart = datetime.time(7, 0)
morningPeakEnd = datetime.time(9, 0)
eveningPeakStart = datetime.time(15, 0)
eveningPeakEnd = datetime.time(19, 0)
binsMinutes = 10

class ObsToolbox(QMainWindow):
    def __init__(self, parent=None):
        super(ObsToolbox, self).__init__(parent)
        self.resize(400, 650)
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        global session, morningPeakStart, morningPeakEnd, eveningPeakStart, eveningPeakEnd
        self.dbFilename = '/Users/Abbas/test.sqlite'

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

        reportAction = QAction(QIcon('icons/report.png'), '&Generate Report', self)
        reportAction.triggered.connect(self.genReport)

        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(24, 24))
        self.toolbar.addAction(self.openAction)
        self.toolbar.addAction(tempHistAction)
        self.toolbar.addAction(stackHistAction)
        self.toolbar.addAction(odMatrixAction)
        self.toolbar.addAction(pieChartAction)
        self.toolbar.addAction(compHistAction)
        self.toolbar.addAction(reportAction)
        self.toolbar.insertSeparator(tempHistAction)
        self.addToolBar(Qt.LeftToolBarArea, self.toolbar)

        # ==================== Toolbox tabs =========================
        # Person tab
        self.newTab([Person], Person.__name__, 'icons/person.png')

        # Group tab
        self.newTab([Group, GroupBelongings], Group.__name__, 'icons/group.png')

        # Pedestrian tab
        self.newTab([Pedestrian, Pedestrian_obs], Pedestrian.__name__, 'icons/pedestrian.png')

        # Vehicle tab
        self.newTab([Vehicle, Vehicle_obs], Vehicle.__name__, 'icons/vehicle.png')

        # Bicycles tab
        self.newTab([Bike, Bike_obs], Bike.__name__, 'icons/bike.png')

        # Activity tab
        self.newTab([Activity], Activity.__name__, 'icons/activity.png')

        # Study_site tab
        self.newTab([Study_site, Site_ODs], Study_site.__name__, 'icons/study_site.png')


        # Create a widget for window contents
        wid = QWidget(self)
        self.setCentralWidget(wid)

        # Set widget to contain window contents
        wid.setLayout(layout)


    def getRelatedTable(self, grpBx):
        grid_wdgt = grpBx.layout().itemAt(1).widget()
        class_ = getattr(dbSchema, grpBx.title())

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


    def generateWidgets(self, tableClass):
        groupBox_layout = QVBoxLayout()
        btnsLayout = QHBoxLayout()
        newBtnsLayout = QHBoxLayout()
        gridLayout = QGridLayout()
        gridWidget = QWidget()
        gridWidget.setEnabled(False)

        newRecButton = QPushButton(QIcon('icons/new.png'), 'New record')
        newObjButton = QPushButton(QIcon('icons/new-object.png'), 'New object')
        newBtnsLayout.addWidget(newRecButton)
        newBtnsLayout.addWidget(newObjButton)
        groupBox_layout.addLayout(newBtnsLayout)

        i = 0
        for column in self.getTableColumns(tableClass):
            label = QLabel(column['name'])
            gridLayout.addWidget(label, i, 0)

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

            gridLayout.addWidget(wdgt, i, 1)
            i = i + 1

        gridWidget.setLayout(gridLayout)

        groupBox_layout.addWidget(gridWidget)



        saveButton = QPushButton(QIcon('icons/save.png'), 'Save')
        saveButton.setEnabled(False)

        editButton = QPushButton(QIcon('icons/edit.png'), 'Edit')
        editButton.setEnabled(False)

        delButton = QPushButton(QIcon('icons/delete.png'), 'Delete')
        delButton.setEnabled(False)

        btnsLayout.addWidget(delButton)
        btnsLayout.addWidget(editButton)
        btnsLayout.addWidget(saveButton)

        groupBox_layout.addLayout(btnsLayout) #.addWidget(saveButton)

        groupBox = QGroupBox(tableClass.__name__)
        groupBox.setAlignment(Qt.AlignHCenter)
        groupBox.setLayout(groupBox_layout)

        newRecButton.clicked.connect(lambda: self.newRecord(groupBox))
        newObjButton.clicked.connect(lambda: self.newObject(groupBox))
        saveButton.clicked.connect(lambda: self.saveRecord(groupBox))
        editButton.clicked.connect(lambda: self.editObject(groupBox, gridWidget, newRecButton,
                                                           saveButton))
        delButton.clicked.connect(lambda: self.deleteObject(groupBox, gridWidget, newRecButton,
                                                            editButton))

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

        class_ = getattr(dbSchema, grpBx.title())
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

        class_ = getattr(dbSchema, grpBx.title())
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
        obs_instance = session.query(Study_site).first()
        if obs_instance == None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText('The observatoin start time is not set!')
            msg.exec_()
            return
        current_obs_end = obs_instance.obsEnd

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

        class_ = getattr(dbSchema, grpBx.title())
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

    def newTab(self, classList, tabName, iconFilename):
        wdgt = QWidget()
        layout = QVBoxLayout()

        for className in classList:
            layout.addWidget(self.generateWidgets(className))
        wdgt.setLayout(layout)
        self.toolbox.addItem(wdgt, QIcon(iconFilename), tabName)


    def opendbFile(self):
        global session
        if self.sender() == self.openAction:
            self.dbFilename, _ = QFileDialog.getSaveFileName(self, "Open database file",
                                                  QDir.homePath(), "Sqlite files (*.sqlite)")
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



    # def okBtnClickTHist(self, userCombobx, odNamesCombobx, canv):
    #     self.roadUser = userCombobx.currentText()
    #     self.odName = odNamesCombobx.currentText()
    #
    #     canv.figure.axes.clear()
    #
    #     if self.roadUser != None and self.odName != None:
    #         fig, err = tempDistHist(user=self.roadUser, od_name=self.odName, session=session)
    #         if err != None:
    #             msg = QMessageBox()
    #             msg.setIcon(QMessageBox.Information)
    #             msg.setText(err)
    #             msg.exec_()
    #         else:
    #             canv.figure = fig
    #             canv.draw()
    #             print(canv.get_width_height())
    #
    # def okBtnClickSHist(self, userCombobx, attrCombobx):
    #     self.roadUser = userCombobx.currentText()
    #     self.userAttr = attrCombobx.currentText()
    #     self.sender().parent().close()
    #
    # def okBtnClickODmatrix(self, userCombobx):
    #     self.roadUser = userCombobx.currentText()
    #     self.sender().parent().close()
    #
    # def cancelBtnClick(self):
    #     self.roadUser = None
    #     self.userAttr = None
    #     self.odName = None
    #     self.sender().parent().close()


class TempHistWindow(QDialog):
    def __init__(self, parent=None):
        super(TempHistWindow, self).__init__(parent)

        self.setWindowTitle('Temporal Distribution Histogram')

        self.figure = plt.figure(tight_layout=False)

        self.canvas = FigureCanvas(self.figure)

        self.ods_dict = getOdNamesDirections(session)
        # self.toolbar = NavigationToolbar(self.canvas, self)

        winLayout = QVBoxLayout()
        gridLayout = QGridLayout()

        self.odDirCombobx = QComboBox()

        gridLayout.addWidget(QLabel('Road user:'), 0, 0, Qt.AlignRight)
        self.userCombobx = QComboBox()
        self.userCombobx.addItems(['Pedestrian', 'Vehicle', 'Bike'])
        gridLayout.addWidget(self.userCombobx, 0, 1, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('OD name:'), 0, 2, Qt.AlignRight)
        self.odNamesCombobx = QComboBox()
        self.odNamesCombobx.currentTextChanged.connect(self.odNameChanged)
        self.odNamesCombobx.addItems(self.ods_dict.keys())
        gridLayout.addWidget(self.odNamesCombobx, 0, 3, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Direction:'), 0, 4, Qt.AlignRight)
        gridLayout.addWidget(self.odDirCombobx, 0, 5, Qt.AlignLeft)

        self.plotBtn = QPushButton('Plot')
        self.plotBtn.clicked.connect(self.plotTHist)
        gridLayout.addWidget(self.plotBtn, 0, 6)

        self.saveBtn = QPushButton()
        self.saveBtn.setIcon(QIcon('icons/save.png'))
        self.saveBtn.setToolTip('Save plot')
        self.saveBtn.clicked.connect(self.saveTHist)
        gridLayout.addWidget(self.saveBtn, 0, 7)

        # winLayout.addWidget(self.toolbar)
        winLayout.addLayout(gridLayout)
        winLayout.addWidget(self.canvas)

        self.setLayout(winLayout)

    def plotTHist(self):
        self.figure.clear()
        self.canvas.draw()

        ax = self.figure.add_subplot(111)

        # plot data
        roadUser = self.userCombobx.currentText()
        odName = self.odNamesCombobx.currentText()
        odDirComboText = self.odDirCombobx.currentText()
        direction = []
        dirSymb = odDirComboText.split(' ')[1]
        od1 = int(odDirComboText.split(' ')[0])
        od2 = int(odDirComboText.split(' ')[2])
        if dirSymb == '<-->':
            direction.append([od1, od2])
            direction.append([od2, od1])
        elif dirSymb == '-->':
            direction.append([od1, od2])
        # elif dirSymb == '<--':
        #     direction.append([od2, od1])

        start_obs_time, end_obs_time = getObsStartEnd(session)
        bins = calculateNoBins(start_obs_time, end_obs_time, binsMinutes)

        err = tempDistHist(roadUser, odName, direction, ax, session, bins=bins)
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

    def odNameChanged(self):
        odName = self.odNamesCombobx.currentText()
        odDirItems = []
        if self.ods_dict[odName][2] == 'directed':
            odDirItems.append('{} --> {}'.format(self.ods_dict[odName][0], self.ods_dict[odName][1]))
        elif self.ods_dict[odName][2] == 'undirected':
            odDirItems.append('{} <--> {}'.format(self.ods_dict[odName][0], self.ods_dict[odName][1]))
            odDirItems.append('{} --> {}'.format(self.ods_dict[odName][0], self.ods_dict[odName][1]))
            odDirItems.append('{} --> {}'.format(self.ods_dict[odName][1], self.ods_dict[odName][0]))
        elif self.ods_dict[odName][2] == 'NA':
            if self.ods_dict[odName][3] == 'on_street_parking_lot':
                for dirList in self.ods_dict.values():
                    if dirList[3] == 'road_lane':
                        odDirItems.append('{} --> {}'.format(self.ods_dict[odName][0], dirList[1]))
                        odDirItems.append('{} --> {}'.format(dirList[0], self.ods_dict[odName][0]))

        self.odDirCombobx.clear()
        self.odDirCombobx.addItems(odDirItems)

class StackHistWindow(QDialog):
    def __init__(self, parent=None):
        super(StackHistWindow, self).__init__(parent)

        self.setWindowTitle('Stacked Histogram')

        self.figure = plt.figure(tight_layout=False)

        self.canvas = FigureCanvas(self.figure)

        # self.toolbar = NavigationToolbar(self.canvas, self)

        winLayout = QVBoxLayout()
        gridLayout = QGridLayout()

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

        self.saveBtn = QPushButton()
        self.saveBtn.setIcon(QIcon('icons/save.png'))
        self.saveBtn.setToolTip('Save plot')
        self.saveBtn.clicked.connect(self.saveSHist)
        gridLayout.addWidget(self.saveBtn, 0, 5)

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

        start_obs_time, end_obs_time = getObsStartEnd(session)
        bins = calculateNoBins(start_obs_time, end_obs_time, binsMinutes)

        err = stackedHist(roadUser, attr, ax, session, bins)
        if err != None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText(err)
            msg.exec_()
        else:
            # refresh canvas
            self.canvas.draw()

    def saveSHist(self):
        fileName, _ = QFileDialog.getSaveFileName(self, "Open database file",
                                                  QDir.homePath(), "PNG files (*.png)")
        if fileName != '':
            self.canvas.print_png(fileName)


class OdMatrixWindow(QDialog):
    def __init__(self, parent=None):
        super(OdMatrixWindow, self).__init__(parent)

        self.setWindowTitle('OD Matrix')

        self.figure = plt.figure(tight_layout=True)

        self.canvas = FigureCanvas(self.figure)

        # self.toolbar = NavigationToolbar(self.canvas, self)

        winLayout = QVBoxLayout()
        gridLayout = QGridLayout()

        gridLayout.addWidget(QLabel('Road user:'), 0, 0, Qt.AlignRight)
        self.userCombobx = QComboBox()
        self.userCombobx.addItems(['pedestrian', 'vehicle', 'cyclist'])
        gridLayout.addWidget(self.userCombobx, 0, 1, Qt.AlignLeft)

        self.plotBtn = QPushButton('Plot')
        self.plotBtn.clicked.connect(self.plotOdMtrx)
        gridLayout.addWidget(self.plotBtn, 0, 2)

        self.saveBtn = QPushButton()
        self.saveBtn.setIcon(QIcon('icons/save.png'))
        self.saveBtn.setToolTip('Save plot')
        self.saveBtn.clicked.connect(self.saveOdMtrx)
        gridLayout.addWidget(self.saveBtn, 0, 3)

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

        start_obs_time, end_obs_time = getObsStartEnd(session)

        err = odMatrix(roadUser, ax, start_obs_time, end_obs_time, session)
        if err != None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText(err)
            msg.exec_()
        else:
            # refresh canvas
            self.canvas.draw()

    def saveOdMtrx(self):
        fileName, _ = QFileDialog.getSaveFileName(self, "Open database file",
                                                  QDir.homePath(), "PNG files (*.png)")
        if fileName != '':
            self.canvas.print_png(fileName)


class PieChartWindow(QDialog):
    def __init__(self, parent=None):
        super(PieChartWindow, self).__init__(parent)

        self.setWindowTitle('Pie Chart')

        self.figure = plt.figure(tight_layout=False)

        self.canvas = FigureCanvas(self.figure)

        # self.toolbar = NavigationToolbar(self.canvas, self)

        winLayout = QVBoxLayout()
        gridLayout = QGridLayout()

        gridLayout.addWidget(QLabel('Road user:'), 0, 0, Qt.AlignRight)
        self.userCombobx = QComboBox()
        self.userCombobx.addItems(['All users', 'Pedestrian', 'Vehicle', 'Bike', 'Activity'])
        self.userCombobx.currentTextChanged.connect(self.getAttrList)
        gridLayout.addWidget(self.userCombobx, 0, 1, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Attribute:'), 0, 2, Qt.AlignRight)
        self.attrCombobx = QComboBox()
        self.attrCombobx.addItems(['count'])
        gridLayout.addWidget(self.attrCombobx, 0, 3, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Time span:'), 0, 4, Qt.AlignRight)
        self.timeSpanCombobx = QComboBox()

        start_obs_time, end_obs_time = getObsStartEnd(session)
        peakHours = getPeakHours(morningPeakStart, morningPeakEnd, eveningPeakStart, eveningPeakEnd,
                                 start_obs_time, end_obs_time)
        timeSpans = ['{} - {}'.format(start_obs_time.strftime('%I:%M %p'),
                                      end_obs_time.strftime('%I:%M %p'))]
        for pVal in peakHours.values():
            if pVal != None:
                timeSpans.append('{} - {}'.format(pVal[0].strftime('%I:%M %p'),
                                                  pVal[1].strftime('%I:%M %p')))
        self.timeSpanCombobx.addItems(timeSpans)
        self.timeSpanCombobx.currentTextChanged.connect(self.plotPieChart)
        gridLayout.addWidget(self.timeSpanCombobx, 0, 5, Qt.AlignLeft)

        self.plotBtn = QPushButton('Plot')
        self.plotBtn.clicked.connect(self.plotPieChart)
        gridLayout.addWidget(self.plotBtn, 0, 6)

        self.saveBtn = QPushButton()
        self.saveBtn.setIcon(QIcon('icons/save.png'))
        self.saveBtn.setToolTip('Save plot')
        self.saveBtn.clicked.connect(self.savePieChart)
        gridLayout.addWidget(self.saveBtn, 0, 7)

        # winLayout.addWidget(self.toolbar)
        winLayout.addLayout(gridLayout)
        winLayout.addWidget(self.canvas)

        self.setLayout(winLayout)

    def plotPieChart(self):
        self.figure.clear()
        self.canvas.draw()

        ax = self.figure.add_subplot(111)

        # plot data
        roadUser = self.userCombobx.currentText()
        attr = self.attrCombobx.currentText()

        sTimeText = self.timeSpanCombobx.currentText().split(' - ')[0]
        sTime = datetime.datetime.strptime(sTimeText, '%I:%M %p').time()
        sDate = getObsStartEnd(session)[0].date()
        startTime = datetime.datetime.combine(sDate, sTime)

        eTimeText = self.timeSpanCombobx.currentText().split(' - ')[1]
        eTime = datetime.datetime.strptime(eTimeText, '%I:%M %p').time()
        eDate = getObsStartEnd(session)[1].date()
        endTime = datetime.datetime.combine(eDate, eTime)

        err = pieChart(roadUser, attr, startTime, endTime, ax, session)
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
        if self.userCombobx.currentText() == 'All users':
            self.attrCombobx.clear()
            self.attrCombobx.addItems(['count'])
        elif self.userCombobx.currentText() == 'Pedestrian':
            self.attrCombobx.clear()
            self.attrCombobx.addItems(['age', 'gender'])
        elif self.userCombobx.currentText() == 'Vehicle':
            self.attrCombobx.clear()
            self.attrCombobx.addItems(['vehicleType'])
        elif self.userCombobx.currentText() == 'Bike':
            self.attrCombobx.clear()
            self.attrCombobx.addItems(['bikeType', 'wearHelmet'])
        elif self.userCombobx.currentText() == 'Activity':
            self.attrCombobx.clear()
            self.attrCombobx.addItems(['activityType'])


class CompHistWindow(QDialog):
    def __init__(self, parent=None):
        super(CompHistWindow, self).__init__(parent)

        self.setWindowTitle('Comparative Temporal Distribution Histogram')
        self.session2 = None

        self.figure = plt.figure(tight_layout=False)

        self.canvas = FigureCanvas(self.figure)

        self.ods_dict = getOdNamesDirections(session)
        # self.toolbar = NavigationToolbar(self.canvas, self)

        winLayout = QVBoxLayout()
        dbLayout = QHBoxLayout()
        gridLayout = QGridLayout()

        dbLayout.addWidget(QLabel('Database file:'))
        self.dbFile2Ledit = QLineEdit()
        dbLayout.addWidget(self.dbFile2Ledit)

        self.openDbFileBtn = QPushButton()
        self.openDbFileBtn.setIcon(QIcon('icons/database.png'))
        self.openDbFileBtn.setToolTip('Open database file')
        self.openDbFileBtn.clicked.connect(self.opendbFile)
        dbLayout.addWidget(self.openDbFileBtn)

        self.odDirCombobx = QComboBox()

        gridLayout.addWidget(QLabel('Road user:'), 0, 0, Qt.AlignRight)
        self.userCombobx = QComboBox()
        self.userCombobx.addItems(['Pedestrian', 'Vehicle', 'Bike'])
        gridLayout.addWidget(self.userCombobx, 0, 1, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('OD name:'), 0, 2, Qt.AlignRight)
        self.odNamesCombobx = QComboBox()
        self.odNamesCombobx.currentTextChanged.connect(self.odNameChanged)
        self.odNamesCombobx.addItems(self.ods_dict.keys())
        gridLayout.addWidget(self.odNamesCombobx, 0, 3, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Direction:'), 0, 4, Qt.AlignRight)
        gridLayout.addWidget(self.odDirCombobx, 0, 5, Qt.AlignLeft)

        self.plotBtn = QPushButton('Plot')
        self.plotBtn.clicked.connect(self.plotCompHist)
        gridLayout.addWidget(self.plotBtn, 0, 6)

        self.saveBtn = QPushButton()
        self.saveBtn.setIcon(QIcon('icons/save.png'))
        self.saveBtn.setToolTip('Save plot')
        self.saveBtn.clicked.connect(self.saveCompHist)
        gridLayout.addWidget(self.saveBtn, 0, 7)

        # winLayout.addWidget(self.toolbar)
        winLayout.addLayout(dbLayout)
        winLayout.addLayout(gridLayout)
        winLayout.addWidget(self.canvas)

        self.setLayout(winLayout)

    def plotCompHist(self):
        self.figure.clear()
        self.canvas.draw()

        ax = self.figure.add_subplot(111)

        # plot data
        roadUser = self.userCombobx.currentText()
        odName = self.odNamesCombobx.currentText()
        odDirComboText = self.odDirCombobx.currentText()
        direction = []
        dirSymb = odDirComboText.split(' ')[1]
        od1 = int(odDirComboText.split(' ')[0])
        od2 = int(odDirComboText.split(' ')[2])
        if dirSymb == '<-->':
            direction.append([od1, od2])
            direction.append([od2, od1])
        elif dirSymb == '-->':
            direction.append([od1, od2])

        if roadUser in ['Pedestrian', 'Vehicle', 'Bike']:
            cls_obs = getattr(dbSchema, roadUser + '_obs')

        # if roadUser == 'pedestrian':
        #     cls_ = Pedestrian_obs
        # elif roadUser == 'vehicle':
        #     cls_ = Vehicle_obs
        # elif roadUser == 'cyclist':
        #     cls_ = Bike_obs

        first_obs_time1 = session.query(func.min(cls_obs.instant)).all()[0][0]
        last_obs_time1 = session.query(func.max(cls_obs.instant)).all()[0][0]

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

        periods = calculateNoBins(start, end, binsMinutes)

        bins = pd.date_range(start, end, periods=periods).to_pydatetime()
        label1 = os.path.basename(self.parent().dbFilename).split('.')[0]
        label2 = os.path.basename(self.dbFile2Ledit.text()).split('.')[0]

        err = tempDistHist(roadUser, odName, direction, ax, [session, self.session2], bins=bins, alpha=0.7,
                           color = ['skyblue', 'red'], ec='grey', label=[label1, label2], rwidth=0.9)
        # err = tempDistHist(roadUser, odName, direction, ax, self.session2, bins=bins, alpha=0.5,
        #                    color='red', ec='red', label=label2, rwidth=1, histtype='stepfilled',
        #                    comparison=True)
        plt.legend(loc='upper right')
        if err != None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText(err)
            msg.exec_()
        else:
            # refresh canvas
            self.canvas.draw()

    def saveCompHist(self):
        fileName, _ = QFileDialog.getSaveFileName(self, "Save image file",
                                                  QDir.homePath(), "PNG files (*.png)")
        if fileName != '':
            self.canvas.print_png(fileName)

    def opendbFile(self):
        dbFilename, _ = QFileDialog.getOpenFileName(self, "Open database file",
                                                    QDir.homePath(), "Sqlite files (*.sqlite)")
        if dbFilename != '':
            self.dbFile2Ledit.setText(dbFilename)

            self.session2 = createDatabase(dbFilename)
            if self.session2 is None:
                self.session2 = connectDatabase(dbFilename)

    def odNameChanged(self):
        odName = self.odNamesCombobx.currentText()
        odDirItems = []
        if self.ods_dict[odName][2] == 'directed':
            odDirItems.append('{} --> {}'.format(self.ods_dict[odName][0], self.ods_dict[odName][1]))
        elif self.ods_dict[odName][2] == 'undirected':
            odDirItems.append('{} <--> {}'.format(self.ods_dict[odName][0], self.ods_dict[odName][1]))
            odDirItems.append('{} --> {}'.format(self.ods_dict[odName][0], self.ods_dict[odName][1]))
            odDirItems.append('{} --> {}'.format(self.ods_dict[odName][1], self.ods_dict[odName][0]))
        elif self.ods_dict[odName][2] == 'NA':
            if self.ods_dict[odName][3] == 'on_street_parking_lot':
                for dirList in self.ods_dict.values():
                    if dirList[3] == 'road_lane':
                        odDirItems.append('{} --> {}'.format(self.ods_dict[odName][0], dirList[1]))
                        odDirItems.append('{} --> {}'.format(dirList[0], self.ods_dict[odName][0]))

        self.odDirCombobx.clear()
        self.odDirCombobx.addItems(odDirItems)


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

        gridLayout.addWidget(QLabel('Subject:'), 0, 0, Qt.AlignRight)
        self.subjCombobx = QComboBox()
        self.subjCombobx.addItems(['Pedestrian', 'Vehicle', 'Bike', 'Activity', 'Access'])
        self.subjCombobx.currentTextChanged.connect(self.genReport)
        gridLayout.addWidget(self.subjCombobx, 0, 1, Qt.AlignLeft)

        self.genRepBtn = QPushButton('Generate report')
        self.genRepBtn.clicked.connect(self.genReport)
        gridLayout.addWidget(self.genRepBtn, 0, 2)

        self.saveBtn = QPushButton()
        self.saveBtn.setIcon(QIcon('icons/save.png'))
        self.saveBtn.setToolTip('Save report')
        self.saveBtn.clicked.connect(self.saveReport)
        gridLayout.addWidget(self.saveBtn, 0, 3)

        # winLayout.addWidget(self.toolbar)
        winLayout.addLayout(gridLayout)
        winLayout.addWidget(self.table)

        self.setLayout(winLayout)

    def genReport(self):

        subject = self.subjCombobx.currentText()

        start_obs_time, end_obs_time = getObsStartEnd(session)
        peakHours = getPeakHours(morningPeakStart, morningPeakEnd, eveningPeakStart, eveningPeakEnd,
                                 start_obs_time, end_obs_time)

        self.indicatorsDf = generateReport(subject, start_obs_time, end_obs_time, peakHours, session)

        model = dfTableModel(self.indicatorsDf)
        self.table.setModel(model)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def saveReport(self):
        if not self.indicatorsDf is None:
            self.indicatorsDf.to_clipboard()
            msg = QMessageBox()
            msg.setText('The table is copied to the clipboard.')
            msg.exec_()


def getPeakHours(morningPeakStart, morningPeakEnd, eveningPeakStart, eveningPeakEnd,
                 start_obs_time, end_obs_time):
    peakHours = {}
    if start_obs_time.time() < morningPeakStart:
        peakHours['Morning peak'] = [morningPeakStart, morningPeakEnd]
        peakHours['Off-peak'] = [morningPeakEnd, eveningPeakStart]
        peakHours['Evening peak'] = [eveningPeakStart, eveningPeakEnd]

    elif morningPeakStart < start_obs_time.time() < morningPeakEnd:
        peakHours['Morning peak'] = [start_obs_time.time(), morningPeakEnd]
        peakHours['Off-peak'] = [morningPeakEnd, eveningPeakStart]
        peakHours['Evening peak'] = [eveningPeakStart, eveningPeakEnd]

    elif morningPeakEnd < start_obs_time.time() < eveningPeakStart:
        peakHours['Morning peak'] = None
        peakHours['Off-peak'] = [start_obs_time.time(), eveningPeakStart]
        peakHours['Evening peak'] = [eveningPeakStart, eveningPeakEnd]

    elif eveningPeakStart < start_obs_time.time() < eveningPeakEnd:
        peakHours['Morning peak'] = None
        peakHours['Off-peak'] = None
        peakHours['Evening peak'] = [start_obs_time.time(), eveningPeakEnd]

    if eveningPeakStart < end_obs_time.time() < eveningPeakEnd:
        peakHours['Evening peak'][1] = end_obs_time.time()

    elif morningPeakEnd < end_obs_time.time() < eveningPeakStart:
        peakHours['Evening peak'] = None
        peakHours['Off-peak'][1] = end_obs_time.time()

    elif morningPeakStart < end_obs_time.time() < morningPeakEnd:
        peakHours['Evening peak'] = None
        peakHours['Off-peak'] = None
        peakHours['Morning peak'][1] = end_obs_time.time()

    return peakHours

def getObsStartEnd(session):
    site_instance = session.query(Study_site).first()
    start_obs_time = site_instance.obsStart
    end_obs_time = site_instance.obsEnd
    return start_obs_time, end_obs_time

def getOdNamesDirections(session):
    q = session.query(Site_ODs.odType, Site_ODs.odName, Site_ODs.id, Site_ODs.direction)

    pointOds = ['adjoining_ZOI', 'on_street_parking_lot', 'bicycle_rack', 'informal_bicycle_parking',
                'bus_stop', 'subway_station']
    ods_dict = {}
    for od in q.all():
        if od[1] in ods_dict.keys():
            ods_list = ods_dict[od[1]]
            if None in ods_list:
                ods_list[ods_list.index(None)] = od[2]
        else:
            if od[3].name == 'end_point':
                ods_dict[od[1]] = [None, od[2], 'directed', od[0].name]
            elif od[3].name == 'start_point':
                ods_dict[od[1]] = [od[2], None, 'directed', od[0].name]
            elif od[3].name == 'NA' and not(od[0].name in pointOds):
                ods_dict[od[1]] = [od[2], None, 'undirected', od[0].name]
            elif od[0].name in pointOds:
                ods_dict[od[1]] = [od[2], -1, 'NA', od[0].name]
    return ods_dict

def calculateNoBins(start_obs_time, end_obs_time, minutes):

    duration = end_obs_time - start_obs_time
    duration_in_s = duration.total_seconds()
    bins = round(duration_in_s/(60*minutes))
    if bins == 0:
        bins = 1
    return bins

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