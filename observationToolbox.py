import sys
import os
import pandas as pd
import datetime
from PyQt5.QtWidgets import (QApplication, QWidget, QGridLayout, QVBoxLayout, QHBoxLayout,
                             QToolBox, QPushButton, QTextEdit, QLineEdit, QMainWindow,
                             QComboBox, QGroupBox, QDateTimeEdit, QAction, QStyle,
                             QFileDialog, QToolBar, QMessageBox, QDialog, QLabel,
                             QSizePolicy, QStatusBar, QTableWidget, QHeaderView, QTableWidgetItem,
                             QAbstractItemView)
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtCore import QDateTime, QSize, QDir, Qt

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


class ObsToolbox(QMainWindow):
    def __init__(self, parent=None):
        super(ObsToolbox, self).__init__(parent)
        self.resize(400, 650)
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.dbFilename = '/Users/Abbas/test.sqlite'
        self.session = None
        self.roadUser = None
        self.odName = None
        self.userAttr = None
        layout = QVBoxLayout() #QGridLayout()

        #--------------------------------------------
        self.setWindowTitle(os.path.basename(self.dbFilename))

        self.session = createDatabase(self.dbFilename)
        if self.session is None:
            self.session = connectDatabase(self.dbFilename)
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
        self.session.add(instance)
        self.session.flush()

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

                    items = [i[0] for i in self.session.query(fk.column).all()]
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


        # self.session.commit()

        # rels = inspect(class_).relationships
        # clss = [rel.mapper.class_ for rel in rels]
        # print(clss)

        # fk_set = inspect(class_).columns.personId.foreign_keys
        # fk = next(iter(fk_set))
        # print(fk.column)
        # print([i[0] for i in self.session.query(fk.column).all()])

    def newObject(self, grpBx):
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

        instance = self.session.query(class_).filter(getattr(class_, pk_name) == pk_val).first()
        obs_instance = self.session.query(Study_site).first()
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
                if current_obs_end != None:
                    if current_obs_end < input_wdgt_val:
                        obs_instance.obsEnd = input_wdgt_val
                else:
                    obs_instance.obsEnd = input_wdgt_val

            setattr(instance, label.text(), input_wdgt_val)
            i = i + 1

        self.session.commit()

        # grid_wdgt.repaint()

    def editObject(self, grpBx, grid_wdgt, newBtn, addBtn):
        grid_wdgt.setEnabled(True)
        addBtn.setEnabled(True)
        addBtn.setText('Update')
        self.sender().setEnabled(False)

    def deleteObject(self, grpBx, grid_wdgt, newBtn, editBtn):
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

        self.session.query(class_).filter(getattr(class_, pk_name) == pk_val).delete()
        self.session.commit()

    def newTab(self, classList, tabName, iconFilename):
        wdgt = QWidget()
        layout = QVBoxLayout()

        for className in classList:
            layout.addWidget(self.generateWidgets(className))
        wdgt.setLayout(layout)
        self.toolbox.addItem(wdgt, QIcon(iconFilename), tabName)


    def opendbFile(self):
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

            self.session = createDatabase(self.dbFilename)
            if self.session is None:
                self.session = connectDatabase(self.dbFilename)

    def tempHist(self):
        if self.session == None:
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
        if self.session == None:
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
        if self.session == None:
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
        if self.session == None:
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
        if self.session == None:
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
        if self.session == None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText('The database file is not defined.')
            msg.exec_()
            return
        genRepWin = genReportWindow(self)
        genRepWin.setGeometry(100, 100, 640, 480)

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
    #         fig, err = tempDistHist(user=self.roadUser, od_name=self.odName, session=self.session)
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

        # self.toolbar = NavigationToolbar(self.canvas, self)

        winLayout = QVBoxLayout()
        gridLayout = QGridLayout()

        gridLayout.addWidget(QLabel('Road user:'), 0, 0, Qt.AlignRight)
        self.userCombobx = QComboBox()
        self.userCombobx.addItems(['pedestrian', 'vehicle', 'cyclist'])
        gridLayout.addWidget(self.userCombobx, 0, 1, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('OD name:'), 0, 2, Qt.AlignRight)
        self.odNamesCombobx = QComboBox()
        self.odNamesCombobx.addItems([name[0]
                                      for name in self.parent().session.query(Site_ODs.odName).all()])
        gridLayout.addWidget(self.odNamesCombobx, 0, 3, Qt.AlignLeft)

        self.plotBtn = QPushButton('Plot')
        self.plotBtn.clicked.connect(self.plotTHist)
        gridLayout.addWidget(self.plotBtn, 0, 4)

        self.saveBtn = QPushButton()
        self.saveBtn.setIcon(QIcon('icons/save.png'))
        self.saveBtn.setToolTip('Save plot')
        self.saveBtn.clicked.connect(self.saveTHist)
        gridLayout.addWidget(self.saveBtn, 0, 5)

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

        err = tempDistHist(roadUser, odName, ax, self.parent().session)
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

        err = stackedHist(roadUser, attr, ax, self.parent().session)
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

        err = odMatrix(roadUser, ax, self.parent().session)
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
        gridLayout.addWidget(self.userCombobx, 0, 1, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('Attribute:'), 0, 2, Qt.AlignRight)
        self.attrCombobx = QComboBox()
        self.attrCombobx.addItems(['age', 'gender', 'vehicleType', 'activityType'])
        gridLayout.addWidget(self.attrCombobx, 0, 3, Qt.AlignLeft)

        self.plotBtn = QPushButton('Plot')
        self.plotBtn.clicked.connect(self.plotPieChart)
        gridLayout.addWidget(self.plotBtn, 0, 4)

        self.saveBtn = QPushButton()
        self.saveBtn.setIcon(QIcon('icons/save.png'))
        self.saveBtn.setToolTip('Save plot')
        self.saveBtn.clicked.connect(self.savePieChart)
        gridLayout.addWidget(self.saveBtn, 0, 5)

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

        err = pieChart(roadUser, attr, ax, self.parent().session)
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


class CompHistWindow(QDialog):
    def __init__(self, parent=None):
        super(CompHistWindow, self).__init__(parent)

        self.setWindowTitle('Comparative Temporal Distribution Histogram')
        self.session2 = None

        self.figure = plt.figure(tight_layout=False)

        self.canvas = FigureCanvas(self.figure)

        # self.toolbar = NavigationToolbar(self.canvas, self)

        winLayout = QVBoxLayout()
        gridLayout = QGridLayout()

        gridLayout.addWidget(QLabel('Database file:'), 0, 0, Qt.AlignRight)
        self.dbFile2Ledit = QLineEdit()
        gridLayout.addWidget(self.dbFile2Ledit, 0, 1, Qt.AlignLeft)

        self.openDbFileBtn = QPushButton()
        self.openDbFileBtn.setIcon(QIcon('icons/database.png'))
        self.openDbFileBtn.setToolTip('Open database file')
        self.openDbFileBtn.clicked.connect(self.opendbFile)
        gridLayout.addWidget(self.openDbFileBtn, 0, 2)

        gridLayout.addWidget(QLabel('Road user:'), 1, 0, Qt.AlignRight)
        self.userCombobx = QComboBox()
        self.userCombobx.addItems(['pedestrian', 'vehicle', 'cyclist'])
        gridLayout.addWidget(self.userCombobx, 1, 1, Qt.AlignLeft)

        gridLayout.addWidget(QLabel('OD name:'), 1, 2, Qt.AlignRight)
        self.odNamesCombobx = QComboBox()
        self.odNamesCombobx.addItems([name[0]
                                      for name in self.parent().session.query(Site_ODs.odName).all()])
        gridLayout.addWidget(self.odNamesCombobx, 1, 3, Qt.AlignLeft)

        self.plotBtn = QPushButton('Plot')
        self.plotBtn.clicked.connect(self.plotCompHist)
        gridLayout.addWidget(self.plotBtn, 1, 4)

        self.saveBtn = QPushButton()
        self.saveBtn.setIcon(QIcon('icons/save.png'))
        self.saveBtn.setToolTip('Save plot')
        self.saveBtn.clicked.connect(self.saveCompHist)
        gridLayout.addWidget(self.saveBtn, 1, 5)

        # winLayout.addWidget(self.toolbar)
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

        if roadUser == 'pedestrian':
            cls_ = Pedestrian_obs
        elif roadUser == 'vehicle':
            cls_ = Vehicle_obs
        elif roadUser == 'cyclist':
            cls_ = Bike_obs

        first_obs_time1 = self.parent().session.query(func.min(cls_.instant)).all()[0][0]
        last_obs_time1 = self.parent().session.query(func.max(cls_.instant)).all()[0][0]

        first_obs_time2 = self.session2.query(func.min(cls_.instant)).all()[0][0]
        last_obs_time2 = self.session2.query(func.max(cls_.instant)).all()[0][0]

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

        bins = pd.date_range(start, end, periods=21).to_pydatetime()
        label1 = os.path.basename(self.parent().dbFilename).split('.')[0]
        label2 = os.path.basename(self.dbFile2Ledit.text()).split('.')[0]

        err = tempDistHist(roadUser, odName, ax, self.parent().session, bins=bins, alpha=0.5,
                           color = 'blue', ec='blue', label=label1, rwidth=1, histtype='stepfilled',
                           comparison=True)
        err = tempDistHist(roadUser, odName, ax, self.session2, bins=bins, alpha=0.5,
                           color='red', ec='red', label=label2, rwidth=1, histtype='stepfilled',
                           comparison=True)
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


class genReportWindow(QDialog):
    def __init__(self, parent=None):
        super(genReportWindow, self).__init__(parent)

        self.setWindowTitle('List of indicators')
        self.setWindowIcon(QIcon('icons/report.png'))
        self.table = QTableWidget()
        # self.table.horizontalHeader().setStretchLastSection(True)
        # self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().hide()


        winLayout = QVBoxLayout()
        gridLayout = QGridLayout()

        gridLayout.addWidget(QLabel('Subject:'), 0, 0, Qt.AlignRight)
        self.subjCombobx = QComboBox()
        self.subjCombobx.addItems(['Pedestrian', 'Vehicle', 'Bike', 'Activity'])
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
        for _ in range(self.table.columnCount()):
            self.table.removeColumn(0)

        for _ in range(self.table.rowCount()):
            self.table.removeRow(0)

        subject = self.subjCombobx.currentText()

        indicatorsList = generateReport(subject, self.parent().session)
        for key in indicatorsList[0].keys():
            self.table.insertColumn(self.table.columnCount())
        self.table.setHorizontalHeaderLabels(indicatorsList[0].keys())

        row = 0
        for indicator in indicatorsList:
            self.table.insertRow(self.table.rowCount())
            col = 0
            for val in indicator.values():
                tabelItem = QTableWidgetItem(val)
                if col == 0:
                    self.table.horizontalHeader().setSectionResizeMode(col,
                                                                       QHeaderView.ResizeToContents)
                else:
                    self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Stretch)
                    tabelItem.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, tabelItem)
                col += 1
            row += 1

        # print(self.table.horizontalHeader().stretchSectionCount())


    def saveReport(self):
        pass


if __name__ == '__main__':
    app = QApplication(sys.argv)

    obsTb = ObsToolbox()
    obsTb.show()

    sys.exit(app.exec_())