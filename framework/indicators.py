#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

@author: Abbas
"""
import numpy as np
import datetime
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator
from sqlalchemy import func

import pandas as pd
from framework import dbSchema
from framework.dbSchema import connectDatabase, Pedestrian_obs, Vehicle, Person, Bike, \
    Vehicle_obs, Bike_obs, Pedestrian, Activity, Site_ODs, Study_site
from framework import enums as en

# session = connectDatabase('/Users/Abbas/stuart.sqlite')


# ==============================================================
def tempDistHist(user, od_name, direction, ax, session, bins=20, alpha=1, color='skyblue', ec='grey',
                 label=None, rwidth=0.9, histtype='bar', comparison = False):
    cls_obs = getattr(dbSchema, user + '_obs')

    time_list = []
    for ods in direction:
        q = session.query(cls_obs.instant).\
            filter(cls_obs.originId == ods[0]). \
            filter(cls_obs.destinationId == ods[1])

        time_list = time_list + [i[0] for i in q.all()]

    if time_list == []:
        return 'No {} is observed in {} for the selected direction(s)!'.format(user, od_name)

    # if user == 'pedestrian':
    #     q1 = session.query(Pedestrian_obs.instant). \
    #         join(Site_ODs, Pedestrian_obs.originId == Site_ODs.id). \
    #         filter(Site_ODs.odName == od_name)
    #
    #     q2 = session.query(Pedestrian_obs.instant). \
    #         join(Site_ODs, Pedestrian_obs.destinationId == Site_ODs.id). \
    #         filter(Site_ODs.odName == od_name)
    #
    # elif user == 'vehicle':
    #     q1 = session.query(Vehicle_obs.instant). \
    #         join(Site_ODs, Vehicle_obs.originId == Site_ODs.id). \
    #         filter(Site_ODs.odName == od_name)
    #
    #     q2 = session.query(Vehicle_obs.instant). \
    #         join(Site_ODs, Vehicle_obs.destinationId == Site_ODs.id). \
    #         filter(Site_ODs.odName == od_name)
    #
    # elif user == 'cyclist':
    #     q1 = session.query(Bike_obs.instant). \
    #         join(Site_ODs, Bike_obs.originId == Site_ODs.id). \
    #         filter(Site_ODs.odName == od_name)
    #
    #     q2 = session.query(Bike_obs.instant). \
    #         join(Site_ODs, Bike_obs.destinationId == Site_ODs.id). \
    #         filter(Site_ODs.odName == od_name)
    #
    # if q1.all() == [] and q2.all() == []:
    #     return 'No {} is observed passing through the {} section!'.format(user, od_name)
    #
    # time_list = [i[0] for i in q1.all()] + [i[0] for i in q2.all()]

    if comparison:
        i = 0
        for t in time_list:
            time_list[i] = datetime.datetime(2000,1,1,t.hour, t.minute, t.second)
            i += 1

    # fig = plt.figure()#figsize=(5, 5), dpi=200, tight_layout=True)
    # ax = fig.add_subplot(111) #plt.subplots(1, 1)
    ax.hist(time_list, bins=bins, color=color, ec=ec, rwidth=rwidth, alpha=alpha, label=label,
            histtype=histtype)

    locator = mdates.AutoDateLocator()
    ax.xaxis.set_major_locator(locator)

    ax.xaxis.set_minor_locator(mdates.HourLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    # print((locator()))

    # ax.set_xticklabels(fontsize = 6, rotation = 45)#'vertical')
    ax.tick_params(axis='x', labelsize=8, rotation=0)
    ax.tick_params(axis='y', labelsize=7)
    ax.set_xlabel('Time', fontsize=8)
    ax.set_ylabel('No. of ' + user, fontsize=8)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_title('Temporal distribution of ' + user + ' passings from ' + od_name, fontsize=10)
    ax.grid(True, 'major', 'y', ls='--', lw=.5, c='k', alpha=.3)

    if not comparison:
        ax.text(0.05, 0.95, str(time_list[0].strftime('%A, %b %d, %Y')),
                horizontalalignment='left',
                verticalalignment='center',
                transform=ax.transAxes,
                fontsize=8)

    ax.text(0.03, 0.03, str('StudioProject'),
            fontsize=10, color='gray',
            ha='left', va='bottom',
            transform=ax.transAxes,
            weight="bold", alpha=.5)

    # plt.show()

# ==============================================================
def stackedHist(user, attr, ax, session, bins=20):
    if user == 'pedestrian':
        if attr == 'gender':
            cls_fld = Person.gender
            comp_list = [g.name for g in en.Gender]
        elif attr == 'age':
            cls_fld = Person.age
            comp_list = [a.name for a in en.Age]
        else:
            return 'ERROR: The argument is not correct!'

        q = session.query(cls_fld).join(Pedestrian, Person.id == Pedestrian.personId). \
            distinct()
    elif user == 'vehicle':
        if attr == 'vehicleType':
            cls_fld = Vehicle.vehicleType
            comp_list = [v.name for v in en.vehicleTypes]
        else:
            return 'ERROR: The argument is not correct!'
        q = session.query(cls_fld).distinct()
    elif user == 'activities':
        if attr == 'activityType':
            cls_fld = Activity.activityType
            comp_list = [v.name for v in en.activityTypes]
        else:
            return 'ERROR: The argument is not correct!'
        q = session.query(cls_fld).distinct()

    if q.all() == []:
        return 'There is no observation for {} of {}!'.format(attr, user)

    distinct_vals = [i[0].name for i in q.all()]
    distinct_vals = sorted(distinct_vals, key=lambda x: comp_list.index(x))
    time_list = []
    for val in distinct_vals:
        if user == 'pedestrian':
            q = session.query(Pedestrian_obs.instant). \
                join(Pedestrian, Pedestrian_obs.pedestrianId == Pedestrian.id). \
                join(Person, Person.id == Pedestrian.personId). \
                filter(cls_fld == val)
        elif user == 'vehicle':
            q = session.query(Vehicle_obs.instant). \
                join(Vehicle, Vehicle_obs.vehicleId == Vehicle.id). \
                filter(cls_fld == val)
        elif user == 'activities':
            q = session.query(Activity.startTime).filter(cls_fld == val)
        else:
            return 'ERROR: The argument is not correct!'


        time_list.append([i[0] for i in q.all()])

    # fig, ax = plt.subplots(1, 1)
    ax.hist(time_list, bins=bins, label=distinct_vals, ec='grey', rwidth=0.85, stacked=True)

    locator = mdates.AutoDateLocator()
    ax.xaxis.set_major_locator(locator)

    ax.xaxis.set_minor_locator(mdates.HourLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

    # ax.set_xticklabels(fontsize = 6, rotation = 45)#'vertical')
    ax.tick_params(axis='x', labelsize=8, rotation=0)
    ax.tick_params(axis='y', labelsize=7)
    ax.set_xlabel('Time', fontsize=8)
    ax.set_ylabel('No. of ' + user, fontsize=8)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_title('Temporal distribution of ' + user + ' by ' + attr, fontsize=10)
    ax.grid(True, 'major', 'y', ls='--', lw=.5, c='k', alpha=.3)
    plt.legend(loc="upper right", fontsize=7)

    ax.text(0.05, 0.95, str(time_list[0][0].strftime('%A, %b %d, %Y')),
            horizontalalignment='left',
            verticalalignment='center',
            transform=ax.transAxes,
            fontsize=7)

    ax.text(0.03, 0.03, str('StudioProject'),
            fontsize=10, color='gray',
            ha='left', va='bottom',
            transform=ax.transAxes,
            weight="bold", alpha=.5)

    # plt.show()

# ==============================================================
def odMatrix(user, ax, session):
    if user == 'pedestrian':
        cls_ = Pedestrian_obs
        cls_fld = Pedestrian_obs.pedestrianId
        cbarlabel = 'No. of pedestrians'
        valfmt = "{x:.1f}"

    elif user == 'cyclist':
        cls_ = Bike_obs
        cls_fld = Bike_obs.bikeId
        cbarlabel = 'No. of cyclists'
        valfmt = "{x:.1f}"

    elif user == 'vehicle':
        cls_ = Vehicle_obs
        cls_fld = Vehicle_obs.vehicleId
        cbarlabel = 'No. of vehicles'
        valfmt = "{x:.1f}"

    else:
        return 'ERROR: The argument is not correct!'

    q_ods = session.query(Site_ODs.id, Site_ODs.odName)

    if q_ods.all() == []:
        return 'There is no data for ODs!'

    ods_id = [str(i[0]) for i in q_ods.all()]
    ods_name = [str(i[1]) for i in q_ods.all()]

    od_df = pd.DataFrame(columns=ods_id, index=ods_id)
    od_df[:] = 0

    q = session.query(cls_fld, cls_.originId, cls_.destinationId)

    site_instance = session.query(Study_site).first()
    start_obs_time = site_instance.obsStart
    end_obs_time = site_instance.obsEnd
    duration = end_obs_time - start_obs_time
    duration_in_s = duration.total_seconds()
    duration_hours = duration_in_s/3600

    if q.all() == []:
        return 'There is no observation for {}!'.format(user)

    user_od_dict = {}
    for rec in q.all():
        if not rec[0] in user_od_dict.keys():
            user_od_dict[rec[0]] = [None, None]

        if rec[1] == '' and rec[2] != '':
            user_od_dict[rec[0]][1] = rec[2]
        elif rec[1] != '' and rec[2] == '':
            user_od_dict[rec[0]][0] = rec[1]
        elif rec[1] != '' and rec[2] != '':
            user_od_dict[rec[0]][0] = rec[1]
            user_od_dict[rec[0]][1] = rec[2]
        else:
            continue

    for od in user_od_dict.values():
        od_df.loc[od[0], od[1]] = od_df.loc[od[0], od[1]] + 1

    od_df = od_df.apply(pd.to_numeric)

    org_sum = [i for i in od_df.sum(1).values]
    dst_sum = [i for i in od_df.sum(0).values]

    indices_zero = [i for i, x in enumerate([sum(s) for s in zip(org_sum, dst_sum)]) if x == 0]
    indices_toDrop = od_df.index[indices_zero]
    od_df.drop(index=indices_toDrop, inplace=True)
    od_df.drop(columns=indices_toDrop, inplace=True)

    ids_toRemove = []
    names_toRemove = []
    for idx in indices_zero:
        ids_toRemove.append(ods_id[idx])
        names_toRemove.append(ods_name[idx])
    for i in range(len(ids_toRemove)):
        ods_id.remove(ids_toRemove[i])
        ods_name.remove(names_toRemove[i])

    data = od_df/duration_hours
    data = data.to_numpy()

    ticks = ['{}\n(ID: {})'.format(ods_name[i], ods_id[i]) for i in range(len(ods_name))]

    im, cbar = heatmap(od_df, ticks, ticks, ax=ax,
                       cmap="Wistia", cbarlabel=cbarlabel) #, cbar  "YlGn"
    texts = annotate_heatmap(im, data=data, valfmt=valfmt)


    # ax.matshow(od_df, cmap=plt.cm.coolwarm)
    # plt.xticks(range(len(ods_name)), ticks, fontsize=7, rotation=90, weight="bold")
    # plt.yticks(range(len(ods_name)), ticks, fontsize=7, weight="bold")
    # plt.tick_params(bottom=False, left=False, right=False, top=False)
    #
    # plt.text(len(ods_name) - 0.4, len(ods_name) - 0.3, od_df.values.sum(), va='center', ha='left',
    #          fontsize=8, weight="bold")
    # # plt.colorbar()
    # # plt.table(cellText = dst_sum,loc = 'bottom', cellLoc = 'center')
    # # plt.table(cellText = org_sum,loc = 'right', cellLoc = 'center')
    #
    # for i in range(len(ods_name)):
    #     plt.text(len(ods_name) - 0.4, i, org_sum[i], va='center', ha='left', fontsize=8)
    #     plt.text(i, len(ods_name) - 0.3, dst_sum[i], va='center', ha='center', fontsize=8)
    #
    # for i in range(0, od_df.shape[0]):
    #     for j in range(0, od_df.shape[0]):
    #         c = od_df.iat[j, i]
    #         plt.text(i, j, str(c), va='center', ha='center', fontsize=8, weight="bold", color='k')
    #
    # plt.show()

#=====================================================================
def pieChart(user, attr, startTime, endTime, ax, session):
    if user == 'All users':
        ped_count = session.query(Pedestrian_obs.id).filter(Pedestrian_obs.instant >= startTime)\
                                                 .filter(Pedestrian_obs.instant <= endTime)\
                                                 .filter(Pedestrian_obs.destinationId != '').count()
        veh_count = session.query(Vehicle_obs.id).filter(Vehicle_obs.instant >= startTime)\
                                                 .filter(Vehicle_obs.instant <= endTime)\
                                                 .filter(Vehicle_obs.destinationId != '').count()
        bik_count = session.query(Bike_obs.id).filter(Bike_obs.instant >= startTime)\
                                                 .filter(Bike_obs.instant <= endTime)\
                                                 .filter(Bike_obs.destinationId != '').count()

        all_count = ped_count + veh_count + bik_count
        ped_pct = round((ped_count / all_count) * 100, 1)
        veh_pct = round((veh_count / all_count) * 100, 1)
        bik_pct = round((bik_count / all_count) * 100, 1)

        labels = 'Pedestrian', 'Vehicle', 'Bike'
        sizes = [ped_pct, veh_pct, bik_pct]
        explode = [0.01, 0.01, 0.01]  # only "explode" the 2nd slice
    else:
        labels, sizes = getLabelSizePie(user, attr, startTime, endTime, session)
        explode = [0.01]*len(labels)

    wedges, texts, autotexts = ax.pie(sizes, explode=explode, labels=labels, autopct='%1.1f%%',
                                      shadow=False, startangle=90, textprops={'size': 8})

    ax.axis('equal')
    # ax.legend(wedges, labels,
    #           title="title",
    #           loc="upper right")

    plt.setp(autotexts, size=8, weight="bold")

#=====================================================================
def generateReport(subj, session):
    indicatorsList = []

    site_instance = session.query(Study_site).first()
    start_obs_time = site_instance.obsStart
    end_obs_time = site_instance.obsEnd
    duration = end_obs_time - start_obs_time
    duration_in_s = duration.total_seconds()
    duration_hours = duration_in_s / 3600

    if subj in ['Pedestrian', 'Vehicle', 'Bike']:
        cls_ = getattr(dbSchema, subj)
        cls_obs = getattr(dbSchema, subj+'_obs')
        cls_obs_fld = getattr(cls_obs, subj.lower()+'Id')
        q = session.query(cls_obs_fld).distinct()
        no_all_users = q.count()

        if no_all_users == 0:
            return None

        flow = round(no_all_users/duration_hours, 1)

        indicatorDict = {}
        indicatorDict['Indicator'] = 'No. of all {}s'.format(subj.lower())
        indicatorDict['Value'] = str(no_all_users)
        indicatorDict['Percent(%)'] = '{}'.format(100)
        indicatorDict['Flow ({}/h)'.format(subj[:3].lower())] = '{}'.format(flow)
        indicatorsList.append(indicatorDict)

        morningPeakStart = datetime.time(7,0)
        morningPeakEnd = datetime.time(9, 0)
        eveningPeakStart = datetime.time(15, 0)
        eveningPeakEnd = datetime.time(19, 0)

        peakHours = {}
        if start_obs_time.time() < morningPeakStart:
            peakHours['Morning peak'] = [morningPeakStart, morningPeakEnd]
            peakHours['Off-peak'] = [morningPeakEnd, eveningPeakStart]
            peakHours['Evening peak'] = [eveningPeakStart, eveningPeakEnd]

        elif morningPeakStart < start_obs_time.time() < morningPeakEnd:
            peakHours['Morning peak'] = [start_obs_time.time(), morningPeakEnd]
            peakHours['Off-peak'] = [morningPeakEnd, eveningPeakStart]
            peakHours['Evening peak'] = [eveningPeakStart, eveningPeakEnd]

        elif morningPeakEnd < start_obs_time.time() < eveningPeakStart:
            peakHours['Morning peak'] = None
            peakHours['Off-peak'] = [start_obs_time.time(), eveningPeakStart]
            peakHours['Evening peak'] = [eveningPeakStart, eveningPeakEnd]

        elif eveningPeakStart < start_obs_time.time() < eveningPeakEnd:
            peakHours['Morning peak'] = None
            peakHours['Off-peak'] = None
            peakHours['Evening peak'] = [start_obs_time.time(), eveningPeakEnd]

        if eveningPeakStart < end_obs_time.time() < eveningPeakEnd:
            peakHours['Evening peak'][1] = end_obs_time.time()

        elif morningPeakEnd < end_obs_time.time() < eveningPeakStart:
            peakHours['Evening peak'] = None
            peakHours['Off-peak'][1] = end_obs_time.time()

        elif morningPeakStart < end_obs_time.time() < morningPeakEnd:
            peakHours['Evening peak'] = None
            peakHours['Off-peak'] = None
            peakHours['Morning peak'][1] = end_obs_time.time()

        for p in peakHours.keys():
            if peakHours[p] == None:
                no_users = 'No Data'
                percent = 'No Data'
                flow = 'No Data'
                duration_text = ''
            else:
                y = start_obs_time.year
                m = start_obs_time.month
                d = start_obs_time.day
                lh = peakHours[p][0].hour
                lm = peakHours[p][0].minute
                ls = peakHours[p][0].second
                uh = peakHours[p][1].hour
                um = peakHours[p][1].minute
                us = peakHours[p][1].second
                ums = peakHours[p][1].microsecond
                lowerBound = datetime.datetime(y, m, d, lh, lm, ls)
                upperBound = datetime.datetime(y, m, d, uh, um, us, ums)
                q = session.query(cls_obs).filter(cls_obs.instant >= lowerBound)\
                                          .filter(cls_obs.instant <= upperBound)
                no_users = q.count()
                percent = round((no_users/no_all_users)*100, 1)
                duration = (peakHours[p][1].hour + peakHours[p][1].minute / 60) - \
                           (peakHours[p][0].hour + peakHours[p][0].minute / 60)
                flow = round(no_users / duration, 1)
                duration_text = '({}-{})'.format(peakHours[p][0].strftime('%I:%M %p'),
                                                 peakHours[p][1].strftime('%I:%M %p'))

            indicatorDict = {}
            indicatorDict['Indicator'] = '{} {}'.format(p, duration_text)
            indicatorDict['Value'] = str(no_users)
            indicatorDict['Percent(%)'] = '{}'.format(percent)
            indicatorDict['Flow ({}/h)'.format(subj[:3].lower())] = '{}'.format(flow)
            indicatorsList.append(indicatorDict)

    if subj == 'Bike':
        q = session.query(Bike_obs.originId, Bike_obs.destinationId)
        q_swk = session.query(Site_ODs.id).filter(Site_ODs.odType == 'sidewalk')
        swk_ids = [int(i[0]) for i in q_swk.all()]

        biks_on_swk = 0
        for rec in q.all():
            if int(rec[0]) in swk_ids or int(rec[1]) in swk_ids:
                biks_on_swk += 1

        flow = round(biks_on_swk / duration_hours, 1)

        indicatorDict = {}
        indicatorDict['Indicator'] = 'No. of cyclists riding on sidewalk'
        indicatorDict['Value'] = '{}'.format(biks_on_swk)
        indicatorDict['Percent(%)'] = '{}'.format(round(biks_on_swk / q.count() * 100, 1))
        indicatorDict['Flow ({}/h)'.format(subj[:3].lower())] = '{}'.format(flow)
        indicatorsList.append(indicatorDict)


        q_against = session.query(Bike_obs.originId).join(Site_ODs, Bike_obs.originId == Site_ODs.id).\
                    filter(Site_ODs.direction == 'end_point')

        biks_against = q_against.count()

        flow = round(biks_against / duration_hours, 1)

        indicatorDict = {}
        indicatorDict['Indicator'] = 'No. of cyclists riding against traffic'
        indicatorDict['Value'] = '{}'.format(biks_against)
        indicatorDict['Percent(%)'] = '{}'.format(round(biks_against / q.count() * 100, 1))
        indicatorDict['Flow ({}/h)'.format(subj[:3].lower())] = '{}'.format(flow)
        indicatorsList.append(indicatorDict)

    if subj == 'Activity':
        q = session.query(Activity.activityType, Activity.startTime, Activity.endTime)

        activity_dict = {}
        for act in q.all():
            act_type = act[0].name
            if act_type in activity_dict.keys():
                activity_dict[act_type]['count'] += 1
                activity_dict[act_type]['actTotalTime'] += (act[2] - act[1]).total_seconds()
            else:
                activity_dict[act_type] = {'count':1, 'actTotalTime':(act[2] - act[1]).total_seconds()}

        total_acts = 0
        total_time = 0
        for val in activity_dict.values():
            total_acts += val['count']
            total_time += val['actTotalTime']

        indicatorDict = {}
        indicatorDict['Indicator'] = 'No. of all activities'
        indicatorDict['Value'] = '{}'.format(total_acts)
        indicatorDict['Percent(%)'] = '{}'.format(100)
        if total_time > 0:
            indicatorDict['Total time (min.)'] = '{}'.format(round(total_time/60, 1))
            indicatorDict['Avg. time (min.)'] = '{}'.format(round(total_time/(60*total_acts), 1))
        else:
            indicatorDict['Total time (min.)'] = 'NA'
            indicatorDict['Avg. time (min.)'] = 'NA'
        indicatorDict['Rate (act/h)'] = '{}'.format(round(total_acts/duration_hours, 1))
        indicatorsList.append(indicatorDict)

        # field_ = Activity.activityType
        # q = session.query(field_, func.count(field_)).group_by(field_)
        # actTypes = [[i[0].name, int(i[1])] for i in q.all()]

        for act in activity_dict.keys():
            act_count = activity_dict[act]['count']
            act_totalTime_min = activity_dict[act]['actTotalTime']/60
            indicatorDict = {}
            indicatorDict['Indicator'] = 'No. of people {}'.format(act)
            indicatorDict['Value'] = '{}'.format(act_count)
            indicatorDict['Percent(%)'] = '{}'.format(round((act_count/total_acts)*100, 1))
            if act_totalTime_min > 0:
                indicatorDict['Total time (min.)'] = '{}'.format(round(act_totalTime_min, 1))
                indicatorDict['Avg. time (min.)'] = '{}'.format(round(act_totalTime_min/act_count,1))
            else:
                indicatorDict['Total time (min.)'] = 'NA'
                indicatorDict['Avg. time (min.)'] = 'NA'
            indicatorDict['Rate (act/h)'] = '{}'.format(round(act_count/duration_hours,1))
            indicatorsList.append(indicatorDict)

    if subj == 'Access':
        q = session.query(Vehicle_obs.id).join(Site_ODs, Vehicle_obs.destinationId == Site_ODs.id).\
            filter(Site_ODs.odType == 'on_street_parking_lot')
        no_arriv_vehs = q.count()
        flow = round(no_arriv_vehs/duration_hours, 1)
        indicatorDict = {}
        indicatorDict['Indicator'] = 'No. of arriving vehicles'
        indicatorDict['Value'] = '{}'.format(no_arriv_vehs)
        indicatorDict['Percent(%)'] = '{}'.format(100)
        indicatorDict['Flow'] = '{} ({}/h)'.format(flow, 'veh')
        indicatorsList.append(indicatorDict)

        q = session.query(Vehicle_obs.id).join(Site_ODs, Vehicle_obs.originId == Site_ODs.id). \
            filter(Site_ODs.odType == 'on_street_parking_lot')
        no_depart_vehs = q.count()
        flow = round(no_depart_vehs / duration_hours, 1)
        indicatorDict = {}
        indicatorDict['Indicator'] = 'No. of departing vehicles'
        indicatorDict['Value'] = '{}'.format(no_depart_vehs)
        indicatorDict['Percent(%)'] = '{}'.format(100)
        indicatorDict['Flow'] = '{} ({}/h)'.format(flow, 'veh')
        indicatorsList.append(indicatorDict)

    return indicatorsList




def getLabelSizePie(className, fieldName, startTime, endTime, session):
    if className in ['Pedestrian', 'Vehicle', 'Bike']:
        className = className+'_obs'
    class_ = getattr(dbSchema, className)
    if className == 'Pedestrian_obs':
        field_ = getattr(Person, fieldName)
        q = session.query(func.count(field_), field_)\
                   .join(Pedestrian, Person.id == Pedestrian.personId)\
                   .join(Pedestrian_obs, Pedestrian_obs.pedestrianId == Pedestrian.id) \
                   .filter(Pedestrian_obs.instant >= startTime) \
                   .filter(Pedestrian_obs.instant <= endTime) \
                   .filter(Pedestrian_obs.destinationId != '') \
                   .group_by(field_)
    elif className == 'Vehicle_obs':
        field_ = getattr(Vehicle, fieldName)
        q = session.query(func.count(field_), field_)\
                   .join(Vehicle_obs, Vehicle_obs.vehicleId == Vehicle.id) \
                   .filter(Vehicle_obs.instant >= startTime) \
                   .filter(Vehicle_obs.instant <= endTime) \
                   .filter(Vehicle_obs.destinationId != '') \
                   .group_by(field_)
    elif className == 'Bike_obs':
        field_ = getattr(Bike, fieldName)
        q = session.query(func.count(field_), field_)\
                   .join(Bike_obs, Bike_obs.bikeId == Bike.id) \
                   .filter(Bike_obs.instant >= startTime) \
                   .filter(Bike_obs.instant <= endTime) \
                   .filter(Bike_obs.destinationId != '') \
                   .group_by(field_)
    elif className == 'Activity':
        field_ = getattr(Activity, fieldName)
        q = session.query(func.count(field_), field_) \
                   .filter(Activity.startTime >= startTime) \
                   .filter(Activity.startTime <= endTime) \
                   .group_by(field_)

    # q = session.query(cls_fld).join(Pedestrian, Person.id == Pedestrian.personId). \
    #     distinct()
    labels = [i[1].name for i in q.all()]
    sizes = [int(i[0]) for i in q.all()]

    return labels, sizes


def heatmap(data, row_labels, col_labels, ax=None,
            cbar_kw={}, cbarlabel="", **kwargs):
    """
    Create a heatmap from a numpy array and two lists of labels.

    Parameters
    ----------
    data
        A 2D numpy array of shape (N, M).
    row_labels
        A list or array of length N with the labels for the rows.
    col_labels
        A list or array of length M with the labels for the columns.
    ax
        A `matplotlib.axes.Axes` instance to which the heatmap is plotted.  If
        not provided, use current axes or create a new one.  Optional.
    cbar_kw
        A dictionary with arguments to `matplotlib.Figure.colorbar`.  Optional.
    cbarlabel
        The label for the colorbar.  Optional.
    **kwargs
        All other arguments are forwarded to `imshow`.
    """

    if not ax:
        ax = plt.gca()

    # Plot the heatmap
    im = ax.imshow(data, **kwargs)

    # Create colorbar
    cbar = ax.figure.colorbar(im, ax=ax, **cbar_kw)
    cbar.ax.set_ylabel(cbarlabel, rotation=-90, va="bottom")

    # We want to show all ticks...
    ax.set_xticks(np.arange(data.shape[1]))
    ax.set_yticks(np.arange(data.shape[0]))
    # ... and label them with the respective list entries.
    ax.set_xticklabels(col_labels)
    ax.set_yticklabels(row_labels)

    # Let the horizontal axes labeling appear on top.
    ax.tick_params(top=True, bottom=False,
                   labeltop=True, labelbottom=False, labelsize=8)

    # Rotate the tick labels and set their alignment.
    plt.setp(ax.get_xticklabels(), rotation=-30, ha="right",
             rotation_mode="anchor")

    # Turn spines off and create white grid.
    for edge, spine in ax.spines.items():
        spine.set_visible(False)

    ax.set_xticks(np.arange(data.shape[1]+1)-.5, minor=True)
    ax.set_yticks(np.arange(data.shape[0]+1)-.5, minor=True)
    ax.grid(which="minor", color="w", linestyle='-', linewidth=3)
    ax.tick_params(which="minor", bottom=False, left=False)

    return im, cbar


def annotate_heatmap(im, data=None, valfmt="{x:.2f}",
                     textcolors=("black", "white"),
                     threshold=None, **textkw):
    """
    A function to annotate a heatmap.

    Parameters
    ----------
    im
        The AxesImage to be labeled.
    data
        Data used to annotate.  If None, the image's data is used.  Optional.
    valfmt
        The format of the annotations inside the heatmap.  This should either
        use the string format method, e.g. "$ {x:.2f}", or be a
        `matplotlib.ticker.Formatter`.  Optional.
    textcolors
        A pair of colors.  The first is used for values below a threshold,
        the second for those above.  Optional.
    threshold
        Value in data units according to which the colors from textcolors are
        applied.  If None (the default) uses the middle of the colormap as
        separation.  Optional.
    **kwargs
        All other arguments are forwarded to each call to `text` used to create
        the text labels.
    """

    if not isinstance(data, (list, np.ndarray)):
        data = im.get_array()

    # Normalize the threshold to the images color range.
    if threshold is not None:
        threshold = im.norm(threshold)
    else:
        threshold = im.norm(data.max())/2.

    # Set default alignment to center, but allow it to be
    # overwritten by textkw.
    kw = dict(horizontalalignment="center",
              verticalalignment="center")
    kw.update(textkw)

    # Get the formatter in case a string is supplied
    if isinstance(valfmt, str):
        valfmt = matplotlib.ticker.StrMethodFormatter(valfmt)

    # Loop over the data and create a `Text` for each "pixel".
    # Change the text's color depending on the data.
    texts = []
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            kw.update(color=textcolors[int(im.norm(data[i, j]) > threshold)])
            text = im.axes.text(j, i, valfmt(data[i, j], None), **kw)
            texts.append(text)

    return texts


# ======================= DEMO MODE ============================
if __name__ == '__main__':
    # tempDistHist(user = 'vehicle', od_name = 'road_2')
    # stackedHist('activities', 'activityType', 20)
    odMatrix('cyclist', session)
