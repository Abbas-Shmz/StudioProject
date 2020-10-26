#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

@author: Abbas
"""
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator

import pandas as pd
from dbSchema import connectDatabase, Pedestrian_obs,Vehicle,\
                     Person, Vehicle_obs, Bike_obs, Pedestrian,\
                     Activity, Site_ODs
import enums as en

session = connectDatabase('../simulatedData.sqlite')

#==============================================================
def tempDistHist(user, od_name):
    if user == 'pedestrians':
        q = session.query(Pedestrian_obs.instant).\
            join(Site_ODs, Pedestrian_obs.odId == Site_ODs.id).\
            filter(Site_ODs.odName == od_name)

    elif user == 'vehicles':
        q = session.query(Vehicle_obs.instant).\
            join(Site_ODs, Vehicle_obs.odId == Site_ODs.id).\
            filter(Site_ODs.odName == od_name)
    elif user == 'bikes':
        q = session.query(Bike_obs.instant).\
            join(Site_ODs, Bike_obs.odId == Site_ODs.id).\
            filter(Site_ODs.odName == od_name)
    
    if q.all() == []:
        print('No ' + user + ' passage in the ' + od_name)
        return
    time_list = [i[0] for i in q.all()]
    
    fig, ax = plt.subplots(1,1)
    ax.hist(time_list, bins=20, color='skyblue', ec='grey', rwidth = 0.9)
    
    locator = mdates.AutoDateLocator()
    ax.xaxis.set_major_locator(locator)
    
    ax.xaxis.set_minor_locator(mdates.HourLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    # print((locator()))
    
    # ax.set_xticklabels(fontsize = 6, rotation = 45)#'vertical')
    ax.tick_params(axis='x', labelsize = 8, rotation = 0)
    ax.tick_params(axis='y', labelsize = 7)
    ax.set_xlabel('Time', fontsize = 8)
    ax.set_ylabel('No. of ' + user, fontsize = 8)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_title('Temporal distribution of ' + user + ' passing from ' + od_name, fontsize = 10)
    ax.grid(True, 'major', 'y', ls='--', lw=.5, c='k', alpha=.3)
    
    ax.text(0.05, 0.95,str(time_list[0].strftime('%A, %b %d, %Y')),
            horizontalalignment='left',
            verticalalignment='center',
            transform = ax.transAxes,
            fontsize=7)
    
    plt.show()

#==============================================================
def stackedHist(user, attr, bins):
    if user == 'pedestrians':
        if attr == 'gender':
            cls_fld = Person.gender
            comp_list = [g.name for g in en.Gender]
        elif attr == 'age':
            cls_fld = Person.age
            comp_list = [a.name for a in en.Age]
        q = session.query(cls_fld).join(Pedestrian, Person.id == Pedestrian.personId).\
        distinct()
    elif user == 'vehicles':
        if attr == 'vehicleType':
            cls_fld = Vehicle.vehicleType
            comp_list = [v.name for v in en.vehicleTypes]
        q = session.query(cls_fld).distinct()
    elif user == 'activities':
        if attr == 'activityType':
            cls_fld = Activity.activityType
            comp_list = [v.name for v in en.activityTypes]
        q = session.query(cls_fld).distinct()
        
    distinct_vals = [i[0].name for i in q.all()]
    distinct_vals = sorted(distinct_vals, key=lambda x: comp_list.index(x))
    time_list = []
    for val in distinct_vals:
        if user == 'pedestrians':
            q = session.query(Pedestrian_obs.instant).\
                join(Pedestrian, Pedestrian_obs.pedestrianId == Pedestrian.id).\
                join(Person, Person.id == Pedestrian.personId).\
                filter(cls_fld == val)
        elif user == 'vehicles':
            q = session.query(Vehicle_obs.instant).\
                join(Vehicle, Vehicle_obs.vehicleId == Vehicle.id).\
                filter(cls_fld == val)
        elif user == 'activities':
            q = session.query(Activity.startTime).filter(cls_fld == val)
        
        time_list.append([i[0] for i in q.all()])
    
    fig, ax = plt.subplots(1,1)
    ax.hist(time_list, bins=bins, label=distinct_vals, ec='grey', rwidth = 0.85, stacked=True)
    
    locator = mdates.AutoDateLocator()
    ax.xaxis.set_major_locator(locator)
    
    ax.xaxis.set_minor_locator(mdates.HourLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    
    # ax.set_xticklabels(fontsize = 6, rotation = 45)#'vertical')
    ax.tick_params(axis='x', labelsize = 8, rotation = 0)
    ax.tick_params(axis='y', labelsize = 7)
    ax.set_xlabel('Time', fontsize = 8)
    ax.set_ylabel('No. of ' + user, fontsize = 8)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_title('Temporal distribution of ' + user + ' by ' + attr, fontsize = 10)
    ax.grid(True, 'major', 'y', ls='--', lw=.5, c='k', alpha=.3)
    plt.legend(loc="upper right", fontsize=7)
    
    ax.text(0.05, 0.95,str(time_list[0][0].strftime('%A, %b %d, %Y')),
      horizontalalignment='left',
      verticalalignment='center',
      transform = ax.transAxes,
      fontsize=7)
    
    plt.show()
    
#==============================================================
def odMatrix(user):
    
    if user == 'pedestrians':
        ods_list = ['sidewalk', 'adjoining_ZOI', 'bus_stop',
                    'on_street_parking_lot', 'bicycle_rack']
        cls_ = Pedestrian_obs
        cls_fld = Pedestrian_obs.pedestrianId
        
    elif user == 'cyclists':
        ods_list = ['cycling_path', 'sidewalk', 'road_lane',
                    'bus_lane', 'bicycle_rack', 'informal_bicycle_parking']
        cls_ = Bike_obs
        cls_fld = Bike_obs.bikeId
        
    elif user == 'vehicles':
        ods_list = ['road_lane', 'on_street_parking_lot', 'bus_stop']
        cls_ = Vehicle_obs
        cls_fld = Vehicle_obs.vehicleId
    
    q_ods = session.query(Site_ODs.id, Site_ODs.odType, Site_ODs.odName).\
        filter(Site_ODs.odType.in_(ods_list))
        
    ods_id = [str(i[0]) for i in q_ods.all()]
    ods_name = [str(i[2]) for i in q_ods.all()]

    od_df = pd.DataFrame(columns = ods_id, index = ods_id)
    od_df[:] = 0

    q = session.query(cls_fld, cls_.odStatus, cls_.odId)
    
    user_od_dict = {}
    for rec in q.all():
        if rec[0] in user_od_dict.keys():
            if rec[1] == 'origin':
                user_od_dict[rec[0]][0] = rec[2]
            else:
                user_od_dict[rec[0]][1] = rec[2]
        else:
            user_od_dict[rec[0]] = [None, None]
            if rec[1] == 'origin':
                user_od_dict[rec[0]][0] = rec[2]
            else:
                user_od_dict[rec[0]][1] = rec[2]
                
    for od in user_od_dict.values():
        od_df.loc[od[0], od[1]] = od_df.loc[od[0], od[1]] + 1
        
    od_df = od_df.apply(pd.to_numeric)
    
    org_sum = [str(i) for i in od_df.sum(1).values]
    dst_sum = [str(i) for i in od_df.sum(0).values]
    
    plt.matshow(od_df, cmap=plt.cm.coolwarm)
    plt.xticks(range(len(ods_name)), ods_name , fontsize = 7, rotation= 90, weight="bold");
    plt.yticks(range(len(ods_name)), ods_name , fontsize = 7, weight="bold");
    # plt.colorbar()
    # plt.table(cellText = dst_sum,loc = 'bottom', cellLoc = 'center')
    # plt.table(cellText = org_sum,loc = 'right', cellLoc = 'center')
    
    for i in range(len(ods_name)):
        plt.text(len(ods_name) - 0.3, i, org_sum[i], va='center', ha='left')
        plt.text(i, len(ods_name) - 0.2, dst_sum[i], va='center', ha='center')
    
    for i in range(0,od_df.shape[0]):
        for j in range(0,od_df.shape[0]):
            c = od_df.iat[j,i]
            plt.text(i, j, str(c), va='center', ha='center', fontsize = 7, weight="bold", color = 'k')

    plt.show()
    
#======================= DEMO MODE ============================
if __name__ == '__main__':
    # tempDistHist(user = 'pedestrians', od_name = 'sidewalk_SW')
    # stackedHist('vehicles', 'vehicleType', 20)
    odMatrix(user = 'pedestrians')