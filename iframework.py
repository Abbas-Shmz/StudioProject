from enum import Enum
from pathlib import Path
from datetime import datetime

from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy import Table, Column, Integer, Boolean, String, Float, DateTime, Enum as SQLEnum, ForeignKey, \
    CheckConstraint, create_engine
from sqlalchemy.orm import relationship, backref, sessionmaker

"""

"""

Base = declarative_base()

GenderEnum = Enum('GenderEnum', 'unknown male female')
ModeEnum = Enum('ModeEnum', 'cardriver carpassenger transit taxi motorcycle cycling walking other')
VehicleEnum = Enum('VehicleEnum', 'car bike van truck bus taxi motorcycle scooter skate rollers mobility_scooter')
ActivityEnum = Enum('ActivityEnum',
                    'unknown strolling jogging shopping sitting talking resting eating playing doing_exercise smoking using_cellphone observing reading_writing performing selling playing_with_pets taking_pet_for_walk')
DisabilityEnum = Enum('DisabilityEnum', 'none Wheelchair Walker Cane While_cane')
AgeEnum = Enum('AgeEnum', 'unknown infant toddler child teen young_adult adult senior')
LineTypeEnum = Enum('LineTypeEnum', 'sidewalk roadbed cycling_path bus_lane adjoining_ZOI on_street_parking_lot')


# should there be a survey object for site info, observer, etc?

class Mode(Base):
    'personal, because in a group (family), some might have a scooter or rollers'
    __tablename__ = 'modes'
    idx = Column(Integer, primary_key=True)
    personIdx = Column(Integer, ForeignKey('persons.idx'))
    vehicleIdx = Column(Integer, ForeignKey('vehicles.idx'))
    transport = Column(SQLEnum(ModeEnum), nullable=False)
    startTime = Column(DateTime)  # None first time if only one group
    pointIdx = Column(Integer, ForeignKey('points.idx'))

    person = relationship('Person', backref=backref('modes'))
    vehicle = relationship('Vehicle')
    point = relationship('Point')

    def __init__(self, transport, person, vehicle=None, startTime=None, p=None):
        self.person = person
        self.transport = transport
        self.vehicle = vehicle
        self.startTime = startTime
        self.point = p

    @staticmethod
    def initGroup(transport, group, vehicle=None, startTime=None):
        return [Mode(transport, p, startTime) for p in group.getPersons()]


class Group(Base):
    __tablename__ = 'groups'
    idx = Column(Integer, primary_key=True)
    trajectoryDB = Column(String)
    trajectoryIdx = Column(String)

    def __init__(self, persons):
        for p in persons:
            GroupBelonging(p, self)

    def getPersons(self):
        return [gb.person for gb in self.groupBelongings]


class GroupBelonging(Base):
    __tablename__ = 'groupbelongings'
    groupIdx = Column(Integer, ForeignKey('groups.idx'), primary_key=True)
    personIdx = Column(Integer, ForeignKey('persons.idx'), primary_key=True)
    pointIdx = Column(Integer, ForeignKey('points.idx'))
    startTime = Column(DateTime)  # None first time if only one group

    person = relationship('Person', backref=backref('groupBelongings'))
    group = relationship('Group', backref=backref('groupBelongings'))
    point = relationship('Point')

    def __init__(self, person, group, startTime=None, p=None):
        self.person = person
        self.group = group
        self.startTime = startTime
        self.point = p


# in aggregated form, there is a total number of observations for a given time interval, a number for each binary variable and k-1 variables for a categorical variable with k categories
class Person(Base):
    __tablename__ = 'persons'
    idx = Column(Integer, primary_key=True)
    # groupIdx = Column(Integer, ForeignKey('groups.idx'))
    age = Column(SQLEnum(AgeEnum), nullable=True)
    gender = Column(SQLEnum(GenderEnum), nullable=False)
    disability = Column(Boolean) #Column(SQLEnum(DisabilityEnum), nullable=True)  # could be enum
    stroller = Column(Boolean)  # the booleans could be strings or enum to have more information
    bag = Column(Boolean)
    animal = Column(Boolean)

    # group = relationship('Group', backref = backref('persons'))

    def __init__(self, age='unknown', gender='unknown', disability=False, stroller=False, bag=False, animal=False):
        self.age = age
        self.gender = gender
        self.disability = disability
        self.stroller = stroller
        self.bag = bag
        self.animal = animal

    def getAgeNum(self):
        if str.isnumeric(self.age):
            return int(self.age)
        elif '.' in self.age:
            try:
                return float(self.age)
            except ValueError:
                pass
        else:
            return self.age

    def getGroups(self):
        if len(self.groupBelongings) > 0:
            return [gb.group for gb in self.groupBelongings]
        else:
            return None


class Vehicle(Base):
    __tablename__ = 'vehicles'
    idx = Column(Integer, primary_key=True)
    category = Column(SQLEnum(VehicleEnum), nullable=False)
    trailer = Column(Boolean)

    def __init__(self, category, trailer=False):
        self.category = category
        self.trailer = trailer


class Point(Base):
    __tablename__ = 'points'
    idx = Column(Integer, primary_key=True)
    x = Column(Float)
    y = Column(Float)

    def __init__(self, x, y):
        self.x = x
        self.y = y


pointLineAssociation = Table('pointlines', Base.metadata,
                             Column('pointIdx', Integer, ForeignKey('points.idx')),
                             Column('lineIdx', Integer, ForeignKey('lines.idx')))


class Line(Base):
    __tablename__ = 'lines'
    idx = Column(Integer, primary_key=True)
    name = Column(String)
    type = Column(SQLEnum(LineTypeEnum), nullable=True)
    # define lines for access counting: add type? - AccessLine?

    points = relationship('Point', secondary=pointLineAssociation)

    def __init__(self, name, type, x1, y1, x2, y2):
        self.name = name
        self.points = [Point(x1, y1), Point(x2, y2)]


pointZoneAssociation = Table('pointzones', Base.metadata,
                             Column('pointIdx', Integer, ForeignKey('points.idx')),
                             Column('zoneIdx', Integer, ForeignKey('zones.idx')))


class Zone(Base):
    __tablename__ = 'zones'
    idx = Column(Integer, primary_key=True)
    name = Column(String)
    type = Column(SQLEnum(LineTypeEnum), nullable=True)

    points = relationship('Point', secondary=pointZoneAssociation)

    def __init__(self, name, type, xs=None, ys=None):
        'xs and ys are the list of x and y coordinates'
        self.name = name
        if xs is not None and ys is not None:
            for x, y in zip(xs, ys):
                self.addPoint(x, y)

    def addPoint(self, x, y):
        self.points.append(Point(x, y))


class AbstractPassing:
    def initPersonGroupPassing(self, group, person, transport, vehicle):
        ''' initiates with the passing the group or person

        design question: what should be done about simple line counting,
        without information about persons'''
        if person is None and group is not None:  # create group
            self.group = group
            if transport is not None:
                Mode.initGroup(transport, group, vehicle)
        elif person is not None and group is None:  # create person
            self.group = Group([person])
            if transport is not None:
                Mode(transport, person, vehicle)
        else:
            print('Warning: passing person and group or both None')


class LineCrossing(AbstractPassing, Base):
    __tablename__ = 'linecrossings'
    idx = Column(Integer, primary_key=True)
    lineIdx = Column(Integer, ForeignKey('lines.idx'))
    groupIdx = Column(Integer, ForeignKey('groups.idx'))
    pointIdx = Column(Integer, ForeignKey('points.idx'))
    instant = Column(DateTime)
    speed = Column(Float)
    # wrongDirection = Column(Boolean)
    rightToLeft = Column(Boolean)

    line = relationship('Line')
    group = relationship('Group')
    point = relationship('Point')

    def __init__(self, line, instant, speed=None, wrongDirection=None, p=None, group=None, person=None, transport=None,
                 vehicle=None):
        # makes it possible to create person and mode for just counting
        # pass transport as string to instantiate after
        self.line = line
        self.instant = instant
        self.speed = speed
        self.wrongDirection = wrongDirection
        self.point = p
        self.initPersonGroupPassing(group, person, transport, vehicle)


class ZoneCrossing(AbstractPassing, Base):
    __tablename__ = 'zonecrossings'
    idx = Column(Integer, primary_key=True)
    zoneIdx = Column(Integer, ForeignKey('zones.idx'))
    groupIdx = Column(Integer, ForeignKey('groups.idx'))
    pointIdx = Column(Integer, ForeignKey('points.idx'))
    instant = Column(DateTime)
    speed = Column(Float)
    entering = Column(Boolean)

    zone = relationship('Zone')
    group = relationship('Group')
    point = relationship('Point')

    def __init__(self, zone, instant, entering, p=None, group=None, person=None, transport=None, vehicle=None):
        self.zone = zone
        self.instant = instant
        self.entering = entering
        self.point = p
        self.initPersonGroupPassing(group, person, transport, vehicle)


class Activity(AbstractPassing, Base):
    __tablename__ = 'activities'
    idx = Column(Integer, primary_key=True)
    activity = Column(SQLEnum(ActivityEnum), nullable=False)  # could be enum
    groupIdx = Column(Integer, ForeignKey('groups.idx'))
    # can an activity be done in a vehicle? Is it relevant? Can it be unambiguously identified?
    startTime = Column(DateTime)
    endTime = Column(DateTime)
    zoneIdx = Column(Integer, ForeignKey('zones.idx'))
    pointIdx = Column(Integer, ForeignKey('points.idx'))

    group = relationship('Group')
    zone = relationship('Zone')
    point = relationship('Point')

    def __init__(self, startTime, endTime, zone, activity='unknown', p=None, group=None, person=None, transport=None,
                 vehicle=None):
        self.activity = activity
        self.startTime = startTime
        self.endTime = endTime
        self.zone = zone
        self.point = p
        self.initPersonGroupPassing(group, person, transport, vehicle)


def createDatabase(filename, insertInExisting = False, createOnlyGroupTables = False):
    'creates a session to query the filename'
    if Path(filename).is_file() and not insertInExisting:
        print('The file '+filename+' exists')
        return None
    else:
        engine = create_engine('sqlite:///'+filename)
        if createOnlyGroupTables:
            Base.metadata.create_all(engine, tables = [Base.metadata.tables['modes'], Base.metadata.tables['groups'], Base.metadata.tables['groupbelongings'], Base.metadata.tables['persons'], Base.metadata.tables['vehicles'], Base.metadata.tables['points']])
        else:
            Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        return Session()

def connectDatabase(filename):
    'creates a session to query the filename'
    if Path(filename).is_file():
        engine = create_engine('sqlite:///'+filename)
        Session = sessionmaker(bind=engine)
        return Session()
    else:
        print('The file '+filename+' does not exist')
        return None


if __name__ == '__main__':  # demo code
    session = createDatabase('test.sqlite')
    if session is None:
        session = connectDatabase('test.sqlite')
    # count example
    p = Person(6, 'female', bag=True)
    veh1 = Vehicle('car')
    modes = [Mode('cardriver', p, veh1), Mode('walking', p, startTime=datetime(2020, 7, 7, 11, 20))]

    line = Line('line1', 0., 0., 0., 10.)
    zone = Zone('zone1', [0., 0., 1., 1.], [0., 1., 1., 0.])
    destination = Zone('destination1', [10., 10., 11., 11.], [10., 11., 11., 10.])
    counts = [LineCrossing(line, datetime(2020, 7, 2, 23, 20 + i), person=Person(20 + i, 'female', disability=True),
                           transport='walking') for i in range(5)]
    group1 = Group([Person(13 + i, 'female', False, False, True, False) for i in range(3)])
    groupMode1 = Mode.initGroup('walking', group1)
    activities = [Activity('walking', datetime(2020, 7, 2, 23, 0), datetime(2020, 7, 2, 23, 10), zone,
                           person=Person(40, 'male', True, False, True, False)),
                  Activity('eating', datetime(2020, 7, 2, 23, 10), datetime(2020, 7, 2, 23, 12), zone,
                           person=Person(40, 'male', True, False, True, False)),
                  Activity('playing', datetime(2020, 7, 2, 22, 0), datetime(2020, 7, 2, 23, 0), zone, group=group1)]
    counts.append(LineCrossing(line, datetime(2020, 7, 2, 23, 5), group=group1))
    counts.append(LineCrossing(line, datetime(2020, 7, 2, 23, 7), person=Person(23, 'unknown'), transport='cardriver',
                               vehicle=Vehicle('car')))
    counts.append(LineCrossing(line, datetime(2020, 7, 2, 23, 9), person=Person('teen', 'unknown'), transport='scooter',
                               vehicle=Vehicle('scooter')))
    counts.append(LineCrossing(line, datetime(2020, 7, 2, 23, 11), person=Person(12, 'female'), transport='bike'))
    counts.append(LineCrossing(line, datetime(2020, 7, 2, 23, 13), person=Person(),
                               transport='cardriver'))  # example of counting cars without knowing the driver and passenger's attributes
    counts.append(LineCrossing(line, datetime(2020, 7, 2, 23, 15), group=Group([Person(34 + i) for i in range(3)]),
                               transport='carpassenger'))

    counts.append(
        ZoneCrossing(zone, datetime(2020, 7, 7, 9, 5), True, person=Person(33, 'male', False, False, True, False)))

    session.add_all([line, p, zone, group1, destination] + modes + groupMode1 + counts + activities)

    session.commit()
    session.close()
