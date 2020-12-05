import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QGridLayout, QVBoxLayout, QHBoxLayout,
                             QToolBox, QPushButton, QTextEdit, QLineEdit, QMainWindow,
                             QComboBox, QGroupBox, QDateTimeEdit, QAction, QStyle,
                             QFileDialog, QToolBar, QMessageBox, QDialog, QLabel)
from PyQt5.QtGui import QColor
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
        self.dbFilename = '/Users/Abbas/stuart.sqlite'
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
                             """

        self.toolbox = QToolBox()
        self.toolbox.setStyleSheet(styleSheet)
        layout.addWidget(self.toolbox)#, 0, 0)

        openAction = QAction('&Open', self)  # QIcon('open.png'),
        openAction.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        openAction.setShortcut('Ctrl+O')
        openAction.setStatusTip('Open database file')
        openAction.triggered.connect(self.opendbFile)

        tempHistAction = QAction('&THist', self)  # QIcon('open.png'),
        tempHistAction.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        # openAction.setShortcut('Ctrl+O')
        # openAction.setStatusTip('Open database file')
        tempHistAction.triggered.connect(self.tempHist)

        stackHistAction = QAction('&SHist', self)  # QIcon('open.png'),
        stackHistAction.setIcon(self.style().standardIcon(QStyle.SP_ArrowUp))
        stackHistAction.triggered.connect(self.stackedHist)

        odMatrixAction = QAction('&OD Matrix', self)  # QIcon('open.png'),
        odMatrixAction.setIcon(self.style().standardIcon(QStyle.SP_DesktopIcon))
        odMatrixAction.triggered.connect(self.odMatrix)

        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.addAction(openAction)
        self.toolbar.addAction(tempHistAction)
        self.toolbar.addAction(stackHistAction)
        self.toolbar.addAction(odMatrixAction)
        self.toolbar.insertSeparator(tempHistAction)
        self.addToolBar(Qt.LeftToolBarArea, self.toolbar)

        # ==================== Toolbox tabs =========================
        # Person tab
        self.newTab([Person], Person.__name__)

        # Group tab
        self.newTab([Group, GroupBelongings], Group.__name__)

        # Pedestrian tab
        self.newTab([Pedestrian, Pedestrian_obs], Pedestrian.__name__)

        # Vehicle tab
        self.newTab([Vehicle, Vehicle_obs], Vehicle.__name__)

        # Bicycles tab
        self.newTab([Bike, Bike_obs], Bike.__name__)

        # Activity tab
        self.newTab([Activity], Activity.__name__)

        # Study_site tab
        self.newTab([Study_site, Site_ODs], Study_site.__name__)


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

        newButton = QPushButton('New')
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

        addButton = QPushButton('Add to list')
        addButton.setEnabled(False)
        groupBox_layout.addWidget(addButton)

        groupBox = QGroupBox(tableClass.__name__)
        groupBox.setLayout(groupBox_layout)

        newButton.clicked.connect(lambda: self.newObject(groupBox, gridWidget, newButton, addButton))
        addButton.clicked.connect(lambda: self.addObject(groupBox, gridWidget, newButton, addButton))

        return  groupBox

    def newObject(self, grpBx, grid_wdgt, newBtn, addBtn):
        newBtn.setEnabled(False)
        grid_wdgt.setEnabled(True)
        addBtn.setEnabled(True)

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


    def addObject(self, grpBx, grid_wdgt, newBtn, addBtn):
        newBtn.setEnabled(True)
        grid_wdgt.setEnabled(False)
        addBtn.setEnabled(False)

        class_ = getattr(dbSchema, grpBx.title())

        grid_lyt = grid_wdgt.layout()
        grid_labels = [grid_lyt.itemAtPosition(i, 0).widget() for i in range(grid_lyt.rowCount())]

        i = 0
        for label in grid_labels:
            input_wdgt = grid_lyt.itemAtPosition(i, 1).widget()
            if not input_wdgt.isEnabled():
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


    def newTab(self, classList, tabName):
        wdgt = QWidget()
        layout = QVBoxLayout()

        for className in classList:
            layout.addWidget(self.generateWidgets(className))
        wdgt.setLayout(layout)
        self.toolbox.addItem(wdgt, tabName)


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

        err = tempDistHist(user=self.roadUser, od_name=self.odName)
        if err != None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText(err)
            msg.exec_()


    def stackedHist(self):
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

        err = stackedHist(user=self.roadUser, attr=self.userAttr)
        if err != None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText(err)
            msg.exec_()


    def odMatrix(self):
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

        err = odMatrix(user=self.roadUser)
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
        self.sender().parent().close()

if __name__ == '__main__':
    app = QApplication(sys.argv)

    obsTb = ObsToolbox()
    obsTb.show()

    sys.exit(app.exec_())