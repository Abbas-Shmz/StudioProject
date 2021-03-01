#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

@author: Abbas
"""
import os

from pathlib import Path

from framework import enums as en

from sqlalchemy import create_engine
# engine = create_engine('sqlite:///case_study_01.sqlite', echo = False)

from sqlalchemy import Table, Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship, sessionmaker

from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.declarative import declarative_base


class Base(object):
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = Column(Integer, primary_key=True)


Base = declarative_base(cls=Base)


class ObsMixin(object):
    # odStatus = Column(String)
    instant = Column(DateTime)
    # speed = Column(Integer)
    # location = Column(String)

    @declared_attr
    def originId(cls):
        return Column(String, ForeignKey('site_ods.id'))

    @declared_attr
    def destinationId(cls):
        return Column(String, ForeignKey('site_ods.id'))

    @declared_attr
    def origin(cls):
        return relationship('Site_ODs', foreign_keys=cls.originId)

    @declared_attr
    def destination(cls):
        return relationship('Site_ODs', foreign_keys=cls.destinationId)


class Person(Base):
    age = Column(Enum(en.Age))
    gender = Column(Enum(en.Gender))
    race = Column(String)
    disability = Column(Enum(en.Disability), default='none')
    withBag = Column(Boolean, default=False)
    withPet = Column(Boolean, default=False)

    pedestrian = relationship('Pedestrian', uselist=False, back_populates='person')
    # vehicle = relationship('Vehicle', uselist=False, back_populates='driver')
    # bike = relationship('Bike', uselist=False, back_populates='cyclist')
    activity = relationship('Activity', back_populates='person')
    # passenger = relationship('Passenger', uselist=False, back_populates='person')

    def __repr__(self):
        return "person(Id = {}, age = {}, gender = {}, disability = {})".format(self.id, self.age, self.gender,
                                                                                self.disability)


class Pedestrian(Base):
    personId = Column(Integer, ForeignKey('person.id'))
    carryObject = Column(Enum(en.pedCarrying), default='none')
    rolling = Column(Enum(en.pedRolling), default='none')

    person = relationship('Person', back_populates='pedestrian')
    observation = relationship('Pedestrian_obs', back_populates='pedestrian')


class Vehicle(Base):
    vehicleType = Column(Enum(en.vehicleTypes))
    # noPassengers = Column(Integer)
    # driverId = Column(Integer, ForeignKey('person.id'))
    hasTrailer = Column(Boolean)

    # driver = relationship('Person', back_populates='vehicle')
    observation = relationship('Vehicle_obs', back_populates='vehicle')
    # passengers = relationship('Passenger', back_populates='vehicle')


class Bike(Base):
    bikeType = Column(String)
    # cyclistId = Column(Integer, ForeignKey('person.id'))
    hasTrailer = Column(Boolean)

    # cyclist = relationship('Person', back_populates='bike')
    observation = relationship('Bike_obs', back_populates='bike')


# class Passenger(Base):
#     vehicleId = Column(Integer, ForeignKey('vehicle.id'))
#     personId = Column(Integer, ForeignKey('person.id'))
#
#     vehicle = relationship('Vehicle', back_populates='passengers')
#     person = relationship('Person', back_populates='passenger')


class Pedestrian_obs(Base, ObsMixin):
    pedestrianId = Column(Integer, ForeignKey('pedestrian.id'))

    pedestrian = relationship('Pedestrian', back_populates='observation')


class Vehicle_obs(Base, ObsMixin):
    vehicleId = Column(Integer, ForeignKey('vehicle.id'))
    delayed = Column(Boolean)
    # noStops = Column(Integer, default=0)
    hasStop = Column(Enum(en.stopActions))

    vehicle = relationship('Vehicle', back_populates='observation')


class Bike_obs(Base, ObsMixin):
    bikeId = Column(Integer, ForeignKey('bike.id'))
    wearHelmet = Column(Boolean)
    carryPerson = Column(Boolean)
    carryObject = Column(Boolean)

    bike = relationship('Bike', back_populates='observation')


class Activity(Base):
    personId = Column(Integer, ForeignKey('person.id'))
    activityType = Column(Enum(en.activityTypes))
    startTime = Column(DateTime)
    endTime = Column(DateTime)
    activityLocation = Column(String)
    siteId = Column(Integer, ForeignKey('study_site.id'))

    person = relationship('Person', back_populates='activity')
    site = relationship('Study_site', back_populates='activities')


# association_table = Table('groupbelongings', Base.metadata,
#                           Column('personId', Integer, ForeignKey('person.id')),
#                           Column('groupId', Integer, ForeignKey('group.id')))

class GroupBelongings(Base):
    groupId = Column(Integer, ForeignKey('group.id'))
    personId = Column(Integer, ForeignKey('person.id'))

association_table = GroupBelongings.__table__


class Group(Base):
    groupSize = Column(Integer)

    people = relationship('Person', secondary=association_table, back_populates="group")


Person.group = relationship("Group", secondary=association_table, back_populates="people")


class Study_site(Base):
    shape = Column(String)
    siteName = Column(String)
    siteType = Column(Enum(en.siteTypes))
    obsStart = Column(DateTime)
    obsEnd = Column(DateTime)
    obsvrLoc = Column(String)

    ods = relationship('Site_ODs', back_populates='site')
    activities = relationship('Activity', back_populates='site')


class Site_ODs(Base):
    siteId = Column(Integer, ForeignKey('study_site.id'))
    odType = Column(Enum(en.odTypes))
    shape = Column(String)
    # zoiType = Column(Enum(en.zoiTypes), default = 'NA')
    odName = Column(String)
    direction = Column(Enum(en.OdDirection))

    site = relationship('Study_site', back_populates='ods')


def createDatabase(filename):
    'creates a session to query the filename'
    # -------------------------------------------
    # if os.path.exists(filename):
    #     os.remove(filename)
    # -------------------------------------------
    if Path(filename).is_file():
        print('The file ' + filename + ' exists')
        return None
    else:
        engine = create_engine('sqlite:///' + filename, echo=False)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        return Session()


def connectDatabase(filename):
    'creates a session to query the filename'
    if Path(filename).is_file():
        engine = create_engine('sqlite:///' + filename, echo=False)
        Session = sessionmaker(bind=engine)
        return Session()
    else:
        print('The file ' + filename + ' does not exist')
        return None


# ======================= DEMO MODE ============================
if __name__ == '__main__':  # demo code
    session = createDatabase('test.sqlite')
    if session is None:
        session = connectDatabase('test.sqlite')
