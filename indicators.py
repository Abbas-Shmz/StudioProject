#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

@author: Abbas
"""
import numpy as np
from pathlib import Path
import datetime
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator
from sqlalchemy import func
from configparser import ConfigParser

from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
from hachoir.core import config as HachoirConfig

import pandas as pd
from matplotlib.patches import Polygon
from trafficintelligence import storage, moving
from trafficintelligence.cvutils import imageToWorldProject, worldToImageProject
from trafficintelligence.storage import ProcessParameters
import iframework
from iframework import connectDatabase, LinePassing, ZonePassing, Person, Mode, GroupBelonging,\
    Vehicle, Line, Zone

noDataSign = 'x'

config_object = ConfigParser()
cfg = config_object.read("config.ini")
if cfg != []:
    PH = config_object['PEAKHOURS']
    morningPeakStart = datetime.datetime.strptime(PH['morningPeakStart'], '%I:%M %p').time()
    morningPeakEnd = datetime.datetime.strptime(PH['morningPeakEnd'], '%I:%M %p').time()
    eveningPeakStart = datetime.datetime.strptime(PH['eveningPeakStart'], '%I:%M %p').time()
    eveningPeakEnd = datetime.datetime.strptime(PH['eveningPeakEnd'], '%I:%M %p').time()
    binsMinutes = int(config_object['BINS']['binsminutes'])
else:
    morningPeakStart = datetime.time(7, 0)
    morningPeakEnd = datetime.time(9, 0)
    eveningPeakStart = datetime.time(15, 0)
    eveningPeakEnd = datetime.time(19, 0)
    binsMinutes = 10

# ==============================================================
def tempDistHist(transport, actionType, unitIdx, ax, session, bins=20, alpha=1, color='skyblue',
                 ec='grey', label=None, rwidth=0.9, histtype='bar'):

    if not isinstance(session, list):
        time_list = []
        if 'line' in actionType.split(' '):
            q = session.query(LinePassing.instant).filter(LinePassing.lineIdx == unitIdx). \
                join(GroupBelonging, GroupBelonging.groupIdx == LinePassing.groupIdx)
        elif 'zone' in actionType.split(' '):
            q = session.query(ZonePassing.instant).filter(ZonePassing.zoneIdx == unitIdx). \
                join(GroupBelonging, GroupBelonging.groupIdx == ZonePassing.groupIdx)
            if 'entering' in actionType.split(' '):
                q = q.filter(ZonePassing.entering == True)
            elif 'exiting' in actionType.split(' '):
                q = q.filter(ZonePassing.entering == False)
        q = q.join(Mode, Mode.personIdx == GroupBelonging.personIdx)\
            .filter(Mode.transport == transport)

        time_list = [i[0] for i in q.all()]

        if time_list == []:
            return 'No {} is observed {} #{}!'.format(transport, actionType, unitIdx)

        (n, edges, patches) = ax.hist(time_list, bins=bins, color=color, ec=ec, rwidth=rwidth,
                                      alpha=alpha, label=label, histtype=histtype)
    else:
        time_lists = []
        for s in session:
            time_list = []
            if 'line' in actionType.split(' '):
                q = s.query(LinePassing.instant).filter(LinePassing.lineIdx == unitIdx). \
                    join(GroupBelonging, GroupBelonging.groupIdx == LinePassing.groupIdx)
            elif 'zone' in actionType.split(' '):
                q = s.query(ZonePassing.instant).filter(ZonePassing.zoneIdx == unitIdx). \
                    join(GroupBelonging, GroupBelonging.groupIdx == ZonePassing.groupIdx)
                if 'entering' in actionType.split(' '):
                    q = q.filter(ZonePassing.entering == True)
                elif 'exiting' in actionType.split(' '):
                    q = q.filter(ZonePassing.entering == False)
            q = q.join(Mode, Mode.personIdx == GroupBelonging.personIdx) \
                .filter(Mode.transport == transport)

            time_list = [i[0] for i in q.all()]
            time_lists.append(time_list)

        if time_lists[0] == [] and time_lists[1] == []:
            return 'No {} is observed {} #{}!'.format(transport, actionType, unitIdx)

        i = 0
        for t in time_lists[0]:
            time_lists[0][i] = datetime.datetime(2000,1,1,t.hour, t.minute, t.second)
            i += 1

        i = 0
        for t in time_lists[1]:
            time_lists[1][i] = datetime.datetime(2000, 1, 1, t.hour, t.minute, t.second)
            i += 1

        # fig = plt.figure()#figsize=(5, 5), dpi=200, tight_layout=True)
        # ax = fig.add_subplot(111) #plt.subplots(1, 1)
        (n, edges, patches) = ax.hist(time_lists, bins=bins, color=color, ec=ec,
                                      rwidth=rwidth, alpha=alpha, label=label, histtype=histtype)

    if not isinstance(n[0], np.ndarray):
        n = [n]

    c = ['skyblue', 'red']
    i = 0
    for lst in n:
        avg = np.mean(lst)
        ax.axhline(y=avg, color=c[i], linestyle='-', lw=1.5)
        i += 1

    locator = mdates.AutoDateLocator()
    ax.xaxis.set_major_locator(locator)

    ax.xaxis.set_minor_locator(mdates.HourLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    # print((locator()))

    if not isinstance(session, list):
        xLabel = 'Time ({})'.format(time_list[0].strftime('%A, %b %d, %Y'))
    else:
        xLabel = 'Time'

    # ax.set_xticklabels(fontsize = 6, rotation = 45)#'vertical')
    ax.tick_params(axis='x', labelsize=8, rotation=0)
    ax.tick_params(axis='y', labelsize=7)
    ax.set_xlabel(xLabel, fontsize=8)
    ax.set_ylabel('No. of ' + transport, fontsize=8)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_title('Temporal distribution of {}s {} #{}'.format(transport, actionType, unitIdx),
                 fontsize=8)
    ax.grid(True, 'major', 'y', ls='--', lw=.5, c='k', alpha=.3)

    # if not isinstance(session, list):
    #     ax.text(0.05, 0.95, str(time_list[0].strftime('%A, %b %d, %Y')),
    #             horizontalalignment='left',
    #             verticalalignment='center',
    #             transform=ax.transAxes,
    #             fontsize=8)

    ax.text(0.03, 0.93, str('StUDiO Project'),
            fontsize=9, color='gray',
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
    ax.hist(time_list, bins=bins, label=distinct_vals, rwidth=0.85, stacked=True)

    locator = mdates.AutoDateLocator()
    ax.xaxis.set_major_locator(locator)

    ax.xaxis.set_minor_locator(mdates.HourLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

    if not isinstance(session, list):
        xLabel = 'Time ({})'.format(time_list[0][0].strftime('%A, %b %d, %Y'))
    else:
        xLabel = 'Time'

    # ax.set_xticklabels(fontsize = 6, rotation = 45)#'vertical')
    ax.tick_params(axis='x', labelsize=8, rotation=0)
    ax.tick_params(axis='y', labelsize=7)
    ax.set_xlabel(xLabel, fontsize=8)
    ax.set_ylabel('No. of ' + user, fontsize=8)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_title('Temporal distribution of ' + user + ' by ' + attr, fontsize=10)
    ax.grid(True, 'major', 'y', ls='--', lw=.5, c='k', alpha=.3)
    plt.legend(loc="upper right", fontsize=7)

    # ax.text(0.05, 0.95, str(time_list[0][0].strftime('%A, %b %d, %Y')),
    #         horizontalalignment='left',
    #         verticalalignment='center',
    #         transform=ax.transAxes,
    #         fontsize=7)

    ax.text(0.03, 0.93, str('StUDiO Project'),
            fontsize=9, color='gray',
            ha='left', va='bottom',
            transform=ax.transAxes,
            weight="bold", alpha=.5)

    # plt.show()

# ==============================================================
def odMatrix(user, ax, session):
    start_obs_time, end_obs_time = getObsStartEnd(session)

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
    odFlow_df = od_df / duration_hours

    org_sum = [i for i in odFlow_df.sum(1).values]
    dst_sum = [i for i in odFlow_df.sum(0).values]

    indices_zero = [i for i, x in enumerate(zip(org_sum, dst_sum)) if x[0] < 1 and x[1] < 1]

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

    ticks = ['{}\n(ID: {})'.format(ods_name[i], ods_id[i]) for i in range(len(ods_name))]

    odFlow_df = od_df / duration_hours
    data = odFlow_df.to_numpy()

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
def pieChart(transport, attr, sTime, eTime, ax, session):

    sDate = getObsStartEnd(session)[0].date()
    startTime = datetime.datetime.combine(sDate, sTime)

    eDate = getObsStartEnd(session)[1].date()
    endTime = datetime.datetime.combine(eDate, eTime)

    labels, sizes = getLabelSizePie(transport, attr, startTime, endTime, session)
    explode = [0.01]*len(labels)

    wedges, texts, autotexts = ax.pie(sizes, explode=explode, labels=labels, autopct='%1.1f%%',
                                      shadow=False, startangle=90, textprops={'size': 8})

    ax.axis('equal')
    # ax.legend(wedges, labels,
    #           title="title",
    #           loc="upper right")

    plt.setp(autotexts, size=8, weight="bold")

#=====================================================================
def generateReport(transport, actionType, start_obs_time, end_obs_time, session):

    peakHours = getPeakHours(session, start_obs_time, end_obs_time)
    entP_peakHours = {'Entire period': [start_obs_time.time(), end_obs_time.time()]}
    entP_peakHours.update(peakHours)

    indDf = pd.DataFrame(columns=list(entP_peakHours.keys()), index=['Start time', 'End time', 'Duration'])

    duration = end_obs_time - start_obs_time
    duration_in_s = duration.total_seconds()
    duration_hours = duration_in_s / 3600

    if 'line' in actionType.split(' '):
        q = session.query(LinePassing.idx) \
            .filter(LinePassing.instant >= start_obs_time) \
            .filter(LinePassing.instant < end_obs_time) \
            .join(GroupBelonging, GroupBelonging.groupIdx == LinePassing.groupIdx)
    elif 'zone' in actionType.split(' '):
        q = session.query(ZonePassing.idx) \
            .filter(ZonePassing.instant >= start_obs_time) \
            .filter(ZonePassing.instant < end_obs_time) \
            .join(GroupBelonging, GroupBelonging.groupIdx == ZonePassing.groupIdx)
    q = q.join(Person, Person.idx == GroupBelonging.personIdx) \
         .join(Mode, Mode.personIdx == Person.idx) \
         .filter(Mode.transport == transport)

    if transport == 'walking':

        if 'line' in actionType.split(' '):
            indicators = ['No. of all people passing through',  # 0
                          'No. of females',  # 1
                          'No. of males',  # 2
                          'No. of children',  # 3
                          'No. of elderly people',  # 4
                          'No. of people with pet',  # 5
                          'No. of disabled people',  # 6
                          'Flow of all people (ped/h)',  # 7
                          'No of all groups',  # 8
                          'No. of groups with size = 1',  # 9
                          'No. of groups with size = 2',  # 10
                          'No. of groups with size = 3',  # 11
                          'No. of groups with size > 3'  # 12
                          ]

        no_all_peds = q.count()

        for p in entP_peakHours.keys():
            if entP_peakHours[p] is None:
                continue

            lowerBound = datetime.datetime.combine(start_obs_time.date(), entP_peakHours[p][0])
            upperBound = datetime.datetime.combine(start_obs_time.date(), entP_peakHours[p][1])

            duration = upperBound - lowerBound
            duration_in_s = duration.total_seconds()
            duration_hours = duration_in_s / 3600

            q_all_peaks = q.filter(LinePassing.instant >= lowerBound)\
                           .filter(LinePassing.instant < upperBound)

            no_all_peak = q_all_peaks.count()

            indDf.iloc[0].loc[p] = '{}'.format(entP_peakHours[p][0].strftime('%I:%M %p'))
            indDf.iloc[1].loc[p] = '{}'.format(entP_peakHours[p][1].strftime('%I:%M %p'))
            indDf.iloc[2].loc[p] = '{}h {}m'.format(int(duration_in_s / 3600),
                                                    int(duration_in_s / 60) % 60)

            for ind in indicators:
                if p == indDf.columns[0]:
                    noAll = no_all_peds
                elif p != indDf.columns[0] and ind in list(indDf.index):
                    noAll = float(indDf.loc[ind].iloc[0].split(' ')[0])

                i = indicators.index(ind)
                if i == 0:
                    if p == indDf.columns[0]:
                        indDf.loc[ind, p] = '{}'.format(no_all_peds)
                    else:
                        pct = round((no_all_peak / noAll) * 100, 1) if noAll != 0 else 0
                        indDf.loc[ind, p] = '{} ({}%)'.format(no_all_peak, pct)

                elif i == 1:
                    no_fem_peak = q_all_peaks.filter(Person.gender == 'female').count()
                    pct = round((no_fem_peak / noAll) * 100, 1) if noAll != 0 else 0
                    indDf.loc[ind, p] = '{} ({}%)'.format(no_fem_peak, pct)

                elif i == 2:
                    no_mal_peak = q_all_peaks.filter(Person.gender == 'male').count()
                    pct = round((no_mal_peak / noAll) * 100, 1) if noAll != 0 else 0
                    indDf.loc[ind, p] = '{} ({}%)'.format(no_mal_peak, pct)

                elif i == 3:
                    no_chd_peak = q_all_peaks.filter(Person.age == 'child').count()
                    pct = round((no_chd_peak / noAll) * 100, 1) if noAll != 0 else 0
                    indDf.loc[ind, p] = '{} ({}%)'.format(no_chd_peak, pct)

                elif i == 4:
                    no_eld_peak = q_all_peaks.filter(Person.age == 'senior').count()
                    pct = round((no_eld_peak / noAll) * 100, 1) if noAll != 0 else 0
                    indDf.loc[ind, p] = '{} ({}%)'.format(no_eld_peak, pct)

                elif i == 5:
                    no_pet_peak = q_all_peaks.filter(Person.animal == 1).count()
                    pct = round((no_pet_peak / noAll) * 100, 1) if noAll != 0 else 0
                    indDf.loc[ind, p] = '{} ({}%)'.format(no_pet_peak, pct)

                elif i == 6:
                    no_dis_peak = q_all_peaks.filter(Person.disability != 'no')\
                                             .filter(Person.disability != '')\
                                             .filter(Person.disability != False).count()
                    pct = round((no_dis_peak / noAll) * 100, 1) if noAll != 0 else 0
                    indDf.loc[ind, p] = '{} ({}%)'.format(no_dis_peak, pct)

                elif i == 7:
                    flow_all_peak = round(no_all_peak / duration_hours, 1)
                    indDf.loc[ind, p] = '{}'.format(flow_all_peak)


    elif transport in ['cardriver', 'bike', 'scooter', 'skating']:
        if 'line' in actionType.split(' '):
            indicators = ['No. of all vehicles passing through',   # 0
                          'Flow of passing vehicles (veh/h)'   # 1
                          ]

        no_all_vehs = q.count()

        if no_all_vehs == 0:
            return indDf

        for p in entP_peakHours.keys():
            if entP_peakHours[p] is None:
                continue

            lowerBound = datetime.datetime.combine(start_obs_time.date(), entP_peakHours[p][0])
            upperBound = datetime.datetime.combine(start_obs_time.date(), entP_peakHours[p][1])

            duration = upperBound - lowerBound
            duration_in_s = duration.total_seconds()
            duration_hours = duration_in_s / 3600

            q_all_peaks = q.filter(LinePassing.instant >= lowerBound) \
                           .filter(LinePassing.instant < upperBound)

            no_all_peak = q_all_peaks.count()

            indDf.iloc[0].loc[p] = '{}'.format(entP_peakHours[p][0].strftime('%I:%M %p'))
            indDf.iloc[1].loc[p] = '{}'.format(entP_peakHours[p][1].strftime('%I:%M %p'))
            indDf.iloc[2].loc[p] = '{}h {}m'.format(int(duration_in_s / 3600),
                                                    int(duration_in_s / 60) % 60)

            for ind in indicators:

                if p == indDf.columns[0]:
                    noAll = no_all_vehs
                elif p != indDf.columns[0] and ind in list(indDf.index):
                    noAll = float(indDf.loc[ind].iloc[0].split(' ')[0])

                i = indicators.index(ind)
                if i == 0:
                    if p == indDf.columns[0]:
                        indDf.loc[ind, p] = '{}'.format(no_all_vehs)
                    else:
                        pct = round((no_all_peak / noAll) * 100, 1) if noAll != 0 else 0
                        indDf.loc[ind, p] = '{} ({}%)'.format(no_all_peak, pct)

                # elif i == 2:
                #     no_arriv_vehs = q.join(Site_ODs, Vehicle_obs.destinationId == Site_ODs.id) \
                #                      .filter(Site_ODs.odType == 'on_street_parking_lot').count()
                #     pct = round((no_arriv_vehs / noAll) * 100, 1) if noAll != 0 else 0
                #
                #     indDf.loc[ind, p] = '{} ({}%)'.format(no_arriv_vehs, pct)
                #
                # elif i == 3:
                #     no_depart_vehs = q.join(Site_ODs, Vehicle_obs.originId == Site_ODs.id) \
                #                       .filter(Site_ODs.odType == 'on_street_parking_lot').count()
                #     pct = round((no_depart_vehs / noAll) * 100, 1) if noAll != 0 else 0
                #
                #     indDf.loc[ind, p] = '{} ({}%)'.format(no_depart_vehs, pct)

                elif i == 1:
                    indDf.loc[ind, p] = '{}'.format(round(no_all_peak / duration_hours, 1))

                # elif i == 5:
                #     indDf.loc[ind, p] = '{}'.format(round(no_arriv_vehs / duration_hours, 1))
                #
                # elif i == 6:
                #     indDf.loc[ind, p] = '{}'.format(round(no_depart_vehs / duration_hours, 1))


    elif transport == 'Bike':
        indicators = ['No. of all cyclists',    # 0
                      'No. of cyclists riding on sidewalk',     # 1
                      'No. of cyclists riding against traffic', # 2
                      'Flow of all bikes (bik/h)'  # 3
                      ]

        q = session.query(Bike.id).join(Bike_obs, Bike.id == Bike_obs.bikeId) \
                   .filter(Bike_obs.instant >= start_obs_time) \
                   .filter(Bike_obs.instant < end_obs_time)

        no_all_biks = q.count()

        q_swk = session.query(Site_ODs.id).filter(Site_ODs.odType == 'sidewalk')
        swk_ids = [int(i[0]) for i in q_swk.all()]

        for p in entP_peakHours.keys():
            if entP_peakHours[p] is None:
                continue

            lowerBound = datetime.datetime.combine(start_obs_time.date(), entP_peakHours[p][0])
            upperBound = datetime.datetime.combine(start_obs_time.date(), entP_peakHours[p][1])

            duration = upperBound - lowerBound
            duration_in_s = duration.total_seconds()
            duration_hours = duration_in_s / 3600

            q_all_peaks = session.query(Bike_obs.originId, Bike_obs.destinationId)\
                                 .filter(Bike_obs.instant >= lowerBound) \
                                 .filter(Bike_obs.instant < upperBound)

            indDf.iloc[0].loc[p] = '{}'.format(entP_peakHours[p][0].strftime('%I:%M %p'))
            indDf.iloc[1].loc[p] = '{}'.format(entP_peakHours[p][1].strftime('%I:%M %p'))
            indDf.iloc[2].loc[p] = '{}h {}m'.format(int(duration_in_s / 3600), int(duration_in_s / 60) % 60)

            for ind in indicators:
                if p == indDf.columns[0]:
                    noAll = no_all_biks
                elif p != indDf.columns[0] and ind in list(indDf.index):
                    noAll = float(indDf.loc[ind].iloc[0].split(' ')[0])

                i = indicators.index(ind)
                if i == 0:
                    no_all_peak = q_all_peaks.count()
                    if p == indDf.columns[0]:
                        cell = ['{}', no_all_biks, None]
                    else:
                        pct = round((no_all_peak / noAll) * 100, 1) if noAll != 0 else 0
                        cell = ['{} ({}%)', no_all_peak, pct]
                    indDf.loc[ind, p] = cell[0].format(cell[1], cell[2])

                elif i == 1:
                    no_sdwk_peak = 0
                    for rec in q_all_peaks.all():
                        if int(rec[0]) in swk_ids or int(rec[1]) in swk_ids:
                            no_sdwk_peak += 1
                    pct = round((no_sdwk_peak / noAll) * 100, 1) if noAll != 0 else 0
                    indDf.loc[ind, p] = '{} ({}%)'.format(no_sdwk_peak, pct)

                elif i ==2:
                    q_against = q_all_peaks.join(Site_ODs, Bike_obs.originId == Site_ODs.id) \
                        .filter(Site_ODs.direction == 'end_point')

                    no_agst_peak = q_against.count()
                    pct = round((no_agst_peak / noAll) * 100, 1) if noAll != 0 else 0
                    indDf.loc[ind, p] = '{} ({}%)'.format(no_agst_peak, pct)

                elif i == 3:
                    no_all_peak = q_all_peaks.count()
                    flow_all_peak = round(no_all_peak / duration_hours, 1)
                    indDf.loc[ind, p] = '{}'.format(flow_all_peak)


    elif transport == 'Activity':
        indicators = ['Start time',  # 0
                      'End time',    # 1
                      'Duration'    # 2
                      ]
        q = session.query(Activity.activityType) \
                   .filter(Activity.startTime >= start_obs_time)\
                   .filter(Activity.startTime < end_obs_time).distinct()

        activity_dict = {}
        for rec in q.all():
            act_type = rec[0].name
            activity_dict[act_type] = {'count': 0, 'actTotalTime': 0}

        entP_peakHours = {indDf.columns[0]:[start_obs_time.time(), end_obs_time.time()]}
        entP_peakHours.update(peakHours)

        for p in entP_peakHours.keys():

            if not entP_peakHours[p] is None:

                lowerBound = datetime.datetime.combine(start_obs_time.date(), entP_peakHours[p][0])
                upperBound = datetime.datetime.combine(start_obs_time.date(), entP_peakHours[p][1])

                duration = upperBound - lowerBound
                duration_in_s = duration.total_seconds()
                duration_hours = duration_in_s / 3600

                indDf.iloc[0].loc[p] = '{}'.format(entP_peakHours[p][0].strftime('%I:%M %p'))
                indDf.iloc[1].loc[p] = '{}'.format(entP_peakHours[p][1].strftime('%I:%M %p'))
                indDf.iloc[2].loc[p] = \
                    '{}h {}m'.format(int(duration_in_s / 3600), int(duration_in_s / 60) % 60)

                q = session.query(Activity.activityType, Activity.startTime, Activity.endTime) \
                           .filter(Activity.startTime >= lowerBound) \
                           .filter(Activity.startTime < upperBound)

                for key in activity_dict.keys():
                    activity_dict[key]['count'] = 0
                    activity_dict[key]['actTotalTime'] = 0

                for act in q.all():
                    act_type = act[0].name
                    activity_dict[act_type]['count'] += 1
                    activity_dict[act_type]['actTotalTime'] += (act[2] - act[1]).total_seconds()

                total_acts = 0
                total_time = 0
                for val in activity_dict.values():
                    total_acts += val['count']
                    total_time += val['actTotalTime']

                all_activity_dict = {'all activities': {'count': total_acts, 'actTotalTime':total_time}}
                all_activity_dict.update(activity_dict)

                q_join_person = q.join(Person, Activity.personId == Person.id)
                no_female_act = q_join_person.filter(Person.gender == 'female').count()
                no_male_act = q_join_person.filter(Person.gender == 'male').count()
                no_chld_act = q_join_person.filter(Person.age == 'child').count()
                no_eldry_act = q_join_person.filter(Person.age == 'senior').count()

                for act in all_activity_dict.keys():
                    act_count = all_activity_dict[act]['count']
                    act_totalTime_min = round(all_activity_dict[act]['actTotalTime'] / 60, 1)

                    if act == 'all activities' and p == indDf.columns[0]:
                        indDf.loc['No. of {}'.format(act), p] = '{}'.format(act_count)
                    elif act == 'all activities' and p != indDf.columns[0]:
                        indDf.loc['No. of {}'.format(act), p] = '{} ({}%)'.format(act_count,
                                               round((act_count / int(indDf.loc['No. of {}'
                                               .format(act)].iloc[0].split(' ')[0]))*100, 1))
                    elif act != 'all activities' and p == indDf.columns[0]:
                        indDf.loc['No. of people {}'.format(act), p] = '{} ({}%)'.format(act_count,
                                                                round((act_count / total_acts)*100, 1))
                    elif act != 'all activities' and p != indDf.columns[0]:
                        indDf.loc['No. of people {}'.format(act), p] = '{} ({}%)'.format(act_count,
                                               round((act_count / int(indDf.loc['No. of people {}'
                                               .format(act)].iloc[0].split(' ')[0]))*100, 1))
                    indDf.loc['Total time of {} (min.)'.format(act), p] = \
                        '{}'.format(act_totalTime_min if act_totalTime_min > 0 else 'NA')
                    indDf.loc['Avg. time of {} (min.)'.format(act), p] = \
                      '{}'.format(round(act_totalTime_min / total_acts, 1) if act_totalTime_min > 0 else 'NA')
                    indDf.loc['Rate of {} (act/h)'.format(act), p] = \
                        '{}'.format(round(act_count / duration_hours, 1))

                if p == 'Entire period':
                    indDf.loc['No. of females doing activity', p] = '{} ({}%)'.format(no_female_act,
                                                            round((no_female_act / total_acts)*100, 1))
                    indDf.loc['No. of males doing activity', p] = '{} ({}%)'.format(no_male_act,
                                                            round((no_male_act / total_acts)*100, 1))
                    indDf.loc['No. of children doing activity', p] = '{} ({}%)'.format(no_chld_act,
                                                            round((no_chld_act / total_acts) * 100, 1))
                    indDf.loc['No. of elderly people doing activity', p] = '{} ({}%)'.format(no_eldry_act,
                                                            round((no_eldry_act / total_acts) * 100, 1))
                else:
                    noAll = int(indDf.loc['No. of females doing activity'].iloc[0].split(' ')[0])
                    indDf.loc['No. of females doing activity', p] = '{} ({}%)'.format(no_female_act,
                             round((no_female_act / noAll) * 100, 1) if noAll != 0 else 0)

                    noAll = int(indDf.loc['No. of males doing activity'].iloc[0].split(' ')[0])
                    indDf.loc['No. of males doing activity', p] = '{} ({}%)'.format(no_male_act,
                             round((no_male_act / noAll) * 100,1) if noAll != 0 else 0)

                    noAll = int(indDf.loc['No. of children doing activity'].iloc[0].split(' ')[0])
                    indDf.loc['No. of children doing activity', p] = '{} ({}%)'.format(no_chld_act,
                             round((no_chld_act / noAll) * 100,1) if noAll != 0 else 0)

                    noAll = int(indDf.loc['No. of elderly people doing activity'].iloc[0].split(' ')[0])
                    indDf.loc['No. of elderly people doing activity', p] = '{} ({}%)'.format(no_eldry_act,
                             round((no_eldry_act / noAll) * 100,1) if noAll != 0 else 0)


    indDf[indDf.isnull().values] = noDataSign

    indDf.columns = [indDf.columns[0] + ' (% of all)',
                     indDf.columns[1] + ' (% of item)',
                     indDf.columns[2] + ' (% of item)',
                     indDf.columns[3] + ' (% of item)']
    indDf = indDf.replace(['0 (0.0%)', '0 (0%)'], 0)

    for i in indDf.index:
        for c in indDf.columns:
            parts = str(indDf.loc[i, c]).split(' ')
            if len(parts) > 1:
                if parts[1] == '(100.0%)':
                    indDf.loc[i, c] = '{} ({}%)'.format(parts[0], 100)


    return indDf


def compareIndicators(transport, actionType, start_time, end_time, session1, session2):
    obs_date1 = getObsStartEnd(session1)[0].date()
    obs_date2 = getObsStartEnd(session2)[0].date()

    start_time1 = datetime.datetime.combine(obs_date1, start_time)
    end_time1 = datetime.datetime.combine(obs_date1, end_time)

    start_time2 = datetime.datetime.combine(obs_date2, start_time)
    end_time2 = datetime.datetime.combine(obs_date2, end_time)

    indDf1 = generateReport(transport, actionType, start_time1, end_time1, session1)
    indDf2 = generateReport(transport, actionType, start_time2, end_time2, session2)

    indDf = indDf1.iloc[0:3, :].copy()

    idx1 = indDf1.index[3:]
    idx2 = indDf2.index[3:]

    idx2_idx1 = list(set(idx2) - set(idx1))
    idx1_idx2 = list(set(idx1) - set(idx2))

    if len(idx2_idx1) > 0:
        for idx in idx2_idx1:
            new_idx = indDf2.loc[idx].copy()
            new_idx[(new_idx != noDataSign) & (new_idx != 'NA')] = 0
            indDf1 = indDf1.append(new_idx)

    if len(idx1_idx2) > 0:
        for idx in idx1_idx2:
            new_idx = indDf1.loc[idx]
            new_idx[(new_idx != noDataSign) & (new_idx != 'NA')] = 0
            indDf2 = indDf2.append(new_idx)

    for row in indDf1.index[3:]:
        for col in indDf1.columns:
            if indDf1.loc[row, col] == noDataSign or indDf1.loc[row, col] == 'NA':
                continue
            strVal1 = str(indDf1.loc[row, col]).split(' ')[0]
            strVal2 = str(indDf2.loc[row, col]).split(' ')[0]
            if strVal1.isdigit():
                val1 = int(strVal1)
            else:
                val1 = float(strVal1)
            if strVal2.isdigit():
                val2 = int(strVal2)
            else:
                val2 = float(strVal2)
            diff = val2 - val1

            if diff > 0 and isinstance(diff, float):
                cellStr = '+{:.1f} [+{}%]'
            elif diff < 0 and isinstance(diff, float):
                cellStr = '{:.1f} [{}%]'
            elif diff > 0 and isinstance(diff, int):
                cellStr = '+{} [+{}%]'
            elif diff < 0 and isinstance(diff, int):
                cellStr = '{} [{}%]'
            elif diff == 0:
                cellStr = '{} [{}%]'
            indDf.loc[row, col] = cellStr.format(diff, round((diff/val1)*100, 1) if val1 != 0 else '-')

    indDf[indDf.isnull().values] = noDataSign

    indDf.columns = [indDf.columns[0].split('(')[0][:-1] + ' [% of change]',
                     indDf.columns[1].split('(')[0][:-1] + ' [% of change]',
                     indDf.columns[2].split('(')[0][:-1] + ' [% of change]',
                     indDf.columns[3].split('(')[0][:-1] + ' [% of change]']

    return indDf


def plotTrajectory(trjDBFile, intrinsicCameraMatrix, distortionCoefficients, homographyFile, ax, session):
    intrinsicCameraMatrix = np.array([[894.18, 0.0, 951.75], [0.0, 913.2, 573.04], [0.0, 0.0, 1.0]])
    distortionCoefficients = np.array([-0.12, 0.0, 0.0, 0.0, 0.0])
    objects = storage.loadTrajectoriesFromSqlite(trjDBFile, 'object')
    homography = np.loadtxt(homographyFile, delimiter=' ')

    for traj in objects:
        xy_arr = traj.positions.asArray()
        x = xy_arr[0]
        y = xy_arr[1]
        ax.plot(x, y, lw=0.5)

    q_line = session.query(Line)
    q_zone = session.query(Zone)

    if q_line.all() != []:
        for line in q_line:
            x_list = [p.x for p in line.points]
            y_list = [p.y for p in line.points]

            points = np.array([x_list, y_list], dtype = np.float64)
            prj_points = imageToWorldProject(points, intrinsicCameraMatrix, distortionCoefficients, homography)
            ax.plot(prj_points[0], prj_points[1])

    if q_zone.all() != []:
        for zone in q_zone:
            x_list = [p.x for p in zone.points]
            y_list = [p.y for p in zone.points]
            points = np.array([x_list, y_list])
            prj_points = imageToWorldProject(points, intrinsicCameraMatrix, distortionCoefficients, homography)
            prj_xy = list(zip(prj_points[0], prj_points[1]))
            rand_color = np.random.random(3)
            fc = np.append(rand_color, 0.15)
            ec = np.array([0, 0, 0, 0.5])
            zone = Polygon(prj_xy, fc=fc, ec=ec, lw=0.5)
            ax.add_patch(zone)
    ax.axis('equal')


def importTrajectory(trjDBFile, intrinsicCameraMatrix, distortionCoefficients, homoFile,
                     video_start, frameRate, session):
    log = {}
    if not Path(trjDBFile).exists():
        log['Error'] = 'The database does not exist!'
        print(Path(trjDBFile).name)
        for k, v in log.items():
            print('   {}: {}'.format(k, v))
        return log
    objects = storage.loadTrajectoriesFromSqlite(trjDBFile, 'object')
    homography = np.loadtxt(homoFile, delimiter=' ')

    q_line = session.query(Line)
    if q_line.all() == []:
        log['Error'] = 'There is no screenline!'
        for k, v in log.items():
            print('{}: {}'.format(k, v))
        return log

    linePass_list = []
    modes_list = []
    for line in q_line:
        points = np.array([[line.points[0].x, line.points[1].x],
                           [line.points[0].y, line.points[1].y]])
        prj_points = imageToWorldProject(points, intrinsicCameraMatrix, distortionCoefficients, homography)
        p1 = moving.Point(prj_points[0][0], prj_points[1][0])
        p2 = moving.Point(prj_points[0][1], prj_points[1][1])

        for trj in objects:
            instants_list = trj.getInstantsCrossingLane(p1, p2)
            if len(instants_list) > 0:
                secs = np.floor(instants_list[0]/frameRate)
                instant = video_start + datetime.timedelta(seconds=secs)
                person = Person()
                vehicle = Vehicle(category='car')
                modes_list.append(Mode(transport='cardriver', person=person, vehicle=vehicle))
                linePass_list.append(LinePassing(line=line, instant=instant, person=person))
    session.add_all(linePass_list + modes_list)
    session.commit()
    session.close()

    log['All processed trajectories'] = len(objects)
    log['Total imported trajectories'] = len(linePass_list)
    log['No. of vehicles'] = len(linePass_list)

    print(Path(trjDBFile).name)
    for k, v in log.items():
        print('   {}: {}'.format(k, v))

    return log

# =========================================
def image_to_ground(img_points, homography):
    n_points = img_points.shape[1]
    ground = np.tile(np.array([0]*n_points), (3, 1))
    img_points_1 = np.append(img_points, [[1]*n_points], axis=0)

    for i in range(3):
        for j in range(n_points):
            for k in range(3):
                ground[i][j] += homography[i][k]*img_points_1[k][j]

    for i in range(2):
        for j in range(n_points):
            ground[i][j] = ground[i][j]/ground[2][j]

    return ground[:-1,:]

def getLabelSizePie(transport, fieldName, startTime, endTime, session):

    if transport == 'all types':
        field_ = getattr(Mode, fieldName)
        q = session.query(field_, func.count(field_)) \
            .join(GroupBelonging, GroupBelonging.personIdx == Mode.personIdx) \
            .join(LinePassing, LinePassing.groupIdx == GroupBelonging.groupIdx) \
            .filter(LinePassing.instant >= startTime) \
            .filter(LinePassing.instant < endTime) \
            .group_by(field_)
    elif transport == 'walking':
        field_ = getattr(Person, fieldName)
        q = session.query(field_, func.count(field_)) \
            .join(Mode, Person.idx == Mode.personIdx) \
            .filter(Mode.transport == transport) \
            .join(GroupBelonging, GroupBelonging.personIdx == Person.idx) \
            .join(LinePassing, LinePassing.groupIdx == GroupBelonging.groupIdx) \
            .filter(LinePassing.instant >= startTime) \
            .filter(LinePassing.instant < endTime) \
            .group_by(field_)
    elif transport == 'cardriver':
        field_ = getattr(Vehicle, fieldName)
        q = session.query(field_, func.count(field_)) \
            .join(Mode, Vehicle.idx == Mode.vehicleIdx) \
            .filter(Mode.transport == transport) \
            .join(GroupBelonging, GroupBelonging.personIdx == Mode.personIdx) \
            .join(LinePassing, LinePassing.groupIdx == GroupBelonging.groupIdx) \
            .filter(LinePassing.instant >= startTime) \
            .filter(LinePassing.instant < endTime) \
            .group_by(field_)

    labels = [i[0].name if not isinstance(i[0], str) else i[0] for i in q.all()]
    sizes = [int(i[1]) for i in q.all()]

    return labels, sizes


def getPeakHours(session, start_obs_time, end_obs_time,
                 morningPeakStart = morningPeakStart,
                 morningPeakEnd = morningPeakEnd,
                 eveningPeakStart = eveningPeakStart,
                 eveningPeakEnd = eveningPeakEnd):

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

    return peakHours

def getObsStartEnd(session):
    first_linePass_time = session.query(func.min(LinePassing.instant)).first()[0]
    last_linePass_time = session.query(func.max(LinePassing.instant)).first()[0]

    first_zonePass_time = session.query(func.min(ZonePassing.instant)).first()[0]
    last_zonePass_time = session.query(func.max(ZonePassing.instant)).first()[0]

    first_times = [first_linePass_time, first_zonePass_time]
    last_times = [last_linePass_time, last_zonePass_time]
    if None in first_times:
        start_obs_time = next((t for t in first_times if t is not None), None)
    else:
        start_obs_time = min(first_times)

    if None in last_times:
        end_obs_time = next((t for t in last_times if t is not None), None)
    else:
        end_obs_time = max(last_times)


    # site_instance = session.query(Study_site).first()
    # start_obs_time = site_instance.obsStart
    # end_obs_time = site_instance.obsEnd
    return start_obs_time, end_obs_time

def calculateBinsEdges(start, end):
    if cfg != []:
        interval = int(config_object['BINS']['binsminutes'])
    else:
        interval = 10
    m2 = np.ceil((start.minute + start.second / 60) / interval)
    if m2 == 60 / interval:
        start = datetime.datetime.combine(start.date(), datetime.time(start.hour + 1))
    else:
        start = datetime.datetime.combine(start.date(),
                                          datetime.time(start.hour, int(m2 * interval)))

    bins = pd.date_range(start=start, end=end, freq=pd.offsets.Minute(interval))
    return bins


def calculateNoBins(session, minutes=binsMinutes):
    start_obs_time, end_obs_time = getObsStartEnd(session)
    duration = end_obs_time - start_obs_time
    duration_in_s = duration.total_seconds()
    bins = round(duration_in_s/(60*minutes))
    if bins == 0:
        bins = 1
    return bins


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


def getVideoMetadata(filename):
    HachoirConfig.quiet = True
    parser = createParser(filename)

    with parser:
        try:
            metadata = extractMetadata(parser, 7)
        except Exception as err:
            print("Metadata extraction error: %s" % err)
            metadata = None
    if not metadata:
        print("Unable to extract metadata")

    # creationDatetime_text = metadata.exportDictionary()['Metadata']['Creation date']
    # creationDatetime = datetime.strptime(creationDatetime_text, '%Y-%m-%d %H:%M:%S')

    metadata_dict = metadata._Metadata__data
    # for key in metadata_dict.keys():
    #     if metadata_dict[key].values:
    #         print(key, metadata_dict[key].values[0].value)
    creationDatetime = metadata_dict['creation_date'].values[0].value
    width = metadata_dict['width'].values[0].value
    height = metadata_dict['height'].values[0].value

    return creationDatetime, width, height



# ======================= DEMO MODE ============================
if __name__ == '__main__':
    # tempDistHist(user = 'vehicle', od_name = 'road_2')
    # stackedHist('activities', 'activityType', 20)
    odMatrix('cyclist', session)
