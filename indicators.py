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
from configparser import ConfigParser

import pandas as pd
import iframework
from iframework import connectDatabase

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
def tempDistHist(user, od_name, direction, ax, session, bins=20, alpha=1, color='skyblue', ec='grey',
                 label=None, rwidth=0.9, histtype='bar'):
    cls_obs = getattr(dbSchema, user + '_obs')

    if not isinstance(session, list):
        time_list = []
        for ods in direction:
            q = session.query(cls_obs.instant).\
                filter(cls_obs.originId == ods[0]). \
                filter(cls_obs.destinationId == ods[1])
            time_list = time_list + [i[0] for i in q.all()]

        if time_list == []:
            return 'No {} is observed in {} for the selected direction(s)!'.format(user, od_name)

        (n, edges, patches) = ax.hist(time_list, bins=bins, color=color, ec=ec, rwidth=rwidth,
                                      alpha=alpha, label=label, histtype=histtype)
    else:
        time_list1 = []
        for ods in direction:
            q = session[0].query(cls_obs.instant). \
                filter(cls_obs.originId == ods[0]). \
                filter(cls_obs.destinationId == ods[1])
            time_list1 = time_list1 + [i[0] for i in q.all()]

        time_list2 = []
        for ods in direction:
            q = session[1].query(cls_obs.instant). \
                filter(cls_obs.originId == ods[0]). \
                filter(cls_obs.destinationId == ods[1])
            time_list2 = time_list2 + [i[0] for i in q.all()]
        if time_list1 == [] and time_list2 == []:
            return 'No {} is observed in {} for the selected direction(s)!'.format(user, od_name)

        i = 0
        for t in time_list1:
            time_list1[i] = datetime.datetime(2000,1,1,t.hour, t.minute, t.second)
            i += 1

        i = 0
        for t in time_list2:
            time_list2[i] = datetime.datetime(2000, 1, 1, t.hour, t.minute, t.second)
            i += 1

        # fig = plt.figure()#figsize=(5, 5), dpi=200, tight_layout=True)
        # ax = fig.add_subplot(111) #plt.subplots(1, 1)
        (n, edges, patches) = ax.hist([time_list1, time_list2], bins=bins, color=color, ec=ec,
                                      rwidth=rwidth, alpha=alpha, label=label, histtype=histtype)

    if not isinstance(n[0], np.ndarray):
        n = [n]

    c = ['skyblue', 'red']
    i = 0
    for lst in n:
        avg = np.mean(lst)
        ax.axhline(y=avg, color=c[i], linestyle='-', lw=0.75)
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
    ax.set_ylabel('No. of ' + user, fontsize=8)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_title('Temporal distribution of ' + user + ' passings from ' + od_name, fontsize=10)
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
def pieChart(user, attr, sTime, eTime, ax, session):

    sDate = getObsStartEnd(session)[0].date()
    startTime = datetime.datetime.combine(sDate, sTime)

    eDate = getObsStartEnd(session)[1].date()
    endTime = datetime.datetime.combine(eDate, eTime)

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
def generateReport(subj, start_obs_time, end_obs_time, session):

    peakHours = getPeakHours(session, start_obs_time, end_obs_time)
    entP_peakHours = {'Entire period': [start_obs_time.time(), end_obs_time.time()]}
    entP_peakHours.update(peakHours)

    indDf = pd.DataFrame(columns=list(entP_peakHours.keys()), index=['Start time', 'End time', 'Duration'])

    duration = end_obs_time - start_obs_time
    duration_in_s = duration.total_seconds()
    duration_hours = duration_in_s / 3600

    if subj == 'Pedestrian':
        indicators = ['No. of all pedestrians',    # 0
                      'No. of female pedestrians', # 1
                      'No. of male pedestrians',   # 2
                      'No. of child pedestrians',  # 3
                      'No. of elderly pedestrians',     # 4
                      'No. of pedestrians with rolling',# 5
                      'No. of pedestrians with pet',    # 6
                      'No. of disabled pedestrians',    # 7
                      'No. of ped. crossing street',    # 8
                      'Flow of all pedestrians (ped/h)',# 9
                      'No. of groups with size = 1',    # 10
                      'No. of groups with size = 2',    # 11
                      'No. of groups with size = 3',    # 12
                      'No. of groups with size > 3'     # 13
                      ]

        q = session.query(Pedestrian.id).join(Pedestrian_obs, Pedestrian.id == Pedestrian_obs.pedestrianId)\
                               .filter(Pedestrian_obs.instant >= start_obs_time) \
                               .filter(Pedestrian_obs.instant <= end_obs_time)

        no_all_peds = q.count()
        q_join_person = q.join(Person, Person.id == Pedestrian.personId)

        for p in entP_peakHours.keys():
            if entP_peakHours[p] is None:
                continue

            lowerBound = datetime.datetime.combine(start_obs_time.date(), entP_peakHours[p][0])
            upperBound = datetime.datetime.combine(start_obs_time.date(), entP_peakHours[p][1])

            duration = upperBound - lowerBound
            duration_in_s = duration.total_seconds()
            duration_hours = duration_in_s / 3600

            q_all_peaks = q_join_person.filter(Pedestrian_obs.instant >= lowerBound)
            if entP_peakHours[p][1] in [morningPeakStart, morningPeakEnd, eveningPeakStart, eveningPeakEnd]:
                q_all_peaks = q_all_peaks.filter(Pedestrian_obs.instant < upperBound)
            else:
                q_all_peaks = q_all_peaks.filter(Pedestrian_obs.instant <= upperBound)

            no_all_peak = q_all_peaks.count()

            indDf.iloc[0].loc[p] = '{}'.format(entP_peakHours[p][0].strftime('%I:%M %p'))
            indDf.iloc[1].loc[p] = '{}'.format(entP_peakHours[p][1].strftime('%I:%M %p'))
            indDf.iloc[2].loc[p] = '{}h {}m'.format(int(duration_in_s / 3600), int(duration_in_s / 60) % 60)

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
                    no_rol_peak = q_all_peaks.filter(Pedestrian.rolling != 'none').count()
                    pct = round((no_rol_peak / noAll) * 100, 1) if noAll != 0 else 0
                    indDf.loc[ind, p] = '{} ({}%)'.format(no_rol_peak, pct)

                elif i == 6:
                    no_pet_peak = q_all_peaks.filter(Person.withPet == 1).count()
                    pct = round((no_pet_peak / noAll) * 100, 1) if noAll != 0 else 0
                    indDf.loc[ind, p] = '{} ({}%)'.format(no_pet_peak, pct)

                elif i == 7:
                    no_dis_peak = q_all_peaks.filter(Person.disability != 'none').count()
                    pct = round((no_dis_peak / noAll) * 100, 1) if noAll != 0 else 0
                    indDf.loc[ind, p] = '{} ({}%)'.format(no_dis_peak, pct)

                elif i == 8:
                    pass

                elif i == 9:
                    flow_all_peak = round(no_all_peak / duration_hours, 1)
                    indDf.loc[ind, p] = '{}'.format(flow_all_peak)


    elif subj == 'Vehicle':
        indicators = ['No. of all vehicles',       # 0
                      'No. of passing through vehicles',   # 1
                      'No. of arriving vehicles',  # 2
                      'No. of departing vehicles', # 3
                      'Flow of passing vehicles (veh/h)',   # 4
                      'Rate of arriving vehicles (veh/h)',  # 5
                      'Rate of departing vehicles (veh/h)', # 6
                      'No. of delayed vehicles',     # 7
                      'No. of vehicles had stop'     # 8
                      ]

        q = session.query(Vehicle.id).join(Vehicle_obs, Vehicle.id == Vehicle_obs.vehicleId) \
                   .filter(Vehicle_obs.instant >= start_obs_time) \
                   .filter(Vehicle_obs.instant <= end_obs_time)
        no_all_vehs = q.count()

        for p in entP_peakHours.keys():
            if entP_peakHours[p] is None:
                continue

            lowerBound = datetime.datetime.combine(start_obs_time.date(), entP_peakHours[p][0])
            upperBound = datetime.datetime.combine(start_obs_time.date(), entP_peakHours[p][1])

            duration = upperBound - lowerBound
            duration_in_s = duration.total_seconds()
            duration_hours = duration_in_s / 3600

            q = session.query(Vehicle.id).join(Vehicle_obs, Vehicle.id == Vehicle_obs.vehicleId) \
                                         .filter(Vehicle_obs.instant >= lowerBound)
            if entP_peakHours[p][1] in [morningPeakStart, morningPeakEnd, eveningPeakStart, eveningPeakEnd]:
                q = q.filter(Vehicle_obs.instant < upperBound)
            else:
                q = q.filter(Vehicle_obs.instant <= upperBound)

            indDf.iloc[0].loc[p] = '{}'.format(entP_peakHours[p][0].strftime('%I:%M %p'))
            indDf.iloc[1].loc[p] = '{}'.format(entP_peakHours[p][1].strftime('%I:%M %p'))
            indDf.iloc[2].loc[p] = '{}h {}m'.format(int(duration_in_s / 3600), int(duration_in_s / 60) % 60)

            for ind in indicators:

                if p == indDf.columns[0]:
                    noAll = no_all_vehs
                elif p != indDf.columns[0] and ind in list(indDf.index):
                    noAll = float(indDf.loc[ind].iloc[0].split(' ')[0])

                i = indicators.index(ind)
                if i == 0:
                    no_all_peak = q.count()
                    if p == indDf.columns[0]:
                        cell = ['{}', no_all_vehs, None]
                    else:
                        pct = round((no_all_peak / noAll) * 100, 1) if noAll != 0 else 0
                        cell = ['{} ({}%)', no_all_peak, pct]
                    indDf.loc[ind, p] = cell[0].format(cell[1], cell[2])

                elif i == 1:
                    q_pass_orig = q.join(Site_ODs, Vehicle_obs.originId == Site_ODs.id) \
                                   .filter(Site_ODs.odType == 'road_lane')
                    q_pass_dest = q.join(Site_ODs, Vehicle_obs.destinationId == Site_ODs.id) \
                                   .filter(Site_ODs.odType == 'road_lane')


                    no_pass_vehs = len(set([i[0] for i in q_pass_orig.all()]) &
                                       set([i[0] for i in q_pass_dest.all()]))
                    pct = round((no_pass_vehs / noAll) * 100, 1) if noAll != 0 else 0

                    indDf.loc[ind, p] = '{} ({}%)'.format(no_pass_vehs, pct)

                elif i == 2:
                    no_arriv_vehs = q.join(Site_ODs, Vehicle_obs.destinationId == Site_ODs.id) \
                                     .filter(Site_ODs.odType == 'on_street_parking_lot').count()
                    pct = round((no_arriv_vehs / noAll) * 100, 1) if noAll != 0 else 0

                    indDf.loc[ind, p] = '{} ({}%)'.format(no_arriv_vehs, pct)

                elif i == 3:
                    no_depart_vehs = q.join(Site_ODs, Vehicle_obs.originId == Site_ODs.id) \
                                      .filter(Site_ODs.odType == 'on_street_parking_lot').count()
                    pct = round((no_depart_vehs / noAll) * 100, 1) if noAll != 0 else 0

                    indDf.loc[ind, p] = '{} ({}%)'.format(no_depart_vehs, pct)

                elif i == 4:
                    indDf.loc[ind, p] = '{}'.format(round(no_pass_vehs / duration_hours, 1))

                elif i == 5:
                    indDf.loc[ind, p] = '{}'.format(round(no_arriv_vehs / duration_hours, 1))

                elif i == 6:
                    indDf.loc[ind, p] = '{}'.format(round(no_depart_vehs / duration_hours, 1))

                elif i == 7:
                    no_dely_vehs = q.filter(Vehicle_obs.delayed == 1).count()
                    pct = round((no_dely_vehs / noAll) * 100, 1) if noAll != 0 else 0

                    indDf.loc[ind, p] = '{} ({}%)'.format(no_dely_vehs, pct)

                elif i == 8:
                    no_stop_vehs = q.filter(Vehicle_obs.hasStop != 'no').count()
                    pct = round((no_stop_vehs / noAll) * 100, 1) if noAll != 0 else 0

                    indDf.loc[ind, p] = '{} ({}%)'.format(no_stop_vehs, pct)


    elif subj == 'Bike':
        indicators = ['No. of all cyclists',    # 0
                      'No. of cyclists riding on sidewalk',     # 1
                      'No. of cyclists riding against traffic', # 2
                      'Flow of all bikes (bik/h)'  # 3
                      ]

        q = session.query(Bike.id).join(Bike_obs, Bike.id == Bike_obs.bikeId) \
                   .filter(Bike_obs.instant >= start_obs_time) \
                   .filter(Bike_obs.instant <= end_obs_time)

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
                                 .filter(Bike_obs.instant >= lowerBound)
            if entP_peakHours[p][1] in [morningPeakStart, morningPeakEnd, eveningPeakStart, eveningPeakEnd]:
                q_all_peaks = q_all_peaks.filter(Bike_obs.instant < upperBound)
            else:
                q_all_peaks = q_all_peaks.filter(Bike_obs.instant <= upperBound)

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


    elif subj == 'Activity':
        indicators = ['Start time',  # 0
                      'End time',    # 1
                      'Duration'    # 2
                      ]
        q = session.query(Activity.activityType) \
                   .filter(Activity.startTime >= start_obs_time)\
                   .filter(Activity.startTime <= end_obs_time).distinct()

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
                           .filter(Activity.startTime >= lowerBound)
                if p == indDf.columns[0]:
                    q = q.filter(Activity.startTime <= upperBound)
                else:
                    q = q.filter(Activity.startTime < upperBound)

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


def compareIndicators(subj, session1, session2):
    start_obs_time1, end_obs_time1 = getObsStartEnd(session1)
    start_obs_time2, end_obs_time2 = getObsStartEnd(session2)

    if start_obs_time1.time() >= start_obs_time2.time():
        start_time1 = start_obs_time1
        start_time2 = datetime.datetime.combine(start_obs_time2.date(), start_obs_time1.time())
    else:
        start_time1 = datetime.datetime.combine(start_obs_time1.date(), start_obs_time2.time())
        start_time2 = start_obs_time2

    if end_obs_time1.time() <= end_obs_time2.time():
        end_time1 = end_obs_time1
        end_time2 = datetime.datetime.combine(end_obs_time2.date(), end_obs_time1.time())
    else:
        end_time1 = datetime.datetime.combine(end_obs_time1.date(), end_obs_time2.time())
        end_time2 = end_obs_time2

    indDf1 = generateReport(subj, start_time1, end_time1, session1)
    indDf2 = generateReport(subj, start_time2, end_time2, session2)

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
    site_instance = session.query(Study_site).first()
    start_obs_time = site_instance.obsStart
    end_obs_time = site_instance.obsEnd
    return start_obs_time, end_obs_time

def getOdNamesDirections(session):
    q = session.query(Site_ODs.odType, Site_ODs.odName, Site_ODs.id, Site_ODs.direction)

    pointOds = ['adjoining_ZOI', 'on_street_parking_lot', 'bicycle_rack', 'informal_bicycle_parking',
                'bus_stop', 'subway_station']
    ods_dict = {}
    for od in q.all():
        if od[1] in ods_dict.keys():
            ods_list = ods_dict[od[1]]
            if None in ods_list:
                ods_list[ods_list.index(None)] = od[2]
        else:
            if od[3].name == 'end_point':
                ods_dict[od[1]] = [None, od[2], 'directed', od[0].name]
            elif od[3].name == 'start_point':
                ods_dict[od[1]] = [od[2], None, 'directed', od[0].name]
            elif od[3].name == 'NA' and not(od[0].name in pointOds):
                ods_dict[od[1]] = [od[2], None, 'undirected', od[0].name]
            elif od[0].name in pointOds:
                ods_dict[od[1]] = [od[2], -1, 'NA', od[0].name]
    return ods_dict

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


# ======================= DEMO MODE ============================
if __name__ == '__main__':
    # tempDistHist(user = 'vehicle', od_name = 'road_2')
    # stackedHist('activities', 'activityType', 20)
    odMatrix('cyclist', session)
