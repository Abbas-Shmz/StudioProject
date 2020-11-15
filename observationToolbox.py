import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QGridLayout, QVBoxLayout, QLabel,
                             QToolBox, QPushButton, QTextEdit, QLineEdit, QMainWindow,
                             QComboBox, QGroupBox)
from PyQt5.QtGui import QColor

from framework.dbSchema import createDatabase, connectDatabase, \
    Study_site, Site_ODs, Person, Pedestrian, Vehicle, Bike, \
    Activity, Group, Pedestrian_obs, Vehicle_obs, Bike_obs, \
    Passenger

from framework import dbSchema

from sqlalchemy import Enum, Boolean
from sqlalchemy.inspection import inspect


class ObsToolbox(QMainWindow):
    def __init__(self, parent=None):
        super(ObsToolbox, self).__init__(parent)
        self.resize(300, 480)
        self.dbFilename = '/Users/Abbas/stuart.sqlite'
        self.session = None
        layout = QVBoxLayout() #QGridLayout()

        self.session = createDatabase(self.dbFilename)
        if self.session is None:
            self.session = connectDatabase(self.dbFilename)

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

        # ==================== Toolbox tabs =========================
        # Person tab
        self.newTab([Person], Person.__name__)

        # Pedestrian tab
        self.newTab([Pedestrian, Pedestrian_obs], Pedestrian.__name__)

        # Vehicle tab
        self.newTab([Vehicle, Vehicle_obs], Vehicle.__name__)

        # Bicycles tab
        self.newTab([Bike, Bike_obs], Bike.__name__)


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

            if column.name in pk_list:
                is_pk = True
            else:
                is_pk = False

            columnsList.append({'name':column.name,
                               'enum': e,
                               'default': column.default.arg if column.default != None else None,
                                'is_primary_key': is_pk})
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
                # self.widgetsDict['{}_{}'.format(tableClass.__name__, column['name'])] = QComboBox()
                wdgt = QComboBox()
                wdgt.addItems(column['enum'])
                # self.widgetsDict['{}_{}'.format(tableClass.__name__, column['name'])].\
                #                                  addItems(column['enum'])
            else:
                # self.widgetsDict['{}_{}'.format(tableClass.__name__, column['name'])] = QLineEdit()
                wdgt = QLineEdit()
                if column['is_primary_key']:
                    wdgt.setReadOnly(True) #.setEnabled(False)
            # gridLayout.addWidget(self.widgetsDict['{}_{}'.format(tableClass.__name__, column['name'])], i, 1)
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
            i = i + 1

        grid_wdgt.repaint()
        # self.session.commit()


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



if __name__ == '__main__':
    app = QApplication(sys.argv)

    obsTb = ObsToolbox()
    obsTb.show()

    sys.exit(app.exec_())