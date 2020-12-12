import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QGridLayout, QVBoxLayout, QHBoxLayout,
                             QToolBox, QPushButton, QTextEdit, QLineEdit, QMainWindow,
                             QComboBox, QGroupBox, QDateTimeEdit, QAction, QStyle,
                             QFileDialog, QToolBar, QMessageBox, QDialog, QLabel)
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtCore import QDateTime, QSize, QDir, Qt

from framework.dbSchema import createDatabase, connectDatabase, \
    Study_site, Site_ODs, Person, Pedestrian, Vehicle, Bike, \
    Activity, Group, Pedestrian_obs, Vehicle_obs, Bike_obs, \
    Passenger, GroupBelongings

from framework.indicators import tempDistHist, stackedHist, odMatrix
from framework import dbSchema

from sqlalchemy import Enum, Boolean, DateTime
from sqlalchemy.inspection import inspect


class ObsToolbox(QMainWindow):
    def __init__(self, parent=None):
        super(ObsToolbox, self).__init__(parent)
        self.resize(400, 650)
        self.dbFilename = '/Users/Abbas/test2.sqlite'
        self.session = None
        self.roadUser = None
        self.odName = None
        self.userAttr = None
        layout = QVBoxLayout() #QGridLayout()

        #--------------------------------------------
        self.setWindowTitle(self.dbFilename)
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

        openAction = QAction(QIcon('icons/database.png'), '&Open database file', self)
        openAction.setShortcut('Ctrl+O')
        openAction.setStatusTip('Open database file')
        openAction.triggered.connect(self.opendbFile)

        tempHistAction = QAction(QIcon('icons/histogram.png'), '&Temporal Histogram', self)
        # openAction.setShortcut('Ctrl+O')
        # openAction.setStatusTip('Open database file')
        tempHistAction.triggered.connect(self.tempHist)

        stackHistAction = QAction(QIcon('icons/stacked.png'), '&Stacked Histogram', self)
        stackHistAction.triggered.connect(self.stackedHist)

        odMatrixAction = QAction(QIcon('icons/square-grid.png'), '&OD Matrix', self)
        odMatrixAction.triggered.connect(self.odMatrix)

        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(24, 24))
        self.toolbar.addAction(openAction)
        self.toolbar.addAction(tempHistAction)
        self.toolbar.addAction(stackHistAction)
        self.toolbar.addAction(odMatrixAction)
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

        gridLayout = QGridLayout()
        gridWidget = QWidget()
        gridWidget.setEnabled(False)

        newButton = QPushButton(QIcon('icons/new.png'), 'New record')
        groupBox_layout.addWidget(newButton)

        i = 0
        for column in self.getTableColumns(tableClass):
            label = QLabel(column['name'])
            gridLayout.addWidget(label, i, 0)

            if column['enum'] != None:
                wdgt = QComboBox()
                wdgt.addItems(column['enum'])
                # wdgt.setCurrentIndex(-1)
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

        btnsLayout = QHBoxLayout()

        addButton = QPushButton(QIcon('icons/save.png'), 'Save')
        addButton.setEnabled(False)

        editButton = QPushButton(QIcon('icons/edit.png'), 'Edit')
        editButton.setEnabled(False)

        delButton = QPushButton(QIcon('icons/delete.png'), 'Delete')
        delButton.setEnabled(False)

        btnsLayout.addWidget(delButton)
        btnsLayout.addWidget(editButton)
        btnsLayout.addWidget(addButton)

        groupBox_layout.addLayout(btnsLayout) #.addWidget(addButton)

        groupBox = QGroupBox(tableClass.__name__)
        groupBox.setLayout(groupBox_layout)

        newButton.clicked.connect(lambda: self.newObject(groupBox, gridWidget, addButton, editButton))
        addButton.clicked.connect(lambda: self.addObject(groupBox, gridWidget, newButton, editButton,
                                                         delButton))
        editButton.clicked.connect(lambda: self.editObject(groupBox, gridWidget, newButton, addButton))
        delButton.clicked.connect(lambda: self.deleteObject(groupBox, gridWidget, newButton, editButton))

        return  groupBox

    def newObject(self, grpBx, grid_wdgt, addBtn, editBtn):
        self.sender().setEnabled(False)
        grid_wdgt.setEnabled(True)
        addBtn.setEnabled(True)
        editBtn.setEnabled(False)

        class_ = getattr(dbSchema, grpBx.title())
        instance = class_()
        self.session.add(instance)
        self.session.flush()

        grid_lyt = grid_wdgt.layout()
        grid_labels = [grid_lyt.itemAtPosition(i, 0).widget() for i in range(grid_lyt.rowCount())]

        i = 0
        for label in grid_labels:
            input_wdgt = grid_lyt.itemAtPosition(i, 1).widget()
            if  isinstance(input_wdgt, QLineEdit) and input_wdgt.isReadOnly():
                input_wdgt.setText(str(getattr(instance, label.text())))
            elif isinstance(input_wdgt, QComboBox):
                if len(getattr(class_, label.text()).foreign_keys) > 0:
                    fk_set = getattr(class_, label.text()).foreign_keys
                    fk = next(iter(fk_set))
                    items = [i[0] for i in self.session.query(fk.column).all()]
                    items.sort(reverse=True)
                    items = [str(i) for i in items]
                    input_wdgt.clear()
                    input_wdgt.addItems(items)
            elif  isinstance(input_wdgt, QDateTimeEdit):
                if self.parent() == None or self.parent().videoCurrentDatetime == None:
                    input_wdgt.setDateTime(QDateTime.currentDateTime())
                else:
                    input_wdgt.setDateTime(QDateTime(self.parent().videoCurrentDatetime))
            i = i + 1

        grid_wdgt.repaint()
        # self.session.commit()

        # rels = inspect(class_).relationships
        # clss = [rel.mapper.class_ for rel in rels]
        # print(clss)

        # fk_set = inspect(class_).columns.personId.foreign_keys
        # fk = next(iter(fk_set))
        # print(fk.column)
        # print([i[0] for i in self.session.query(fk.column).all()])


    def addObject(self, grpBx, grid_wdgt, newBtn, editBtn, delBtn):
        newBtn.setEnabled(True)
        editBtn.setEnabled(True)
        delBtn.setEnabled(True)
        grid_wdgt.setEnabled(False)
        self.sender().setEnabled(False)
        self.sender().setText('Save')

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
                if input_wdgt.currentText() == 'True':
                    input_wdgt_val = True
                elif input_wdgt.currentText() == 'False':
                    input_wdgt_val = False
                else:
                    input_wdgt_val = input_wdgt.currentText()
            elif isinstance(input_wdgt, QDateTimeEdit):
                    input_wdgt_val = input_wdgt.dateTime().toPyDateTime()
            setattr(instance, label.text(), input_wdgt_val)
            i = i + 1

        self.session.commit()

        grid_wdgt.repaint()

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
        # dlg = QFileDialog()
        # dlg.DontUseNativeDialog
        # dlg.FileMode(QFileDialog.AnyFile)
        fileName, _ = QFileDialog.getSaveFileName(self, "Open database file",
                                                  QDir.homePath())#, "Sqlite files (*.sqlite)")
        if fileName != '':
            self.setWindowTitle(fileName)

            self.dbFilename = fileName

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
        inputWin = QDialog(self)
        inputWin.setModal(True)
        inputWin.setAttribute(Qt.WA_DeleteOnClose)

        winLayout = QVBoxLayout()
        gridLayout = QGridLayout()
        btnsLayout = QHBoxLayout()

        gridLayout.addWidget(QLabel('Road user'), 0, 0)
        userCombobx = QComboBox()
        userCombobx.addItems(['pedestrian', 'vehicle', 'cyclist'])
        gridLayout.addWidget(userCombobx, 0, 1)

        gridLayout.addWidget(QLabel('OD name'), 1, 0)
        odNamesCombobx = QComboBox()
        odNamesCombobx.addItems([name[0] for name in self.session.query(Site_ODs.odName).all()])
        gridLayout.addWidget(odNamesCombobx, 1, 1)

        okBtn = QPushButton('Ok')
        okBtn.clicked.connect(lambda: self.okBtnClickTHist(userCombobx, odNamesCombobx))
        cancelBtn = QPushButton('Cancel')
        cancelBtn.clicked.connect(self.cancelBtnClick)

        btnsLayout.addWidget(cancelBtn)
        btnsLayout.addWidget(okBtn)

        winLayout.addLayout(gridLayout)
        winLayout.addLayout(btnsLayout)

        inputWin.setLayout(winLayout)

        inputWin.exec_()

        if self.roadUser != None and self.odName != None:
            err = tempDistHist(user=self.roadUser, od_name=self.odName, session=self.session)
            if err != None:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Information)
                msg.setText(err)
                msg.exec_()


    def stackedHist(self):
        if self.session == None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText('The database file is not defined.')
            msg.exec_()
            return
        inputWin = QDialog(self)
        inputWin.setModal(True)
        inputWin.setAttribute(Qt.WA_DeleteOnClose)

        winLayout = QVBoxLayout()
        gridLayout = QGridLayout()
        btnsLayout = QHBoxLayout()

        gridLayout.addWidget(QLabel('Road user'), 0, 0)
        userCombobx = QComboBox()
        userCombobx.addItems(['pedestrian', 'vehicle', 'activities'])
        gridLayout.addWidget(userCombobx, 0, 1)

        gridLayout.addWidget(QLabel('Attribute'), 1, 0)
        attrCombobx = QComboBox()
        attrCombobx.addItems(['age', 'gender', 'vehicleType', 'activityType'])
        gridLayout.addWidget(attrCombobx, 1, 1)

        okBtn = QPushButton('Ok')
        okBtn.clicked.connect(lambda: self.okBtnClickSHist(userCombobx, attrCombobx))
        cancelBtn = QPushButton('Cancel')
        cancelBtn.clicked.connect(self.cancelBtnClick)

        btnsLayout.addWidget(cancelBtn)
        btnsLayout.addWidget(okBtn)

        winLayout.addLayout(gridLayout)
        winLayout.addLayout(btnsLayout)

        inputWin.setLayout(winLayout)

        inputWin.exec_()

        if self.roadUser != None and self.userAttr != None:
            err = stackedHist(user=self.roadUser, attr=self.userAttr, session=self.session)
            if err != None:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Information)
                msg.setText(err)
                msg.exec_()


    def odMatrix(self):
        if self.session == None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText('The database file is not defined.')
            msg.exec_()
            return
        inputWin = QDialog(self)
        inputWin.setModal(True)
        inputWin.setAttribute(Qt.WA_DeleteOnClose)

        winLayout = QVBoxLayout()
        gridLayout = QGridLayout()
        btnsLayout = QHBoxLayout()

        gridLayout.addWidget(QLabel('Road user'), 0, 0)
        userCombobx = QComboBox()
        userCombobx.addItems(['pedestrian', 'vehicle', 'cyclist'])
        gridLayout.addWidget(userCombobx, 0, 1)

        okBtn = QPushButton('Ok')
        okBtn.clicked.connect(lambda: self.okBtnClickODmatrix(userCombobx))
        cancelBtn = QPushButton('Cancel')
        cancelBtn.clicked.connect(self.cancelBtnClick)

        btnsLayout.addWidget(cancelBtn)
        btnsLayout.addWidget(okBtn)

        winLayout.addLayout(gridLayout)
        winLayout.addLayout(btnsLayout)

        inputWin.setLayout(winLayout)

        inputWin.exec_()

        if self.roadUser != None:
            err = odMatrix(user=self.roadUser, session=self.session)
            if err != None:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Information)
                msg.setText(err)
                msg.exec_()

    def okBtnClickTHist(self, userCombobx, odNamesCombobx):
        self.roadUser = userCombobx.currentText()
        self.odName = odNamesCombobx.currentText()
        self.sender().parent().close()

    def okBtnClickSHist(self, userCombobx, attrCombobx):
        self.roadUser = userCombobx.currentText()
        self.userAttr = attrCombobx.currentText()
        self.sender().parent().close()

    def okBtnClickODmatrix(self, userCombobx):
        self.roadUser = userCombobx.currentText()
        self.sender().parent().close()

    def cancelBtnClick(self):
        self.roadUser = None
        self.userAttr = None
        self.odName = None
        self.sender().parent().close()


if __name__ == '__main__':
    app = QApplication(sys.argv)

    obsTb = ObsToolbox()
    obsTb.show()

    sys.exit(app.exec_())