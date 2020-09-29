#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

@author: Abbas
"""
import os

from pathlib import Path

import enums as en

from sqlalchemy import create_engine
# engine = create_engine('sqlite:///case_study_01.sqlite', echo = False)

from sqlalchemy import Table, Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship, sessionmaker

from sqlalchemy.ext.declarative import declared_attr

class Base(object):
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id =  Column(Integer, primary_key=True)

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base(cls=Base)

class ObsMixin(object):
    startTime = Column(DateTime)
    endTime = Column(DateTime)
    
    @declared_attr
    def originId(cls):
        return Column(String, ForeignKey('site_ods.id'))
    
    @declared_attr
    def destinationId(cls):
        return Column(String, ForeignKey('site_ods.id'))
    
    @declared_attr
    def origin(cls):
        return relationship('Site_ODs', uselist=False, foreign_keys = cls.originId)
    
    @declared_attr
    def destination(cls):
        return relationship('Site_ODs', uselist=False, foreign_keys = cls.destinationId)    
    
class Person(Base):
    age = Column(Enum(en.Age))
    gender = Column(Enum(en.Gender))
    race = Column(String)
    disability = Column(Enum(en.Disability), default = 'none')
    withPet = Column(Boolean, default = False)
    withBag = Column(Boolean, default = False)
    
    pedestrian = relationship('Pedestrian', uselist=False, back_populates= 'person')
    vehicle = relationship('Vehicle', uselist=False, back_populates= 'driver')
    bike = relationship('Bike', uselist=False, back_populates= 'cyclist')
    activity = relationship('Activity', back_populates= 'person')
    
    def __repr__(self):
        return "person(Id = {}, age = {}, gender = {}, disability = {})".format(self.id, self.age, self.gender, self.disability)
    
class Pedestrian(Base, ObsMixin):
    personId = Column(Integer, ForeignKey('person.id'))
    carryObject = Column(Enum(en.pedCarrying), default = 'none')
    rolling = Column(Enum(en.pedRolling), default = 'none')
    
    person = relationship('Person', back_populates= 'pedestrian')
    

class Vehicle(Base, ObsMixin):
    vehicleType = Column(Enum(en.vehicleTypes))
    noPassengers = Column(Integer)
    driverId = Column(Integer, ForeignKey('person.id'))
    noStops = Column(Integer, default = 0)
    
    driver = relationship('Person', back_populates= 'vehicle')

class Bike(Base, ObsMixin):
    bikeType = Column(String)
    cyclistId = Column(Integer, ForeignKey('person.id'))
    wearHelmet = Column(Boolean, default = True)
    
    cyclist = relationship('Person', back_populates= 'bike')
    
class Activity(Base):
    personId = Column(Integer, ForeignKey('person.id'))
    activityType = Column(Enum(en.activityTypes))
    startTime = Column(DateTime)
    endTime = Column(DateTime)
    activityLocation = Column(String)
    
    person = relationship('Person', back_populates= 'activity')

association_table = Table('groupbelongings', Base.metadata,
    Column('personId', Integer, ForeignKey('person.id')),
    Column('groupId', Integer, ForeignKey('group.id')))
    
class Group(Base):
    groupSize = Column(Integer)
    
    people = relationship('Person', secondary = association_table, back_populates="group")
    
Person.group = relationship("Group", secondary = association_table, back_populates="people")

class Study_site(Base):
    shape = Column(String)
    siteName = Column(String)
    siteType = Column(Enum(en.siteTypes))
    
    ods = relationship('Site_ODs', back_populates= 'site')
    
class Site_ODs(Base):
    siteId = Column(Integer, ForeignKey('study_site.id'))
    odType = Column(Enum(en.odTypes))
    zoiShape = Column(String)
    zoiType = Column(Enum(en.zoiTypes), default = 'NA')
    odName = Column(String)
    
    site = relationship('Study_site', back_populates = 'ods')
    

def createDatabase(filename):
    'creates a session to query the filename'
    #-------------------------------------------
    if os.path.exists(filename):
        os.remove(filename)
    #-------------------------------------------
    if Path(filename).is_file():
        print('The file '+filename+' exists')
        return None
    else:
        engine = create_engine('sqlite:///'+filename, echo = False)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        return Session()

def connectDatabase(filename):
    'creates a session to query the filename'
    if Path(filename).is_file():
        engine = create_engine('sqlite:///'+filename, echo = False)
        Session = sessionmaker(bind=engine)
        return Session()
    else:
        print('The file '+filename+' does not exist')
        return None

#======================= DEMO MODE ============================
if __name__ == '__main__': # demo code
    session = createDatabase('test.sqlite')
    if session is None:
        session = connectDatabase('test.sqlite')

    # ---------------- Sample data ---------------------------
    site_1 = Study_site(id = 500, siteName = 'Jean-Talon', siteType = 'street_segment')
    ods_1 = Site_ODs(id = 101, odType = 'sidewalk')
    ods_2 = Site_ODs(id = 102, odType = 'sidewalk')
    ods_3 = Site_ODs(id = 201, odType = 'road_lane')
    ods_4 = Site_ODs(id = 202, odType = 'road_lane')
    ods_5 = Site_ODs(id = 301, odType = 'cycling_path')
    ods_6 = Site_ODs(id = 302, odType = 'cycling_path')
    site_1.ods = [ods_1, ods_2, ods_3, ods_4, ods_5, ods_6]
    
    act_1 = Activity(activityType = 'playing')
    
    per1_1 = Person(age = 'teen', gender = 'male')
    per1_2 = Person(age = 'adult', gender = 'female')
    per2 = Person(age = 'senior', gender = 'female')
    per3 = Person(age = 'adult', gender = 'male')
    per4 = Person(age = 'senior', gender = 'unknown')
    
    ped1 = Pedestrian(carryObject = 'stroller', rolling = 'none', origin = ods_1)
    ped1.person = per1_1
    ped1.destination = ods_2
    ped1.activity = [act_1]
    
    
    ped2 = Pedestrian()
    ped2.person = per1_2
    
    grp1 = Group()
    grp1.people = [per1_1, per1_2]
    
    grp2 = Group()
    grp2.people = [per2, per4]
    
    veh1 = Vehicle(vehicleType = 'personal_car_Sedan', origin = ods_3)
    veh1.driver = per2
    veh1.destination = ods_4
    
    bik1 = Bike(bikeType = 'Automatic', origin = ods_5)
    bik1.cyclist = per3
    bik1.destination = ods_6
    #--------------------------------------------------------
    
    session.add_all([ped1, ped2, grp1, grp2, veh1, bik1])
    session.commit()
    session.close()