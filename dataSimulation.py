#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

"""

from datetime import datetime, timedelta

from random import choice, randint, choices

from framework.dbSchema import createDatabase, connectDatabase,\
        Study_site, Site_ODs, Person, Pedestrian, Vehicle, Bike,\
        Activity, Group, Pedestrian_obs, Vehicle_obs, Bike_obs,\
        Passenger

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
#--------------------------------------------------------------------
site_1 = Study_site(id = 900, siteName = 'Jean-Talon', siteType = 'street_segment')

swk_sw = Site_ODs(id = 101, odType = 'sidewalk', odName = 'sidewalk_SW')
swk_se = Site_ODs(id = 102, odType = 'sidewalk', odName = 'sidewalk_SE')
swk_nw = Site_ODs(id = 103, odType = 'sidewalk', odName = 'sidewalk_NW')
swk_ne = Site_ODs(id = 104, odType = 'sidewalk', odName = 'sidewalk_NE')

rwy_sw = Site_ODs(id = 201, odType = 'road_lane', odName = 'roadway_SW')
rwy_se = Site_ODs(id = 202, odType = 'road_lane', odName = 'roadway_SE')
rwy_ne = Site_ODs(id = 203, odType = 'road_lane', odName = 'roadway_NE')
rwy_nw = Site_ODs(id = 204, odType = 'road_lane', odName = 'roadway_NW')

cyp_sw = Site_ODs(id = 301, odType = 'cycling_path', odName = 'cycling_SW')
cyp_se = Site_ODs(id = 302, odType = 'cycling_path', odName = 'cycling_SE')

zoi_sh = Site_ODs(id = 401, odType = 'adjoining_ZOI', odName = 'Sam Store')
zoi_bg = Site_ODs(id = 402, odType = 'adjoining_ZOI', odName = 'Richmond Bldg.')
zoi_ff = Site_ODs(id = 403, odType = 'adjoining_ZOI', odName = 'McDonalds')
zoi_cf = Site_ODs(id = 404, odType = 'adjoining_ZOI', odName = 'Tim Hortons')

osp_s = Site_ODs(id = 501, odType = 'on_street_parking_lot', odName = 'parking_lot')
brk_n = Site_ODs(id = 502, odType = 'bicycle_rack', odName = 'bicycle_rack')
ibp_s = Site_ODs(id = 503, odType = 'informal_bicycle_parking', odName = 'bicycle_parking')

bus_n = Site_ODs(id = 601, odType = 'bus_stop', odName = 'bus_stop')


site_1.ods = [swk_sw, swk_se, swk_nw, swk_ne, rwy_sw, rwy_se, rwy_ne, 
              rwy_nw, cyp_sw, cyp_se, zoi_sh, zoi_bg, zoi_ff, zoi_cf,
              osp_s, brk_n, bus_n, ibp_s]

#----------------- START and END time of simulation ------------
#--------------------------------------------------------------------
simStartTime = datetime(2019, 2, 20, 7, 30, 0)
simEndTime = datetime(2019, 2, 20, 12, 30, 0)


#--------- Simulating the passing/staying pedestrians ---------------
#--------------------------------------------------------------------
pedODs = [[swk_sw, swk_se], [swk_se, swk_sw],
          [swk_nw, swk_ne], [swk_ne, swk_nw],
          [swk_sw, zoi_sh], [zoi_sh, swk_sw],
          [swk_nw, zoi_bg], [zoi_bg, swk_nw],
          [swk_se, zoi_ff], [zoi_ff, swk_se],
          [swk_ne, zoi_cf], [zoi_cf, swk_ne],
          [zoi_sh, zoi_bg], [zoi_bg, zoi_sh]]

peds_obs = []
activs = []
obsStartTime = simStartTime
while (obsStartTime < simEndTime):
    
    if obsStartTime.hour < 5 or obsStartTime.hour > 22:
        lb = 1800
        ub = 2700
    elif (obsStartTime.hour >= 5 and obsStartTime.hour < 10) or\
         (obsStartTime.hour >= 15 and obsStartTime.hour < 19):
        lb = 1
        ub = 300
    else:
        lb = 300
        ub = 900
        
    obsStartTime = obsStartTime + timedelta(seconds = randint(lb, ub))
    obsEndTime = obsStartTime + timedelta(seconds = randint(13, 63))
    
    pedod = choice(pedODs)
    isGroup = randint(0,1)
    
    if isGroup:        
        grpSize = choices(range(2,6), weights = [65, 20, 10, 5])
        grp = Group(groupSize = grpSize[0])
                
        for i in range(grpSize[0]):            
            per = Person(age = choice(age), gender = choices(gender, weights = [45, 50, 5])[0], 
                     disability = choices(disability, weights = [80, 5, 5, 5, 5])[0],  
                     withPet = choice(yesNo), withBag = choice(yesNo), group = [grp])
            ped = Pedestrian(carryObject = choice(carryObject),
                     rolling = choice(rolling), person = per)
            ped_obs1 = Pedestrian_obs(pedestrian = ped, odStatus = 'origin',
                     od = pedod[0], instant = obsStartTime)
            ped_obs2 = Pedestrian_obs(pedestrian = ped, odStatus = 'destination',
                     od = pedod[1], instant = obsEndTime)
            peds_obs = peds_obs + [ped_obs1, ped_obs1]
    else:
        per = Person(age = choice(age), gender = choices(gender, weights = [45, 50, 5])[0], 
                     disability = choices(disability, weights = [80, 5, 5, 5, 5])[0],  
                     withPet = choice(yesNo), withBag = choice(yesNo))
        ped = Pedestrian(carryObject = choice(carryObject),
                 rolling = choice(rolling), person = per)
        ped_obs1 = Pedestrian_obs(pedestrian = ped, odStatus = 'origin',
                 od = pedod[0], instant = obsStartTime)
        
        hasActivity = choices([0,1], weights = [70, 30])[0]
        if hasActivity:
            actStartTime = obsStartTime + timedelta(seconds = randint(10, 30))
            actEndTime = actStartTime + timedelta(seconds = randint(60, 900))
            act = Activity(activityType = choice(activity), 
                           startTime = actStartTime, endTime = actEndTime,
                           person = per)
            activs.append(act)
            ped_obs2 = Pedestrian_obs(pedestrian = ped, odStatus = 'destination',
                     od = pedod[1], 
                     instant = actEndTime + timedelta(seconds = randint(10, 30)))
        else:
            ped_obs2 = Pedestrian_obs(pedestrian = ped, odStatus = 'destination',
                     od = pedod[1], instant = obsEndTime)
        peds_obs = peds_obs + [ped_obs1, ped_obs2]

session.add_all(peds_obs + activs)


#------------------ Simulating the passing vehicles ----------------
#--------------------------------------------------------------------
vehODs = [[rwy_sw, rwy_se], [rwy_ne, rwy_nw]]

vehs_obs = []
obsStartTime = simStartTime
while (obsStartTime < simEndTime):
    
    if obsStartTime.hour < 5 or obsStartTime.hour > 22:
        lb = 1200
        ub = 2400
    elif (obsStartTime.hour >= 5 and obsStartTime.hour < 10) or\
          (obsStartTime.hour >= 15 and obsStartTime.hour < 19):
        lb = 1
        ub = 180
    else:
        lb = 180
        ub = 600
        
    obsStartTime = obsStartTime + timedelta(seconds = randint(lb, ub))

    vType = choices(vehType[:6], weights = [40, 40] + [5]*4)[0]
    veh = Vehicle(vehicleType = vType)
    
    vehod = choice(vehODs)
    veh_obs1 = Vehicle_obs(vehicle = veh, odStatus = 'origin', od = vehod[0], 
                     instant = obsStartTime)
    veh_obs2 = Vehicle_obs(vehicle = veh, odStatus = 'destination',od = vehod[1], 
                     instant = obsStartTime + timedelta(seconds = randint(4, 18)))
    
    vehs_obs = vehs_obs + [veh_obs1, veh_obs2]

session.add_all(vehs_obs)

#------------------ Simulating the passing Bikes ----------------
#--------------------------------------------------------------------
bikODs = [[swk_sw, swk_se], [swk_nw, swk_ne],
          [swk_se, swk_sw], [swk_ne, swk_nw]]\
            + vehODs + [[cyp_sw, cyp_se]]

biks_obs = []
obsStartTime = simStartTime
while (obsStartTime < simEndTime):

    if obsStartTime.hour < 5 or obsStartTime.hour > 22:
        lb = 2400
        ub = 3600
    elif (obsStartTime.hour >= 5 and obsStartTime.hour < 10) or\
          (obsStartTime.hour >= 15 and obsStartTime.hour < 19):
        lb = 1
        ub = 300
    else:
        lb = 600
        ub = 1200

    obsStartTime = obsStartTime + timedelta(seconds = randint(lb, ub))
    bikod = choice(bikODs)
    bik = Bike() 
    bik_obs1 = Bike_obs(bike = bik, odStatus = 'origin', od = bikod[0], 
                     instant = obsStartTime)
    bik_obs2 = Bike_obs(bike = bik, odStatus = 'destination', od = bikod[1], 
                     instant = obsStartTime + timedelta(seconds = randint(7, 12)))
    
    biks_obs = biks_obs + [bik_obs1, bik_obs2]

session.add_all(biks_obs)

#---- Scenario 1: people accessing site by car, taxi or bus ---------
#--------------------------------------------------------------------
sc1VehArrODs = [[rwy_sw, osp_s]]
sc1VehDepODs = [[osp_s, rwy_se]]
sc1PedOD = [zoi_sh, zoi_bg, zoi_ff, zoi_cf]

sc1BusArrODs = [[rwy_ne, bus_n]]
sc1BusDepODs = [[bus_n, rwy_nw]]

sc1VehsObs = []
sc1PedsObs = []
obsStartTime = simStartTime
while (obsStartTime < simEndTime):

    if obsStartTime.hour < 5 or obsStartTime.hour > 22:
        lb = 3600
        ub = 7200
    elif (obsStartTime.hour >= 5 and obsStartTime.hour < 10) or\
          (obsStartTime.hour >= 15 and obsStartTime.hour < 19):
        lb = 300
        ub = 1800
    else:
        lb = 1800
        ub = 5400

    obsStartTime = obsStartTime + timedelta(seconds = randint(lb, ub))
    
    vType = choices(vehType[:5], weights = [25, 25, 25, 20, 5])[0]

    veh = Vehicle(vehicleType = vType)
    
    per = Person(age = choice(age), gender = choices(gender, weights = [45, 50, 5])[0], 
                     disability = choices(disability, weights = [80, 5, 5, 5, 5])[0],  
                     withPet = choice(yesNo), withBag = choice(yesNo))

    if vType == 'bus':
        vehod = choice(sc1BusArrODs)
        psg = Passenger(person = per)
        veh.passengers = [psg]

    elif vType == 'taxi':
        vehod = choice(sc1VehArrODs)
        psg = Passenger(person = per)
        veh.passengers = [psg]

    else:
        vehod = choice(sc1VehArrODs)
        veh.driver = per
         
    veh_obs1 = Vehicle_obs(vehicle = veh, odStatus = 'origin', 
                     od = vehod[0], instant = obsStartTime)
    vehObsEndTime = obsStartTime + timedelta(seconds = randint(4, 18))
    veh_obs2 = Vehicle_obs(vehicle = veh, odStatus = 'destination',
                     od = vehod[1], instant = vehObsEndTime)
    
    ped = Pedestrian(carryObject = choice(carryObject), person = per)
    pedObsStartTime = vehObsEndTime + timedelta(seconds = 30)
    ped_obs1 = Pedestrian_obs(pedestrian = ped, odStatus = 'origin',
             od = vehod[1], instant = pedObsStartTime)
    pedObsEndTime = pedObsStartTime + timedelta(seconds = randint(20, 60))
    pedDest = choice(sc1PedOD)
    ped_obs2 = Pedestrian_obs(pedestrian = ped, odStatus = 'destination',
             od = pedDest, instant = pedObsEndTime)
    
    sc1VehsObs = sc1VehsObs + [veh_obs1, veh_obs2]
    sc1PedsObs = sc1PedsObs + [ped_obs1, ped_obs2]
     
session.add_all(sc1VehsObs + sc1PedsObs)

#---------- Scenario 2: people accessing site by bike -----------
#--------------------------------------------------------------------
sc2BikArrODs = [[cyp_se, brk_n]]
sc2BikDepODs = [[brk_n, cyp_sw]]
sc2PedOD = [zoi_sh, zoi_bg, zoi_ff, zoi_cf]

sc2BiksObs = []
sc2PedsObs = []
obsStartTime = simStartTime
while (obsStartTime < simEndTime):

    if obsStartTime.hour < 5 or obsStartTime.hour > 22:
        lb = 3600
        ub = 7200
    elif (obsStartTime.hour >= 5 and obsStartTime.hour < 10) or\
          (obsStartTime.hour >= 15 and obsStartTime.hour < 19):
        lb = 300
        ub = 1800
    else:
        lb = 1800
        ub = 5400

    obsStartTime = obsStartTime + timedelta(seconds = randint(lb, ub))
      
    per = Person(age = choice(age), gender = choices(gender, weights = [45, 50, 5])[0], 
                     withBag = choice(yesNo))
    
    bik = Bike(cyclist = per)
    
    bikod = choice(sc2BikArrODs)
         
    bik_obs1 = Bike_obs(bike = bik, odStatus = 'origin', 
                     od = bikod[0], instant = obsStartTime)
    bikObsEndTime = obsStartTime + timedelta(seconds = randint(10, 25))
    bik_obs2 = Bike_obs(bike = bik, odStatus = 'destination',
                     od = bikod[1], instant = bikObsEndTime)
    
    ped = Pedestrian(carryObject = choice(carryObject), person = per)
    pedObsStartTime = bikObsEndTime + timedelta(seconds = 30)
    ped_obs1 = Pedestrian_obs(pedestrian = ped, odStatus = 'origin',
             od = bikod[1], instant = pedObsStartTime)
    pedObsEndTime = pedObsStartTime + timedelta(seconds = randint(20, 60))
    pedDest = choice(sc2PedOD)
    ped_obs2 = Pedestrian_obs(pedestrian = ped, odStatus = 'destination',
             od = pedDest, instant = pedObsEndTime)
    
    sc2BiksObs = sc2BiksObs + [bik_obs1, bik_obs2]
    sc2PedsObs = sc2PedsObs + [ped_obs1, ped_obs2]
     
session.add_all(sc2BiksObs + sc2PedsObs)

session.commit()
session.close()

