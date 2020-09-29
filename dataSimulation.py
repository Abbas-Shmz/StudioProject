#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

"""

from datetime import datetime, timedelta

from random import choice, randint, choices

from framework.dbSchema import createDatabase, connectDatabase,\
        Study_site, Site_ODs, Person, Pedestrian, Vehicle, Bike,\
            Activity
from framework import enums as en

age = [a.name for a in en.Age]
gender = [g.name for g in en.Gender]
disability = [d.name for d in en.Disability]
carryObject = [c.name for c in en.pedCarrying]
rolling = [r.name for r in en.pedRolling]
yesNo = [True, False]
activity = [a.name for a in en.activityTypes]
vehType = [v.name for v in en.vehicleTypes]


session = createDatabase('simulatedData.sqlite')
if session is None:
    session = connectDatabase('simulatedData.sqlite')


#------------------ Simulating street layout -------------------
site_1 = Study_site(id = 500, siteName = 'Jean-Talon', siteType = 'street_segment')
ods_1_1 = Site_ODs(id = 101, odType = 'sidewalk', odName = 'sidewalk_SW')
ods_1_2 = Site_ODs(id = 102, odType = 'sidewalk', odName = 'sidewalk_SE')
ods_2_1 = Site_ODs(id = 103, odType = 'sidewalk', odName = 'sidewalk_NW')
ods_2_2 = Site_ODs(id = 104, odType = 'sidewalk', odName = 'sidewalk_NE')

ods_3_1 = Site_ODs(id = 201, odType = 'road_lane', odName = 'roadway_SW')
ods_3_2 = Site_ODs(id = 202, odType = 'road_lane', odName = 'roadway_SE')
ods_4_1 = Site_ODs(id = 203, odType = 'road_lane', odName = 'roadway_NE')
ods_4_2 = Site_ODs(id = 204, odType = 'road_lane', odName = 'roadway_NW')

ods_5_1 = Site_ODs(id = 301, odType = 'cycling_path', odName = 'cycling_SW')
ods_5_2 = Site_ODs(id = 302, odType = 'cycling_path', odName = 'cycling_SW')

ods_6 = Site_ODs(id = 401, odType = 'adjoining_ZOI', zoiType = 'convenience_store', odName = 'Sam Store')
ods_7 = Site_ODs(id = 402, odType = 'adjoining_ZOI', zoiType = 'residential_building', odName = 'Richmond Bldg.')
ods_8 = Site_ODs(id = 403, odType = 'adjoining_ZOI', zoiType = 'fast_food', odName = 'McDonalds')
ods_9 = Site_ODs(id = 404, odType = 'adjoining_ZOI', zoiType = 'coffee_shop', odName = 'Tim Hortons')

site_1.ods = [ods_1_1, ods_1_2, ods_2_1, ods_2_2, ods_3_1, ods_3_2, ods_4_1, ods_4_2, ods_5_1, ods_5_2, ods_6, ods_7, ods_8, ods_9]

#----------------- START and END time of simulation ------------
start = datetime(2020, 9, 14, 7, 0, 0)
end = datetime(2020, 9, 14, 21, 0, 0)


#------------------ Simulating the moving pedestrians ----------------
pedODs = [[ods_1_1, ods_1_2], [ods_2_1, ods_2_2],
          [ods_1_2, ods_1_1], [ods_2_2, ods_2_1],
          [ods_1_1, ods_6], [ods_6, ods_1_1],
          [ods_2_1, ods_7], [ods_7, ods_2_1],
          [ods_1_2, ods_8], [ods_8, ods_1_2],
          [ods_2_2, ods_9], [ods_9, ods_2_2],
          [ods_6, ods_7], [ods_7, ods_6]]

peds = []
obsTime = start
while (obsTime < end):
    
    if obsTime.hour < 5 or obsTime.hour > 22:
        lb = 1800
        ub = 2700
    elif (obsTime.hour >= 5 and obsTime.hour < 10) or\
         (obsTime.hour >= 15 and obsTime.hour < 19):
        lb = 1
        ub = 300
    else:
        lb = 300
        ub = 900
        
    obsTime = obsTime + timedelta(seconds = randint(lb, ub))
    pedod = choice(pedODs)
    isGroup = randint(0,1)
    if isGroup:
        groupSize = randint(2,6)
    else:
        per = Person(age = choice(age), gender = choice(gender), 
                     disability = choice(disability), withBag = choice(yesNo), 
                     withPet = choice(yesNo))
        ped = Pedestrian(carryObject = choice(carryObject),
                         rolling = choice(rolling), origin = pedod[0],
                         startTime = obsTime)
        ped.person = per
        ped.destination = pedod[1]
        ped.endTime = obsTime + timedelta(seconds = randint(13, 63))
        peds.append(ped)

session.add_all(peds)

#------------------ Simulating the activities ----------------

acts = []
obsTime = start
while (obsTime < end):
    obsTime = obsTime + timedelta(seconds = randint(60, 900))
    if choices([0,1], weights=(90, 10)):  #Simulates whether we have observation
        per = Person(age = choice(age), gender = choice(gender), 
                         disability = choice(disability), withBag = choice(yesNo), 
                         withPet = choice(yesNo))
        act = Activity(activityType = choice(activity), startTime = obsTime)
        per.activity = [act]
        act.endTime = obsTime + timedelta(seconds = randint(60, 900))
        acts.append(act)

session.add_all(acts)

#------------------ Simulating the moving vehicles ----------------
vehODs = [[ods_3_1, ods_3_2], [ods_4_1, ods_4_2]]

vehs = []
obsTime = start
while (obsTime < end):
    
    if obsTime.hour < 5 or obsTime.hour > 22:
        lb = 1200
        ub = 2400
    elif (obsTime.hour >= 5 and obsTime.hour < 10) or\
         (obsTime.hour >= 15 and obsTime.hour < 19):
        lb = 1
        ub = 180
    else:
        lb = 180
        ub = 600
        
    obsTime = obsTime + timedelta(seconds = randint(lb, ub))
    vehod = choice(vehODs)
    veh = Vehicle(vehicleType = choice(vehType), origin = vehod[0],\
                  startTime = obsTime)
    veh.destination = vehod[1]
    veh.endTime = obsTime + timedelta(seconds = randint(4, 18))
    vehs.append(veh)

session.add_all(vehs)

#------------------ Simulating the moving Bikes ----------------
bikODs = [[ods_1_1, ods_1_2], [ods_2_1, ods_2_2],
          [ods_1_2, ods_1_1], [ods_2_2, ods_2_1]]\
           + vehODs + [[ods_5_1, ods_5_2]]

biks = []
obsTime = start
while (obsTime < end):

    if obsTime.hour < 5 or obsTime.hour > 22:
        lb = 2400
        ub = 3600
    elif (obsTime.hour >= 5 and obsTime.hour < 10) or\
         (obsTime.hour >= 15 and obsTime.hour < 19):
        lb = 1
        ub = 300
    else:
        lb = 600
        ub = 1200

    obsTime = obsTime + timedelta(seconds = randint(lb, ub))
    bikod = choice(bikODs)
    bik = Bike(origin = bikod[0], startTime = obsTime)
    bik.destination = bikod[1]
    bik.endTime = obsTime + timedelta(seconds = randint(7, 12))
    biks.append(bik)

session.add_all(biks)


session.commit()
session.close()

