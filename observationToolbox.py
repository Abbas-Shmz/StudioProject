import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QGridLayout, QVBoxLayout, QLabel,
                             QToolBox, QPushButton, QTextEdit, QLineEdit, QMainWindow,
                             QComboBox, QGroupBox)
from PyQt5.QtGui import QColor

from framework.dbSchema import createDatabase, connectDatabase, \
    Study_site, Site_ODs, Person, Pedestrian, Vehicle, Bike, \
    Activity, Group, Pedestrian_obs, Vehicle_obs, Bike_obs, \
    Passenger

from sqlalchemy import Enum, Boolean


class ObsToolbox(QMainWindow):
    def __init__(self, parent=None):
        super(ObsToolbox, self).__init__(parent)
        self.resize(300, 480)
        self.dbFilename = None
        self.widgetsDict = {}
        layout = QVBoxLayout() #QGridLayout()

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

        toolbox = QToolBox()
        layout.addWidget(toolbox)#, 0, 0)

        # ==================== tab Pedestrian =========================
        w1 = QWidget()
        layout1 = QVBoxLayout()
        layout1.addWidget(self.generateWidgets(Person))
        layout1.addWidget(self.generateWidgets(Pedestrian))
        layout1.addWidget(self.generateWidgets(Pedestrian_obs))
        w1.setLayout(layout1)
        toolbox.addItem(w1, 'Pedestrian')

        # ==================== tab Vehicle =========================
        w2 = QWidget()
        layout2 = QVBoxLayout()
        layout2.addWidget(self.generateWidgets(Vehicle))
        layout2.addWidget(self.generateWidgets(Vehicle_obs))
        w2.setLayout(layout2)
        toolbox.addItem(w2, 'Vehicle')

        # ==================== tab Bicycles =========================
        w3 = QWidget()
        layout3 = QVBoxLayout()
        layout3.addWidget(self.generateWidgets(Bike))
        layout3.addWidget(self.generateWidgets(Bike_obs))
        w3.setLayout(layout3)
        toolbox.addItem(w3, 'Bicycles')


        # Create a widget for window contents
        wid = QWidget(self)
        self.setCentralWidget(wid)

        # Set widget to contain window contents
        wid.setLayout(layout)


    @staticmethod
    def getTableColumns(TableCls):
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
                               'default': column.default.arg if column.default != None else None})
        return columnsList


    def generateWidgets(self, tableClass):
        layout = QGridLayout()
        i = 0
        for column in self.getTableColumns(tableClass):
            layout.addWidget(QLabel(column['name']), i, 0)
            if column['enum'] != None:
                self.widgetsDict['{}_{}'.format(tableClass.__name__, column['name'])] = QComboBox()
                self.widgetsDict['{}_{}'.format(tableClass.__name__, column['name'])].\
                                                 addItems(column['enum'])
            else:
                self.widgetsDict['{}_{}'.format(tableClass.__name__, column['name'])] = QLineEdit()
            layout.addWidget(self.widgetsDict['{}_{}'.format(tableClass.__name__, column['name'])], i, 1)
            i = i + 1

        groupBox = QGroupBox(tableClass.__name__)
        groupBox.setLayout(layout)
        return  groupBox


if __name__ == '__main__':
    app = QApplication(sys.argv)

    obsTb = ObsToolbox()
    obsTb.show()

    sys.exit(app.exec_())