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
import sqlite3
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
from iframework import connectDatabase, LineCrossing, ZoneCrossing, Person, Mode, GroupBelonging,\
    Vehicle, Line, Zone, Group, Activity

noDataSign = 'x'
userTypeNames = ['unknown', 'car', 'pedestrian', 'motorcycle', 'bicycle', 'bus', 'truck', 'automated',
                 'scooter', 'skate', 'Activity']
userTypeColors = ['gray',   'blue', 'orange',    'violet',       'green',  'yellow', 'black', 'cyan',
                  'red',  'brown', 'salmon']
plotColors = ['deepskyblue', 'salmon', 'green', 'violet', 'orange', 'yellow', 'black', 'cyan', 'brown', 'gray']

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
def tempDistHist(dbFiles, labels, transports, actionTypes, unitIdxs, directions,
                 ax=None, interval=20, plotType='Line plot', alpha=1, colors=plotColors):

    inputNo = len(dbFiles)
    sessions = []
    first_obs_times = []
    last_obs_times = []

    for i in range(inputNo):
        session = connectDatabase(dbFiles[i])
        sessions.append(session)
        if 'line' in actionTypes[i].split(' '):
            cls_obs = LineCrossing
        elif 'zone' in actionTypes[i].split(' '):
            cls_obs = ZoneCrossing

        first_obs_time = session.query(func.min(cls_obs.instant)).first()[0]
        last_obs_time = session.query(func.max(cls_obs.instant)).first()[0]

        first_obs_times.append(first_obs_time.time())
        last_obs_times.append(last_obs_time.time())

    bins_start = max(first_obs_times)
    bins_end = min(last_obs_times)

    start = datetime.datetime.combine(datetime.datetime(2000, 1, 1), bins_start)
    end = datetime.datetime.combine(datetime.datetime(2000, 1, 1), bins_end)

    bins = calculateBinsEdges(start, end, interval)

    if len(bins) < 3:
        err = 'The observation duration is not enough for the selected interval!'
        return err

    to_timestamp = np.vectorize(lambda x: x.timestamp())

    time_lists = []
    for i in range(inputNo):
        if 'line' in actionTypes[i].split(' '):
            if unitIdxs[i] == 'all_lines':
                q = sessions[i].query(func.min(LineCrossing.instant))
            else:
                q = sessions[i].query(LineCrossing.instant).filter(LineCrossing.lineIdx == unitIdxs[i])

            q = q.join(GroupBelonging, GroupBelonging.groupIdx == LineCrossing.groupIdx) \
                .join(Person, Person.idx == GroupBelonging.personIdx) \
                .join(Mode, Mode.personIdx == Person.idx) \
                .filter(Mode.transport == transports[i])

            if directions[i] == 'Right to left':
                q = q.filter(LineCrossing.rightToLeft == True)
            elif directions[i] == 'Left to right':
                q = q.filter(LineCrossing.rightToLeft == False)

            # q = q.join(GroupBelonging, GroupBelonging.groupIdx == LineCrossing.groupIdx)

        elif 'zone' in actionTypes[i].split(' '):
            q = sessions[i].query(ZoneCrossing.instant).filter(ZoneCrossing.zoneIdx == unitIdxs[i]). \
                join(GroupBelonging, GroupBelonging.groupIdx == ZoneCrossing.groupIdx)
            if 'entering' in actionTypes[i].split(' '):
                q = q.filter(ZoneCrossing.entering == True)
            elif 'exiting' in actionTypes[i].split(' '):
                q = q.filter(ZoneCrossing.entering == False)

        # q = q.join(Mode, Mode.personIdx == GroupBelonging.personIdx) \
        #     .filter(Mode.transport == transports[i])\
        if unitIdxs[i] == 'all_lines':
            q = q.group_by(Person.idx)

        time_lists.append([i[0] for i in q.all()])

    for i in range(inputNo):
        if time_lists[i] == []:
            return 'No {} is observed {} #{}!'.format(transports[i], actionTypes[i], unitIdxs[i])

    for time_list in time_lists:
        i = 0
        for time_ticks in time_list:
            time_list[i] = datetime.datetime(2000, 1, 1, time_ticks.hour, time_ticks.minute, time_ticks.second)
            i += 1

    bins_stamps = to_timestamp(bins)
    time_ticks = []
    for i in range(len(bins) - 1):
        mid_point = bins_stamps[i] + (bins_stamps[i + 1] - bins_stamps[i]) / 2
        time_ticks.append(datetime.datetime.fromtimestamp(mid_point))

    if ax == None:
        fig = plt.figure()  # figsize=(5, 5), dpi=200, tight_layout=True)
        ax = fig.add_subplot(111)  # plt.subplots(1, 1)

    if plotType == 'Line plot':
        l = 0
        for time_list in time_lists:
            time_stamps = to_timestamp(time_list)

            hist, bin_edges = np.histogram(time_stamps, bins=bins_stamps)

            ax.plot(time_ticks, hist, label=labels[l])
            l += 1
    elif plotType == 'Scatter plot':
        if inputNo != 2:
            return 'The scatter plot is possible for only two datasets!'
        time_stamps1 = to_timestamp(time_lists[0])
        hist1, bin_edges = np.histogram(time_stamps1, bins=bins_stamps)

        time_stamps2 = to_timestamp(time_lists[1])
        hist2, bin_edges = np.histogram(time_stamps2, bins=bins_stamps)

        t_min = min(time_ticks)
        t_max = max(time_ticks)
        t_range = (t_max - t_min).total_seconds()
        point_colors = []
        for t in time_ticks:
            point_colors.append((t - t_min).total_seconds() / t_range)

        sc = ax.scatter(hist1, hist2, c=point_colors, cmap='jet')

        b_inter0 = t_range/5
        if b_inter0 >= 45*60: #45min * 60sec
            b_interval = 60 #minutes
        elif 15*60 <= b_inter0 < 45*60:
            b_interval = 30
        elif 5*60 <= b_inter0 < 15*60:
            b_interval = 10
        else:
            b_interval = 5

        b_start = ceil_time(t_min, b_interval)
        cbar_ticks = []
        cbar_ticklabels = []
        while b_start < t_max:
            cbar_ticks.append((b_start - t_min).total_seconds()/t_range)
            cbar_ticklabels.append(b_start.strftime('%H:%M'))
            b_start = b_start + datetime.timedelta(minutes=b_interval)

        cbar = plt.colorbar(sc, ticks=cbar_ticks)
        cbar.ax.set_yticklabels(cbar_ticklabels, fontsize=7)
        cbar.ax.set_ylabel('Time of day', fontsize=8)

        min_val = min([min(hist1), min(hist2)])
        max_val = max([max(hist1), max(hist2)])
        ax.plot([min_val, max_val],[min_val, max_val], ls='--', lw=.5, c='k', alpha=.3)

        m, b = np.polyfit(hist1, hist2, 1)
        ax.plot(np.array(hist1), m * np.array(hist1) + b, ls='-', lw=.5, c='k', alpha=.5)

        corrcoef = round(np.corrcoef(hist1, hist2)[0, 1], 3)
        ax.text(0.9, 0.9, 'r = {}'.format(corrcoef),
                fontsize=7, color='k',
                ha='left', va='bottom',
                transform=ax.transAxes,
                weight="bold")

    if plotType == 'Line plot':
        locator = mdates.AutoDateLocator()
        ax.xaxis.set_major_locator(locator)

        # ax.xaxis.set_major_locator(mdates.HourLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

        ax.xaxis.set_minor_locator(mdates.MinuteLocator(byminute=30))
        # print((locator()))

        if inputNo == 1:
            xLabel = 'Time ({})'.format(bins_start.strftime('%A, %b %d, %Y'))
        else:
            xLabel = 'Time'

        # ax.set_xticklabels(fontsize = 6, rotation = 45)#'vertical')
        ax.tick_params(axis='x', labelsize=8, rotation=0)
        ax.tick_params(axis='y', labelsize=7)
        ax.set_xlabel(xLabel, fontsize=8)

        tm = transports[0]
        if transports[0] == 'cardriver':
            tm = 'car'
        elif transports[0] == 'walking':
            tm = 'pedestrian'

        ax.set_ylabel('No. of {}s'.format(tm), fontsize=8)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.set_title('Temporal distribution of {}s {} #{}'.format(tm, actionTypes[0], unitIdxs[0]),
                     fontsize=8)
        ax.legend(loc='upper right', fontsize=6)

    elif plotType == 'Scatter plot':

        # max_val = max(max(hist1), max(hist2))
        # ax.set_xlim(0, max_val + 10)
        # ax.set_ylim(0, max_val + 10)

        ax.tick_params(axis='both', labelsize=7)

        tm1 = transports[0]
        tm2 = transports[1]
        if transports[0] == 'cardriver':
            tm1 = 'car'
        elif transports[0] == 'walking':
            tm1 = 'pedestrian'
        if transports[1] == 'cardriver':
            tm2 = 'car'
        elif transports[1] == 'walking':
            tm2 = 'pedestrian'

        ax.set_xlabel('Number of {}s ({})'.format(tm1, labels[0]), fontsize=8)
        ax.set_ylabel('Number of {}s ({})'.format(tm2, labels[1]), fontsize=8)
        ax.set_title('Scatter plot of {}s {} #{}'.format(tm1, actionTypes[0], unitIdxs[0]),
                     fontsize=8)
        ax.axis('equal')

    ax.grid(True, 'major', 'both', ls='--', lw=.5, c='k', alpha=.3)

    ax.text(0.03, 0.93, str('StudioProject'),
            fontsize=9, color='gray',
            ha='left', va='bottom',
            transform=ax.transAxes,
            weight="bold", alpha=.5)

        # # plt.show()

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

    ax.text(0.03, 0.93, str('StudioProject'),
            fontsize=9, color='gray',
            ha='left', va='bottom',
            transform=ax.transAxes,
            weight="bold", alpha=.5)

    # plt.show()


# ==============================================================
def speedHistogram(dbFiles, labels, transports, actionTypes, unitIdxs, directions,
                 ax=None, interval=20, alpha=1, colors=plotColors, ec='k', rwidth=0.9):
    inputNo = len(dbFiles)
    speed_lists = []
    # sessions = []
    for i in range(inputNo):
        session = connectDatabase(dbFiles[i])

        if unitIdxs[i] == 'all_lines':
            q = session.query(func.sum(LineCrossing.speed), func.count(LineCrossing.speed))
        else:
            q = session.query(LineCrossing.speed).filter(LineCrossing.lineIdx == unitIdxs[i])

        q = q.join(GroupBelonging, GroupBelonging.groupIdx == LineCrossing.groupIdx) \
            .join(Person, Person.idx == GroupBelonging.personIdx) \
            .join(Mode, Mode.personIdx == Person.idx) \
            .filter(Mode.transport == transports[i])

        if directions[i] == 'Right to left':
            q = q.filter(LineCrossing.rightToLeft == True)
        elif directions[i] == 'Left to right':
            q = q.filter(LineCrossing.rightToLeft == False)

        if unitIdxs[i] == 'all_lines':
            q = q.group_by(Person.idx)
            speed_lists.append([i[0]/i[1] for i in q.all() if i[0] is not None])
        else:
            speed_lists.append([i[0] for i in q.all() if i[0] is not None])


    # bins_start = int(np.floor(min([min(speed_list1), min(speed_list2)])))
    bins_end = np.ceil(max([max(speed_list) for speed_list in speed_lists if speed_list != []]))
    bins_end = int(((bins_end // 10) + 1) * 10)

    bins = [b for b in range(0, bins_end, interval)]

    if ax == None:
        fig = plt.figure()
        ax = fig.add_subplot(111)

    for i in range(inputNo):
        ax.hist(speed_lists[i], alpha=alpha, color=colors[i], ec=ec, label=labels[i],
                rwidth=rwidth, bins=bins)

    ax.tick_params(axis='x', labelsize=8, rotation=0)
    ax.tick_params(axis='y', labelsize=7)
    ax.set_xlabel('Speed (km/h)', fontsize=8)
    ax.legend(fontsize=5)
    # ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    userTitle = transports[0]
    if transports[0] == 'cardriver':
        userTitle = 'car'
    elif transports[0] == 'walking':
        userTitle = 'pedestrian'
    ax.set_title('Speed histogram of {}s {} #{}'.format(userTitle, actionTypes[0], unitIdxs[0]), fontsize=8)
    ax.grid(True, 'major', 'y', ls='--', lw=.5, c='k', alpha=.3)

    ax.text(0.03, 0.93, str('StudioProject'),
            fontsize=9, color='gray',
            ha='left', va='bottom',
            transform=ax.transAxes,
            weight="bold", alpha=.5)



def speedBoxPlot(dbFiles, labels, transports, actionTypes, unitIdxs, directions,
                 ax=None, interval=20, alpha=1, colors=plotColors):

    inputNo = len(dbFiles)
    sessions = []
    first_obs_times = []
    last_obs_times = []

    for i in range(inputNo):
        session = connectDatabase(dbFiles[i])
        sessions.append(session)

    for i in range(inputNo):
        if 'line' in actionTypes[i].split(' '):
            cls_obs = LineCrossing
        elif 'zone' in actionTypes[i].split(' '):
            cls_obs = ZoneCrossing

        first_obs_time = session.query(func.min(cls_obs.instant)).first()[0]
        last_obs_time = session.query(func.max(cls_obs.instant)).first()[0]

        first_obs_times.append(first_obs_time.time())
        last_obs_times.append(last_obs_time.time())

    bins_start = max(first_obs_times)
    bins_end = min(last_obs_times)

    start = datetime.datetime.combine(datetime.datetime(2000,1,1), bins_start)
    end = datetime.datetime.combine(datetime.datetime(2000,1,1), bins_end)

    bin_edges = calculateBinsEdges(start, end, interval)

    if len(bin_edges) < 3:
        err = 'The observation duration is not enough for the selected interval!'
        return err

    times = [b.time() for b in bin_edges]

    bins = []
    for i in range(inputNo):
        date1 = getObsStartEnd(sessions[i])[0].date()
        bins.append([datetime.datetime.combine(date1, t) for t in times])

    grouped_speeds = []
    for j, session in enumerate(sessions):
        time_list = []
        if 'line' in actionTypes[j].split(' '):
            if unitIdxs[j] == 'all_lines':
                q = session.query(func.min(LineCrossing.instant), func.sum(LineCrossing.speed),
                                  func.count(LineCrossing.speed))
            else:
                q = session.query(LineCrossing.instant, LineCrossing.speed)\
                           .filter(LineCrossing.lineIdx == unitIdxs[j])

            q = q.join(GroupBelonging, GroupBelonging.groupIdx == LineCrossing.groupIdx) \
                .join(Person, Person.idx == GroupBelonging.personIdx) \
                .join(Mode, Mode.personIdx == Person.idx) \
                .filter(Mode.transport == transports[j])

            # q = session.query(LineCrossing.instant, LineCrossing.speed).\
            #     filter(LineCrossing.lineIdx == unitIdxs[j]). \
            #     join(GroupBelonging, GroupBelonging.groupIdx == LineCrossing.groupIdx)
            if directions[j] == 'Right to left':
                q = q.filter(LineCrossing.rightToLeft == True)
            elif directions[j] == 'Left to right':
                q = q.filter(LineCrossing.rightToLeft == False)
        elif 'zone' in actionTypes[j].split(' '):
            return 'Under developement!'
        # q = q.join(Mode, Mode.personIdx == GroupBelonging.personIdx)\
        #     .filter(Mode.transport == transports[j])

        if unitIdxs[j] == 'all_lines':
            q = q.group_by(Person.idx)
            time_list = [i[0] for i in q.all()]
            speed_list = [i[1]/i[2] if i[1] is not None else None for i in q.all()]
        else:
            time_list = [i[0] for i in q.all()]
            speed_list = [i[1] for i in q.all()]

        # time_list = [i[0] for i in q.all()]
        # speed_list = [i[1] for i in q.all()]

        if time_list == []:
            return 'No {} is observed {} #{}!'.format(transports[0], actionTypes[0], unitIdxs[0])

        time_list_i8 = np.array([np.datetime64(t) for t in time_list]).view('i8')
        bins_i8 = np.array([np.datetime64(b) for b in bins[j]]).view('i8')
        inds = np.digitize(time_list_i8, bins_i8)
        grouped_speed = []
        for i in range(len(bins[j]) - 1):
            grouped_speed.append([])
        i = 0
        for ind in inds:
            if 0 < ind < len(bins[j]):
                if speed_list[i] is not None:
                    grouped_speed[ind - 1].append(speed_list[i])
            i += 1
        grouped_speeds.append(grouped_speed)
    
    ticks = []
    for i in range(len(bins[0]) - 1):
        t = (bins[0][i] + (bins[0][i + 1] - bins[0][i]) / 2).time()
        ticks.append(t.strftime('%H:%M'))

    def set_box_color(bp, color):
        plt.setp(bp['boxes'], color=color)
        plt.setp(bp['whiskers'], color=color)
        plt.setp(bp['caps'], color=color)
        plt.setp(bp['medians'], color=color)
        plt.setp(bp['means'], color=color)

    if ax == None:
        fig = plt.figure()
        ax = fig.add_subplot(111)

    for i in range(inputNo):
        bp = ax.boxplot(grouped_speeds[i],
                        positions=np.array(range(len(grouped_speeds[i]))) * 2.0 - (-1)**i * 0.4 * (inputNo -1),
                        sym='', widths=0.6, showmeans=False, patch_artist=False)
        set_box_color(bp, colors[i])
        # draw temporary red and blue lines and use them to create a legend
        ax.plot([], c=colors[i], label=labels[i])

    ax.legend(fontsize=5)

    # ----------------------
    # locator = mdates.AutoDateLocator()
    # ax.xaxis.set_major_locator(locator)
    # ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    # ax.xaxis.set_minor_locator(mdates.MinuteLocator(byminute=30))
    # ----------------------------

    ax.set_xticks(range(0, len(ticks) * 2, 2))
    ax.set_xticklabels(ticks)
    ax.set_xlim(-1, len(ticks) * 2)

    ax.tick_params(axis='x', labelsize=8, rotation=0)
    ax.tick_params(axis='y', labelsize=7)
    ax.set_xlabel('Time', fontsize=8)
    ax.set_ylabel('Speed (km/h)', fontsize=8)
    # ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    userTitle = transports[0]
    if transports[0] == 'cardriver':
        userTitle = 'car'
    elif transports[0] == 'walking':
        userTitle = 'pedestrian'
    ax.set_title('Speed of {}s {} #{}'.format(userTitle, actionTypes[0], unitIdxs[0]), fontsize=8)
    ax.grid(True, 'major', 'y', ls='--', lw=.5, c='k', alpha=.3)

    ax.text(0.03, 0.93, str('StudioProject'),
            fontsize=9, color='gray',
            ha='left', va='bottom',
            transform=ax.transAxes,
            weight="bold", alpha=.5)


# ==============================================================
def speedOverSpacePlot(dbFiles, labels, transports, actionTypes, unitIdxs, directions, metadataFile,
                 ax=None, interval=0.5, alpha=1, colors=plotColors):
    inputNo = len(dbFiles)
    sessions = []
    first_obs_times = []
    last_obs_times = []

    for i in range(inputNo):
        session = connectDatabase(dbFiles[i])
        sessions.append(session)

    for i in range(inputNo):
        if 'line' in actionTypes[i].split(' '):
            cls_obs = LineCrossing
        elif 'zone' in actionTypes[i].split(' '):
            cls_obs = ZoneCrossing

        first_obs_time = session.query(func.min(cls_obs.instant)).first()[0]
        last_obs_time = session.query(func.max(cls_obs.instant)).first()[0]

        first_obs_times.append(first_obs_time.time())
        last_obs_times.append(last_obs_time.time())

    bins_start = max(first_obs_times)
    bins_end = min(last_obs_times)

    # start = datetime.datetime.combine(datetime.datetime(2000, 1, 1), bins_start)
    # end = datetime.datetime.combine(datetime.datetime(2000, 1, 1), bins_end)
    # bin_edges = calculateBinsEdges(start, end, interval)
    # if len(bin_edges) < 3:
    #     err = 'The observation duration is not enough for the selected interval!'
    #     return err
    # times = [b.time() for b in bin_edges]

    times = [bins_start, bins_end]

    bins = []
    for i in range(inputNo):
        date1 = getObsStartEnd(sessions[i])[0].date()
        bins.append([datetime.datetime.combine(date1, t) for t in times])

    all_x_arrays = []
    all_speed_arrays = []
    for j, session in enumerate(sessions):
        time_list = []
        if 'line' in actionTypes[j].split(' '):
            if unitIdxs[j] == 'all_lines':
                q = session.query(func.min(LineCrossing.instant), Group.trajectoryDB, Group.trajectoryIdx)
            else:
                q = session.query(LineCrossing.instant, Group.trajectoryDB, Group.trajectoryIdx) \
                    .filter(LineCrossing.lineIdx == unitIdxs[j])

            q = q.join(GroupBelonging, GroupBelonging.groupIdx == LineCrossing.groupIdx) \
                .join(Group, Group.idx == GroupBelonging.groupIdx) \
                .join(Person, Person.idx == GroupBelonging.personIdx) \
                .join(Mode, Mode.personIdx == Person.idx) \
                .filter(Mode.transport == transports[j]) \
                .filter(LineCrossing.instant >= bins[j][0]) \
                .filter(LineCrossing.instant < bins[j][1])

            if directions[j] == 'Right to left':
                q = q.filter(LineCrossing.rightToLeft == True)
            elif directions[j] == 'Left to right':
                q = q.filter(LineCrossing.rightToLeft == False)
        elif 'zone' in actionTypes[j].split(' '):
            return 'Under developement!'

        if unitIdxs[j] == 'all_lines':
            q = q.group_by(Person.idx)
            traj_DB_list = [i[1] for i in q.all()]
            traj_Idx_list = [i[2] for i in q.all()]
        else:
            traj_DB_list = [i[1] for i in q.all()]
            traj_Idx_list = [i[2] for i in q.all()]


        if traj_DB_list == []:
            return 'No {} is observed {} #{}!'.format(transports[0], actionTypes[0], unitIdxs[0])

        traj_DB_Idxs = {}
        for i in range(len(traj_DB_list)):
            if traj_DB_list[i] != None:
                if traj_DB_list[i] in traj_DB_Idxs.keys():
                    traj_DB_Idxs[traj_DB_list[i]].append(traj_Idx_list[i])
                else:
                    traj_DB_Idxs[traj_DB_list[i]] = [traj_Idx_list[i]]

        x_arrays = []
        speed_arrays = []
        for db_Idx in traj_DB_Idxs.keys():
            con = sqlite3.connect(metadataFile)
            cur = con.cursor()
            cur.execute('SELECT databaseFilename, cameraViewIdx FROM video_sequences WHERE idx=?', (db_Idx,))
            row = cur.fetchall()
            date_dbName = row[0][0]
            cam_view_id = row[0][1]
            cur.execute('SELECT siteIdx, cameraTypeIdx FROM camera_views WHERE idx=?', (cam_view_id,))
            row = cur.fetchall()
            site_idx = row[0][0]
            cam_type_idx = row[0][1]
            cur.execute('SELECT name FROM sites WHERE idx=?', (site_idx,))
            row = cur.fetchall()
            site_name = row[0][0]
            cur.execute('SELECT frameRate FROM camera_types WHERE idx=?', (cam_type_idx,))
            row = cur.fetchall()
            frameRate = row[0][0]

            mdbPath = Path(metadataFile).parent
            trjDBFile = mdbPath / site_name / date_dbName
            objects = storage.loadTrajectoriesFromSqlite(trjDBFile, 'object')
            for trj_idx in traj_DB_Idxs[db_Idx]:
                for traj in objects:
                    if str(traj.getNum()) == trj_idx:
                        x_arrays.append(traj.positions.asArray()[0])
                        speed_arrays.append(np.round(traj.getSpeeds()* frameRate * 3.6, 1))
        all_x_arrays.append(x_arrays)
        all_speed_arrays.append(speed_arrays)

    x_mins = []
    x_maxs = []
    for i, x_arrs in enumerate(all_x_arrays):
        x_mins.append(np.min([np.min(x_arr) for x_arr in x_arrs]))
        x_maxs.append(np.max([np.max(x_arr) for x_arr in x_arrs]))

    x_min = np.max(x_mins)
    x_max = np.min(x_maxs)

    bins = np.arange(90, 140, interval).tolist()

    grouped_speeds = []
    for i, x_arrs in enumerate(all_x_arrays):
        grouped_speed = []

        for _ in range(len(bins) - 1):
            grouped_speed.append(np.array([]))

        for j, x_arr in enumerate(x_arrs):
            inds = np.digitize(x_arr, bins)

            for k, ind in enumerate(inds):
                if 0 < ind < len(bins):
                    grouped_speed[ind - 1] = np.append(grouped_speed[ind - 1], all_speed_arrays[i][j][k])

        grouped_speeds.append(grouped_speed)


    if ax == None:
        fig = plt.figure()
        ax = fig.add_subplot(111)

    for i, grouped_speed in enumerate(grouped_speeds):
        x = []
        for n in range(len(bins) - 1):
            x.append(bins[n] + (interval / 2))
        speed = np.array([])
        std_speed = np.array([])
        for j, speeds in enumerate(grouped_speed):
            if speeds != np.array([]):
                speed = np.append(speed,
                                  np.mean(speeds[abs(speeds - np.mean(speeds)) < 1.5 * np.std(speeds)]))
                std_speed = np.append(std_speed,
                                      np.std(speeds[abs(speeds - np.mean(speeds)) < 1.5 * np.std(speeds)]))
            else:
                x[j] = None
        x = [n for n in x if n is not None]
        # [abs(speeds - np.mean(speeds)) < 1.5 * np.std(speeds)]
        # speed = np.array([np.mean(speeds) for speeds in grouped_speed if speeds != np.array([])])
        # std_speed = np.array([np.std(speeds) for speeds in grouped_speed if speeds != np.array([])])

        ax.fill_between(x, speed - std_speed, speed + std_speed,
                        color=colors[i], ec=colors[i], alpha=0.2, label='Std. of {}'.format(labels[i]))
        ax.plot(x, speed, c=colors[i], label=labels[i])


    ax.legend(fontsize=5)

    # ax.set_xticks(range(0, len(ticks) * 2, 2))
    # ax.set_xticklabels(ticks)
    # ax.set_xlim(-1, len(ticks) * 2)

    ax.tick_params(axis='x', labelsize=8, rotation=0)
    ax.tick_params(axis='y', labelsize=7)
    ax.set_xlabel('Location', fontsize=8)
    ax.set_ylabel('Speed (km/h)', fontsize=8)
    # ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    userTitle = transports[0]
    if transports[0] == 'cardriver':
        userTitle = 'car'
    elif transports[0] == 'walking':
        userTitle = 'pedestrian'
    ax.set_title('Speed of {}s {} #{}'.format(userTitle, actionTypes[0], unitIdxs[0]), fontsize=8)
    ax.grid(True, 'major', 'y', ls='--', lw=.5, c='k', alpha=.3)

    ax.text(0.03, 0.93, str('StudioProject'),
            fontsize=9, color='gray',
            ha='left', va='bottom',
            transform=ax.transAxes,
            weight="bold", alpha=.5)

# ==============================================================
def speedSpaceTimePlot(dbFiles, labels, transports, actionTypes, unitIdxs, directions, metadataFile,
                 ax=None, interval_space=0.5, interval_time=10, colors=plotColors):
    inputNo = len(dbFiles)
    sessions = []
    first_obs_times = []
    last_obs_times = []

    for i in range(inputNo):
        session = connectDatabase(dbFiles[i])
        sessions.append(session)

    for i in range(inputNo):
        if 'line' in actionTypes[i].split(' '):
            cls_obs = LineCrossing
        elif 'zone' in actionTypes[i].split(' '):
            cls_obs = ZoneCrossing

        first_obs_time = session.query(func.min(cls_obs.instant)).first()[0]
        last_obs_time = session.query(func.max(cls_obs.instant)).first()[0]

        first_obs_times.append(first_obs_time.time())
        last_obs_times.append(last_obs_time.time())

    bins_start = max(first_obs_times)
    bins_end = min(last_obs_times)

    start = datetime.datetime.combine(datetime.datetime(2000, 1, 1), bins_start)
    end = datetime.datetime.combine(datetime.datetime(2000, 1, 1), bins_end)
    time_bin_edges = calculateBinsEdges(start, end, interval_time)
    if len(time_bin_edges) < 3:
        err = 'The observation duration is not enough for the selected interval!'
        return err
    times = [b.time() for b in time_bin_edges]

    time_bins = []
    for i in range(inputNo):
        date1 = getObsStartEnd(sessions[i])[0].date()
        time_bins.append([datetime.datetime.combine(date1, t) for t in times])

    all_x_arrays = []
    all_speed_arrays = []
    all_trj_time_inds = []
    for j, session in enumerate(sessions):
        if 'line' in actionTypes[j].split(' '):
            if unitIdxs[j] == 'all_lines':
                q = session.query(func.min(LineCrossing.instant), Group.trajectoryDB, Group.trajectoryIdx)
            else:
                q = session.query(LineCrossing.instant, Group.trajectoryDB, Group.trajectoryIdx) \
                    .filter(LineCrossing.lineIdx == unitIdxs[j])

            q = q.join(GroupBelonging, GroupBelonging.groupIdx == LineCrossing.groupIdx) \
                .join(Group, Group.idx == GroupBelonging.groupIdx) \
                .join(Person, Person.idx == GroupBelonging.personIdx) \
                .join(Mode, Mode.personIdx == Person.idx) \
                .filter(Mode.transport == transports[j]) #\
                # .filter(LineCrossing.instant >= time_bins[j][0]) \
                # .filter(LineCrossing.instant < time_bins[j][-1])

            if directions[j] == 'Right to left':
                q = q.filter(LineCrossing.rightToLeft == True)
            elif directions[j] == 'Left to right':
                q = q.filter(LineCrossing.rightToLeft == False)
        elif 'zone' in actionTypes[j].split(' '):
            return 'Under developement!'

        if unitIdxs[j] == 'all_lines':
            q = q.group_by(Person.idx)
            cross_inst_list = [i[0] for i in q.all()]
            traj_DB_list = [i[1] for i in q.all()]
            traj_Idx_list = [i[2] for i in q.all()]
        else:
            cross_inst_list = [i[0] for i in q.all()]
            traj_DB_list = [i[1] for i in q.all()]
            traj_Idx_list = [i[2] for i in q.all()]

        if traj_DB_list == []:
            return 'No {} is observed {} #{}!'.format(transports[0], actionTypes[0], unitIdxs[0])

        cross_inst_list_i8 = np.array([np.datetime64(t) for t in cross_inst_list]).view('i8')
        time_bins_i8 = np.array([np.datetime64(b) for b in time_bins[j]]).view('i8')
        time_inds = np.digitize(cross_inst_list_i8, time_bins_i8)

        # grouped_speed = []
        # for i in range(len(bins[j]) - 1):
        #     grouped_speed.append([])
        # i = 0
        # for ind in inds:
        #     if 0 < ind < len(bins[j]):
        #         if speed_list[i] is not None:
        #             grouped_speed[ind - 1].append(speed_list[i])
        #     i += 1
        # grouped_speeds.append(grouped_speed)

        traj_DB_Idxs = {}
        for i in range(len(traj_DB_list)):
            if traj_DB_list[i] != None:
                if traj_DB_list[i] in traj_DB_Idxs.keys():
                    traj_DB_Idxs[traj_DB_list[i]].append([traj_Idx_list[i], time_inds[i]])
                else:
                    traj_DB_Idxs[traj_DB_list[i]] = [[traj_Idx_list[i], time_inds[i]]]

        x_arrays = []
        speed_arrays = []
        trj_time_inds = []
        for db_Idx in traj_DB_Idxs.keys():
            con = sqlite3.connect(metadataFile)
            cur = con.cursor()
            cur.execute('SELECT databaseFilename, cameraViewIdx FROM video_sequences WHERE idx=?', (db_Idx,))
            row = cur.fetchall()
            date_dbName = row[0][0]
            cam_view_id = row[0][1]
            cur.execute('SELECT siteIdx, cameraTypeIdx FROM camera_views WHERE idx=?', (cam_view_id,))
            row = cur.fetchall()
            site_idx = row[0][0]
            cam_type_idx = row[0][1]
            cur.execute('SELECT name FROM sites WHERE idx=?', (site_idx,))
            row = cur.fetchall()
            site_name = row[0][0]
            cur.execute('SELECT frameRate FROM camera_types WHERE idx=?', (cam_type_idx,))
            row = cur.fetchall()
            frameRate = row[0][0]

            mdbPath = Path(metadataFile).parent
            trjDBFile = mdbPath / site_name / date_dbName
            objects = storage.loadTrajectoriesFromSqlite(trjDBFile, 'object')
            for trj_idx_ind in traj_DB_Idxs[db_Idx]:
                for traj in objects:
                    if str(traj.getNum()) == trj_idx_ind[0]:
                        x_arrays.append(traj.positions.asArray()[0])
                        speed_arrays.append(np.round(traj.getSpeeds()* frameRate * 3.6, 1))
                        trj_time_inds.append(trj_idx_ind[1])
        all_x_arrays.append(x_arrays)
        all_speed_arrays.append(speed_arrays)
        all_trj_time_inds.append(trj_time_inds)

    x_mins = []
    x_maxs = []
    for i, x_arrs in enumerate(all_x_arrays):
        x_mins.append(np.min([np.min(x_arr) for x_arr in x_arrs]))
        x_maxs.append(np.max([np.max(x_arr) for x_arr in x_arrs]))

    x_min = np.max(x_mins)
    x_max = np.min(x_maxs)
    space_bins = np.arange(x_min, x_max, interval_space).tolist()

    grouped_speeds = []
    for i, x_arrs in enumerate(all_x_arrays):
        grouped_speed = []

        for r in range(len(time_bins[i]) - 1):
            grouped_speed.append([])
            for c in range(len(space_bins) - 1):
                grouped_speed[r].append(np.array([]))

        for j, x_arr in enumerate(x_arrs):
            space_inds = np.digitize(x_arr, space_bins)

            for k, ind in enumerate(space_inds):
                if 0 < ind < len(space_bins):
                    if 0 < all_trj_time_inds[i][j] < len(time_bins[i]):
                        grouped_speed[-all_trj_time_inds[i][j]][ind - 1] = \
                            np.append(grouped_speed[-all_trj_time_inds[i][j]][ind - 1],
                                                     all_speed_arrays[i][j][k])

        grouped_speeds.append(grouped_speed)


    if ax == None:
        fig = plt.figure()
        ax = fig.add_subplot(111)

    to_timestamp = np.vectorize(lambda x: x.timestamp())

    for i, grouped_speed in enumerate(grouped_speeds):

        x = []
        for n in range(len(space_bins) - 1):
            x.append(space_bins[n] + (interval_space / 2))

        t = []
        bins_stamps = to_timestamp(time_bins[i])
        for k in range(len(time_bins[i]) - 1):
            mid_point = bins_stamps[k] + (bins_stamps[k + 1] - bins_stamps[k]) / 2
            t.append(datetime.datetime.fromtimestamp(mid_point))

        speed = []
        for m in range(len(grouped_speed)):
            speed.append([])
            for n in range(len(grouped_speed[0])):
                speed[m].append(np.nan)

        for r, speeds_list in enumerate(grouped_speed):
            for c, speeds in enumerate(speeds_list):
                if speeds != np.array([]):
                    speed[r][c] = round(
                        np.mean(speeds),2)#[abs(speeds - np.mean(speeds)) < 1.5 * np.std(speeds)]), 2)

        t_lims = mdates.date2num([t[0], t[-1]])
        im = ax.imshow(speed, extent=[x[0], x[-1], t_lims[0], t_lims[-1]], origin='lower',
           cmap='RdYlBu_r', aspect='auto') #np.array(speed, dtype=float))

        ax.yaxis_date()
        # locator = mdates.AutoDateLocator()
        # ax.xaxis.set_major_locator(locator)
        date_format = mdates.DateFormatter('%H:%M')

        ax.yaxis.set_major_formatter(date_format)
        cbar = plt.colorbar(im)
        cbar.ax.tick_params(labelsize=8)

    ax.tick_params(axis='x', labelsize=8, rotation=0)
    ax.tick_params(axis='y', labelsize=8)
    ax.set_xlabel('Location (m.)', fontsize=8)
    ax.set_ylabel('Time of day', fontsize=8)
    # ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    userTitle = transports[0]
    if transports[0] == 'cardriver':
        userTitle = 'car'
    elif transports[0] == 'walking':
        userTitle = 'pedestrian'
    ax.set_title('Speed of {}s {} #{}'.format(userTitle, actionTypes[0], unitIdxs[0]), fontsize=8)
    # ax.grid(True, 'major', 'y', ls='--', lw=.5, c='k', alpha=.3)

    ax.text(0.03, 0.93, str('StudioProject'),
            fontsize=9, color='gray',
            ha='left', va='bottom',
            transform=ax.transAxes,
            weight="bold", alpha=.5)



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
                                      shadow=False, startangle=90, textprops={'size': 16, 'weight':'bold'})
    color_dict = {'walking':'forestgreen', 'cardriver':'salmon', 'bike':'deepskyblue',
                  'scooter':'orange', 'skating':'pink'}
    for pie_wedge in wedges:
        # pie_wedge.set_edgecolor('white')
        pie_wedge.set_facecolor(color_dict[pie_wedge.get_label()])

    ax.axis('equal')
    # ax.legend(wedges, labels,
    #           title="title",
    #           loc="upper right")

    plt.setp(autotexts, size=12, weight="bold")

# =====================================================================
def generateReport(dbFileName, transport, actionType, unitIdx, direction, interval,
                   start_time=None, end_time=None):

    session = connectDatabase(dbFileName)

    if start_time == None and end_time == None:
        start_obs_time, end_obs_time = getObsStartEnd(session)

    elif start_time != None and end_time != None:
        obs_date = getObsStartEnd(session)[0].date()
        start_obs_time = datetime.datetime.combine(obs_date, start_time)
        end_obs_time = datetime.datetime.combine(obs_date, end_time)
    else:
        return

    entP_peakHours = getPeakHours(start_obs_time, end_obs_time, interval)

    indDf = pd.DataFrame(columns=list(entP_peakHours.keys()))#, index=['Start time', 'End time', 'Duration'])

    duration = end_obs_time - start_obs_time
    duration_in_s = duration.total_seconds()
    duration_hours = duration_in_s / 3600

    if 'line' in actionType.split(' '):
        if unitIdx == 'all_lines':
            q = session.query(LineCrossing.groupIdx, func.sum(LineCrossing.speed), func.count(LineCrossing.speed))
        else:
            q = session.query(LineCrossing.groupIdx, LineCrossing.speed) \
                .filter(LineCrossing.lineIdx == unitIdx)

        q = q.join(GroupBelonging, GroupBelonging.groupIdx == LineCrossing.groupIdx) \
            .join(Person, Person.idx == GroupBelonging.personIdx) \
            .join(Mode, Mode.personIdx == Person.idx) \
            .filter(Mode.transport == transport) \
            .filter(LineCrossing.instant >= start_obs_time) \
            .filter(LineCrossing.instant < end_obs_time)

        if direction == 'Right to left':
            q = q.filter(LineCrossing.rightToLeft == True)
        elif direction == 'Left to right':
            q = q.filter(LineCrossing.rightToLeft == False)

    elif 'zone' in actionType.split(' '):
        q = session.query(ZoneCrossing.idx) \
            .filter(ZoneCrossing.instant >= start_obs_time) \
            .filter(ZoneCrossing.instant < end_obs_time) \
            .join(GroupBelonging, GroupBelonging.groupIdx == ZoneCrossing.groupIdx)

    if unitIdx == 'all_lines':
        q = q.group_by(Person.idx)

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

            q_all_peaks = q.filter(LineCrossing.instant >= lowerBound)\
                           .filter(LineCrossing.instant < upperBound)

            no_all_peak = q_all_peaks.count()

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

                elif 7 < i < 13:
                    rec_list = q_all_peaks.all()
                    if rec_list != []:
                        groups_dict = {i[0]: rec_list.count(i) for i in rec_list}
                        sizes_list = list(groups_dict.values())
                        groups_count = {i: sizes_list.count(i) for i in sizes_list}
                        if i == 8:
                            indDf.loc[ind, p] = '{}'.format(len(sizes_list))
                        elif i == 9 and 1 in groups_count:
                            indDf.loc[ind, p] = '{}'.format(groups_count[1])
                        elif i == 10 and 2 in groups_count:
                            indDf.loc[ind, p] = '{}'.format(groups_count[2])
                        elif i == 11 and 3 in groups_count:
                            indDf.loc[ind, p] = '{}'.format(groups_count[3])
                        elif i == 12 and 4 in groups_count:
                            indDf.loc[ind, p] = '{}'.format(groups_count[4])
                        else:
                            indDf.loc[ind, p] = '{}'.format(0)
                    else:
                        indDf.loc[ind, p] = '{}'.format(0)



    elif transport == 'cardriver':
        if 'line' in actionType.split(' '):
            indicators = ['No. of all vehicles passing through',   # 0
                          'Flow of passing vehicles (veh/h)', # 1
                          'Speed average (km/h)',    # 2
                          'Speed standard deviation (km/h)',  # 3
                          'Speed median (km/h)',  # 4
                          'Speed 85th percentile (km/h)'  # 5
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

            q_all_peaks = q.filter(LineCrossing.instant >= lowerBound) \
                           .filter(LineCrossing.instant < upperBound)

            no_all_peak = q_all_peaks.count()

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

                elif i == 1:
                    indDf.loc[ind, p] = '{}'.format(round(no_all_peak / duration_hours, 1))

                elif 1 < i < 6:
                    rec_list = q_all_peaks.all()
                    if rec_list != []:
                        if unitIdx == 'all_lines':
                            speed_list = [i[1]/i[2] for i in rec_list if i[1] != None]
                        else:
                            speed_list = [i[1] for i in rec_list if i[1] != None]
                        if i == 2:
                            stat_val = round(np.mean(speed_list), 1)
                        elif i == 3:
                            stat_val = round(np.std(speed_list), 1)
                        elif i == 4:
                            stat_val = round(np.median(speed_list), 1)
                        elif i == 5:
                            stat_val = round(np.percentile(speed_list, 85), 1)
                    else:
                        stat_val = 0
                    indDf.loc[ind, p] = '{}'.format(stat_val)


    elif transport == 'cycling':
        if 'line' in actionType.split(' '):
            indicators = ['No. of all cyclists',    # 0
                          'No. of cyclists riding on sidewalk',     # 1
                          'No. of cyclists riding against traffic', # 2
                          'Flow of all bikes (bik/h)',  # 3
                          'No. of female cyclists'  #4
                          ]

        no_all_biks = q.count()

        if no_all_biks == 0:
            return indDf

        for p in entP_peakHours.keys():
            if entP_peakHours[p] is None:
                continue

            lowerBound = datetime.datetime.combine(start_obs_time.date(), entP_peakHours[p][0])
            upperBound = datetime.datetime.combine(start_obs_time.date(), entP_peakHours[p][1])

            duration = upperBound - lowerBound
            duration_in_s = duration.total_seconds()
            duration_hours = duration_in_s / 3600

            q_all_peaks = q.filter(LineCrossing.instant >= lowerBound) \
                           .filter(LineCrossing.instant < upperBound)

            no_all_peak = q_all_peaks.count()

            for ind in indicators:

                if p == indDf.columns[0]:
                    noAll = no_all_biks
                elif p != indDf.columns[0] and ind in list(indDf.index):
                    noAll = float(indDf.loc[ind].iloc[0].split(' ')[0])

                i = indicators.index(ind)
                if i == 0:
                    if p == indDf.columns[0]:
                        indDf.loc[ind, p] = '{}'.format(no_all_biks)
                    else:
                        pct = round((no_all_peak / noAll) * 100, 1) if noAll != 0 else 0
                        indDf.loc[ind, p] = '{} ({}%)'.format(no_all_peak, pct)

                elif i == 1:
                    q_lineType_peak = q_all_peaks.join(Line, Line.idx == LineCrossing.lineIdx).\
                        filter(Line.type == 'sidewalk')
                    no_sdwk_peak = q_lineType_peak.count()
                    pct = round((no_sdwk_peak / noAll) * 100, 1) if noAll != 0 else 0
                    indDf.loc[ind, p] = '{} ({}%)'.format(no_sdwk_peak, pct)

                # elif i ==2:
                #     q_against = q_all_peaks.join(Site_ODs, Bike_obs.originId == Site_ODs.id) \
                #         .filter(Site_ODs.direction == 'end_point')
                #
                #     no_agst_peak = q_against.count()
                #     pct = round((no_agst_peak / noAll) * 100, 1) if noAll != 0 else 0
                #     indDf.loc[ind, p] = '{} ({}%)'.format(no_agst_peak, pct)

                elif i == 3:
                    no_all_peak = q_all_peaks.count()
                    flow_all_peak = round(no_all_peak / duration_hours, 1)
                    indDf.loc[ind, p] = '{}'.format(flow_all_peak)

                elif i == 4:
                    q_femaleCyclist_peak = q_all_peaks.filter(Person.gender == 'female')
                    no_femCylist_peak = q_femaleCyclist_peak.count()
                    pct = round((no_femCylist_peak / noAll) * 100, 1) if noAll != 0 else 0
                    indDf.loc[ind, p] = '{} ({}%)'.format(no_femCylist_peak, pct)


    elif transport == 'Activity':
        indicators = ['Start time',  # 0
                      'End time',    # 1
                      'Duration'    # 2
                      ]
        q = session.query(Activity.activity) \
                   .filter(Activity.startTime >= start_obs_time)\
                   .filter(Activity.startTime < end_obs_time).distinct()

        activity_dict = {}
        for rec in q.all():
            act_type = rec[0].name
            activity_dict[act_type] = {'count': 0, 'actTotalTime': 0}

        for p in entP_peakHours.keys():

            if entP_peakHours[p] is None:
                continue

            lowerBound = datetime.datetime.combine(start_obs_time.date(), entP_peakHours[p][0])
            upperBound = datetime.datetime.combine(start_obs_time.date(), entP_peakHours[p][1])

            duration = upperBound - lowerBound
            duration_in_s = duration.total_seconds()
            duration_hours = duration_in_s / 3600

            q = session.query(Activity.activity, Activity.startTime, Activity.endTime) \
                .join(GroupBelonging, GroupBelonging.groupIdx == Activity.groupIdx) \
                .join(Person, Person.idx == GroupBelonging.personIdx) \
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

            # q_join_person = q.join(GroupBelonging, GroupBelonging.groupIdx == Activity.groupIdx)\
            #     .join(Person, Person.idx == GroupBelonging.personIdx)
            no_female_act = q.filter(Person.gender == 'female').count()
            no_male_act = q.filter(Person.gender == 'male').count()
            no_chld_act = q.filter(Person.age == 'child').count()
            no_eldry_act = q.filter(Person.age == 'senior').count()

            if p == indDf.columns[0]:
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
                if act_totalTime_min > 0:
                    indDf.loc['Total time of {} (min.)'.format(act), p] = \
                        '{}'.format(act_totalTime_min)# if act_totalTime_min > 0 else 'NA')
                    indDf.loc['Avg. time of {} (min.)'.format(act), p] = \
                      '{}'.format(round(act_totalTime_min / total_acts, 1))# if act_totalTime_min > 0 else 'NA')
                elif act_totalTime_min == 0 and 'Total time of {} (min.)'.format(act) in indDf.index:
                    indDf.loc['Total time of {} (min.)'.format(act), p] = '{}'.format(0)
                    indDf.loc['Avg. time of {} (min.)'.format(act), p] = '{}'.format(0)

                indDf.loc['Rate of {} (act/h)'.format(act), p] = \
                    '{}'.format(round(act_count / duration_hours, 1))




    indDf[indDf.isnull().values] = noDataSign

    # indDf.columns = [indDf.columns[0] + ' (% of all)',
    #                  indDf.columns[1] + ' (% of item)',
    #                  indDf.columns[2] + ' (% of item)',
    #                  indDf.columns[3] + ' (% of item)']
    indDf = indDf.replace(['0 (0.0%)', '0 (0%)'], 0)

    for i in indDf.index:
        for c in indDf.columns:
            parts = str(indDf.loc[i, c]).split(' ')
            if len(parts) > 1:
                if parts[1] == '(100.0%)':
                    indDf.loc[i, c] = '{} ({}%)'.format(parts[0], 100)


    return indDf


def compareIndicators(dbFiles, labels, transports, actionTypes, unitIdxs, directions, interval):

    session1 = connectDatabase(dbFiles[0])
    session2 = connectDatabase(dbFiles[1])
    first_obs_time1, last_obs_time1 = getObsStartEnd(session1)
    first_obs_time2, last_obs_time2 = getObsStartEnd(session2)

    if first_obs_time1.time() >= first_obs_time2.time():
        start_time = first_obs_time1.time()
    else:
        start_time = first_obs_time2.time()

    if last_obs_time1.time() <= last_obs_time2.time():
        end_time = last_obs_time1.time()
    else:
        end_time = last_obs_time2.time()

    indDf1 = generateReport(dbFiles[0], transports[0], actionTypes[0], unitIdxs[0], directions[0],
                            interval, start_time, end_time)
    indDf2 = generateReport(dbFiles[1], transports[1], actionTypes[1], unitIdxs[1], directions[1],
                            interval, start_time, end_time)

    indDf = pd.DataFrame()
    # indDf = indDf1.iloc[0:3, :].copy()

    idx1 = indDf1.index #[3:]
    idx2 = indDf2.index #[3:]

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

    for row in indDf1.index:#[3:]:
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

    # indDf.columns = [indDf.columns[0].split('(')[0][:-1] + ' [% of change]',
    #                  indDf.columns[1].split('(')[0][:-1] + ' [% of change]',
    #                  indDf.columns[2].split('(')[0][:-1] + ' [% of change]',
    #                  indDf.columns[3].split('(')[0][:-1] + ' [% of change]']

    return indDf


def plotTrajectory(trjDBFile, intrinsicCameraMatrix, distortionCoefficients, homographyFile, ax, session):
    objects = storage.loadTrajectoriesFromSqlite(trjDBFile, 'object')
    homography = np.loadtxt(homographyFile, delimiter=' ')
    traj_line = {}
    for traj in objects:
        xy_arr = traj.positions.asArray()
        x = xy_arr[0]
        y = xy_arr[1]
        userType = traj.getUserType()
        line, = ax.plot(x, y, color=userTypeColors[userType], lw=0.5, label=userTypeNames[userType])
        traj_line[str(traj.getNum())] = [traj, line]

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
    ax.tick_params(axis='both', labelsize=5)
    handles, labels = ax.get_legend_handles_labels()
    handle_list = []
    label_list = []
    for i, label in enumerate(labels):
        if not label in label_list:
            handle_list.append(handles[i])
            label_list.append(label)
    ax.legend(handle_list, label_list, loc='upper left', prop={'size': 5})

    return traj_line


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

    for trj in objects:
        userType = trj.getUserType()
        if userType == 0:
            continue

        for line in q_line.all():
            points = np.array([[line.points[0].x, line.points[1].x],
                               [line.points[0].y, line.points[1].y]])
            prj_points = imageToWorldProject(points, intrinsicCameraMatrix, distortionCoefficients, homography)
            p1 = moving.Point(prj_points[0][0], prj_points[1][0])
            p2 = moving.Point(prj_points[0][1], prj_points[1][1])

            instants_list = trj.getInstantsCrossingLane(p1, p2)
            if len(instants_list) > 0:
                secs = int(instants_list[0]/frameRate)
                instant = video_start + datetime.timedelta(seconds=secs)
                speed = round(trj.getVelocityAtInstant(int(instants_list[0])).norm2()*frameRate*3.6, 1)  #km/h
                person = Person()
                if userType == 1 or userType == 7:
                    vehicle = Vehicle(category='car')
                    modes_list.append(Mode(transport='cardriver', person=person, vehicle=vehicle))
                elif userType == 2:
                    modes_list.append(Mode(transport='walking', person=person))
                elif userType == 4 or userType == 3:
                    vehicle = Vehicle(category='bike')
                    modes_list.append(Mode(transport='bike', person=person, vehicle=vehicle))
                elif userType == 5:
                    vehicle = Vehicle(category='bus')
                    modes_list.append(Mode(transport='cardriver', person=person, vehicle=vehicle))
                elif userType == 6:
                    vehicle = Vehicle(category='truck')
                    modes_list.append(Mode(transport='cardriver', person=person, vehicle=vehicle))
                elif userType == 8:
                    vehicle = Vehicle(category='scooter')
                    modes_list.append(Mode(transport='scooter', person=person, vehicle=vehicle))
                elif userType == 9:
                    vehicle = Vehicle(category='skate')
                    modes_list.append(Mode(transport='skating', person=person, vehicle=vehicle))
                linePass_list.append(LineCrossing(line=line, instant=instant, person=person, speed=speed))

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

def creatStreetusers(userType, lines, instants, speeds, groupSize):
    linePass_list = []
    modes_list = []

    persons = []
    for i in range(groupSize):
        persons.append(Person())
    group = Group(persons)

    if userType == 1 or userType == 7:
        vehicle = Vehicle(category='car')
        modes_list = modes_list + [Mode(transport='cardriver', person=p, vehicle=vehicle) for p in group.getPersons()]
    elif userType == 2:
        modes_list = modes_list + [Mode(transport='walking', person=p) for p in group.getPersons()]
    elif userType == 4 or userType == 3:
        vehicle = Vehicle(category='bike')
        modes_list = modes_list + [Mode(transport='bike', person=p, vehicle=vehicle) for p in group.getPersons()]
    elif userType == 5:
        vehicle = Vehicle(category='bus')
        modes_list = modes_list + [Mode(transport='cardriver', person=p, vehicle=vehicle) for p in group.getPersons()]
    elif userType == 6:
        vehicle = Vehicle(category='truck')
        modes_list = modes_list + [Mode(transport='cardriver', person=p, vehicle=vehicle) for p in group.getPersons()]
    elif userType == 8:
        vehicle = Vehicle(category='scooter')
        modes_list = modes_list + [Mode(transport='scooter', person=p, vehicle=vehicle) for p in group.getPersons()]
    elif userType == 9:
        vehicle = Vehicle(category='skate')
        modes_list = modes_list + [Mode(transport='skating', person=p, vehicle=vehicle) for p in group.getPersons()]

    for i in range(len(lines)):
        line = lines[i]
        instant = instants[i]
        speed = speeds[i]
        linePass_list.append(LineCrossing(line=line, instant=instant, group=group, speed=speed))

    return [group] + linePass_list + modes_list

def modeShareCompChart(dbFiles, labels, interval, axs=None):
    inputNo = len(dbFiles)
    sessions = []
    first_obs_times = []
    last_obs_times = []

    for i in range(inputNo):
        session = connectDatabase(dbFiles[i])
        sessions.append(session)

        cls_obs = LineCrossing
        first_obs_time = session.query(func.min(cls_obs.instant)).first()[0]
        last_obs_time = session.query(func.max(cls_obs.instant)).first()[0]

        first_obs_times.append(first_obs_time.time())
        last_obs_times.append(last_obs_time.time())

    bins_start = max(first_obs_times)
    bins_end = min(last_obs_times)

    start = datetime.datetime.combine(datetime.datetime(2000, 1, 1), bins_start)
    end = datetime.datetime.combine(datetime.datetime(2000, 1, 1), bins_end)

    duration = end - start
    duration_in_s = duration.total_seconds()

    bins = calculateBinsEdges(start, end, interval)

    if len(bins) < 3:
        err = 'The observation duration is not enough for the selected interval!'
        return err

    times = [b.time() for b in bins]

    if axs is None:
        fig = plt.figure()
        ax = fig.subplots(2, 2, sharex=True, sharey='row')

    ax = [axs[0,0], axs[0,1], axs[1,0], axs[1,1]]
    # X = np.arange(len(times) - 1)

    # before = {'cardriver':[], 'walking':[], 'bike':[], 'scooter':[]}
    # after = {'cardriver':[], 'walking':[], 'bike':[], 'scooter':[]}

    users_dics = []
    for _ in range(inputNo):
        users_dics.append({'cardriver': [], 'walking': [], 'cycling': [], 'other': []})

    for i in range(inputNo):
        date1 = getObsStartEnd(sessions[i])[0].date()
        times1 = [datetime.datetime.combine(date1, t) for t in times]
        for j in range(len(times) - 1):
            startTime1 = times1[j]
            endTime1 = times1[j + 1]
            labels1, sizes1 = getLabelSizePie('all types', 'transport', startTime1, endTime1, sessions[i])
            for mode in ['cardriver', 'walking', 'cycling', 'other']:
                if mode in labels1:
                    users_dics[i][mode].append(sizes1[labels1.index(mode)])
                else:
                    users_dics[i][mode].append(0)

    date = datetime.date(2000, 1, 1)
    datetime1 = datetime.datetime.combine(date, times[0])
    datetime2 = datetime.datetime.combine(date, times[1])
    interval_dt = datetime2 - datetime1
    middlePoint = [(datetime.datetime.combine(date, times[i]) + interval_dt / 2) for i in range(len(times) - 1)]

    # ticks = middlePoint #[t.strftime('%H:%M') for t in middlePoint]
    locator = mdates.AutoDateLocator()
    titles = ['Car', 'Pedestrian', 'Bike', 'Other']
    for i, mode in enumerate(['cardriver', 'walking', 'cycling', 'other']):
        for j in range(inputNo):
            ax[i].plot(middlePoint, users_dics[j][mode], color=plotColors[j])  # , width=w)
        # ax[i].set_xticks([i for i in range(len(times) - 1)])
        # ax[i].set_xticklabels(ticks, rotation=90)

        ax[i].xaxis.set_major_locator(locator)
        ax[i].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax[i].xaxis.set_minor_locator(mdates.MinuteLocator(byminute=30))

        ax[i].tick_params(axis='both', labelsize=7)
        ax[i].tick_params(axis='x', rotation=90)
        ax[i].grid(True, 'major', 'both', ls='--', lw=.5, c='k', alpha=.3)
        ax[i].set_title(titles[i], fontsize=7)
        if i > 1:
            ax[i].set_xlabel('Time', fontsize=7)
        if i == 0 or i == 2:
            ax[i].set_ylabel('No. of street users', fontsize=7)
        ax[i].yaxis.set_major_locator(MaxNLocator(integer=True))
        ax[i].legend(labels, loc='upper right', fontsize=5)

        ax[i].text(0.03, 0.92, str('StudioProject'),
                   fontsize=5, color='gray',
                   ha='left', va='bottom',
                   transform=ax[i].transAxes,
                   weight="bold", alpha=.5)
    plt.suptitle('Comparison of transportation mode share', fontsize=8)

    # date1 = getObsStartEnd(sessions[0])[0].date()
    # date2 = getObsStartEnd(sessions[1])[0].date()
    # times1 = [datetime.datetime.combine(date1, t) for t in times]
    # times2 = [datetime.datetime.combine(date2, t) for t in times]
    # for t in range(len(times) - 1):
    #     startTime1 = times1[t]
    #     endTime1 = times1[t + 1]
    #     startTime2 = times2[t]
    #     endTime2 = times2[t + 1]
    #     labels1, sizes1 = getLabelSizePie('all types', 'transport', startTime1, endTime1, sessions[0])
    #     labels2, sizes2 = getLabelSizePie('all types', 'transport', startTime2, endTime2, sessions[1])
    #     for mode in ['cardriver', 'walking', 'bike', 'scooter']:
    #         if mode in labels1:
    #             before[mode].append(sizes1[labels1.index(mode)])
    #         else:
    #             before[mode].append(0)
    #
    #         if mode in labels2:
    #             after[mode].append(sizes2[labels2.index(mode)])
    #         else:
    #             after[mode].append(0)

    # date = datetime.date(2000, 1, 1)
    # datetime1 = datetime.datetime.combine(date, times[0])
    # datetime2 = datetime.datetime.combine(date, times[1])
    # interval = datetime2 - datetime1
    # middlePoint = [(datetime.datetime.combine(date, times[i]) + interval / 2) for i in range(len(times) - 1)]
    # # ticks = middlePoint #[t.strftime('%H:%M') for t in middlePoint]
    # locator = mdates.AutoDateLocator()
    # titles = ['Car', 'Pedestrian', 'Bike', 'Scooter']
    # for i, mode in enumerate(['cardriver', 'walking', 'bike', 'scooter']):
    #     ax[i].plot(middlePoint, before[mode], color='deepskyblue')#, width=w)
    #     ax[i].plot(middlePoint, after[mode], color='salmon')#, width=w)
    #     # ax[i].set_xticks([i for i in range(len(times) - 1)])
    #     # ax[i].set_xticklabels(ticks, rotation=90)
    #
    #     ax[i].xaxis.set_major_locator(locator)
    #     ax[i].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    #     ax[i].xaxis.set_minor_locator(mdates.MinuteLocator(byminute=30))
    #
    #     ax[i].tick_params(axis='both', labelsize=7)
    #     ax[i].tick_params(axis='x', rotation=90)
    #     ax[i].grid(True, 'major', 'both', ls='--', lw=.5, c='k', alpha=.3)
    #     ax[i].set_title(titles[i], fontsize=7)
    #     if i > 1:
    #         ax[i].set_xlabel('Time', fontsize=7)
    #     if i == 0 or i == 2:
    #         ax[i].set_ylabel('No. of street users', fontsize=7)
    #     ax[i].yaxis.set_major_locator(MaxNLocator(integer=True))
    #     ax[i].legend(['before', 'after'], loc='upper right', fontsize=5)
    #
    #     ax[i].text(0.03, 0.92, str('StudioProject'),
    #             fontsize=5, color='gray',
    #             ha='left', va='bottom',
    #             transform=ax[i].transAxes,
    #             weight="bold", alpha=.5)
    # plt.suptitle('Comparison of transportation mode share', fontsize=8)
    #
    # # locator = mdates.AutoDateLocator()
    # # ax[0].xaxis.set_major_locator(locator)
    # # ax[0].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    # # ax[0].xaxis.set_minor_locator(mdates.MinuteLocator(byminute=30))

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
        q = session.query(field_, func.count(func.distinct(Mode.idx))) \
            .join(GroupBelonging, GroupBelonging.personIdx == Mode.personIdx) \
            .join(LineCrossing, LineCrossing.groupIdx == GroupBelonging.groupIdx) \
            .filter(LineCrossing.instant >= startTime) \
            .filter(LineCrossing.instant < endTime) \
            .group_by(field_)
    elif transport == 'walking':
        field_ = getattr(Person, fieldName)
        q = session.query(field_, func.count(field_)) \
            .join(Mode, Person.idx == Mode.personIdx) \
            .filter(Mode.transport == transport) \
            .join(GroupBelonging, GroupBelonging.personIdx == Person.idx) \
            .join(LineCrossing, LineCrossing.groupIdx == GroupBelonging.groupIdx) \
            .filter(LineCrossing.instant >= startTime) \
            .filter(LineCrossing.instant < endTime) \
            .group_by(field_)
    elif transport == 'cardriver':
        field_ = getattr(Vehicle, fieldName)
        q = session.query(field_, func.count(field_)) \
            .join(Mode, Vehicle.idx == Mode.vehicleIdx) \
            .filter(Mode.transport == transport) \
            .join(GroupBelonging, GroupBelonging.personIdx == Mode.personIdx) \
            .join(LineCrossing, LineCrossing.groupIdx == GroupBelonging.groupIdx) \
            .filter(LineCrossing.instant >= startTime) \
            .filter(LineCrossing.instant < endTime) \
            .group_by(field_)

    labels = [i[0].name if not isinstance(i[0], str) else i[0] for i in q.all()]
    sizes = [int(i[1]) for i in q.all()]

    return labels, sizes


def getPeakHours(start_obs_time, end_obs_time, interval):
    # morningPeakStart = morningPeakStart,
    # morningPeakEnd = morningPeakEnd,
    # eveningPeakStart = eveningPeakStart,
    # eveningPeakEnd = eveningPeakEnd):

    peakHours = {}
    key_config = '{} - {}'
    key_format = '%H:%M'

    bins_start = ceil_time(start_obs_time, interval)
    bins_end = ceil_time(end_obs_time, interval) - datetime.timedelta(minutes=interval)

    key = key_config.format(start_obs_time.strftime(key_format), end_obs_time.strftime(key_format))
    peakHours[key] = [start_obs_time.time(), end_obs_time.time()]

    key = key_config.format(start_obs_time.strftime(key_format), bins_start.strftime(key_format))
    peakHours[key] = [start_obs_time.time(), bins_start.time()]

    bin_edge = bins_start
    while bin_edge != bins_end:
        bin_edge2 = bin_edge + datetime.timedelta(minutes=interval)
        key = key_config.format(bin_edge.strftime(key_format), bin_edge2.strftime(key_format))
        peakHours[key] = [bin_edge.time(), bin_edge2.time()]
        bin_edge = bin_edge2

    key = key_config.format(bins_end.strftime(key_format), end_obs_time.strftime(key_format))
    peakHours[key] = [bins_end.time(), end_obs_time.time()]

    return peakHours

    # peakHours = {}
    # if start_obs_time.time() < morningPeakStart:
    #     peakHours['Morning peak'] = [morningPeakStart, morningPeakEnd]
    #     peakHours['Off-peak'] = [morningPeakEnd, eveningPeakStart]
    #     peakHours['Evening peak'] = [eveningPeakStart, eveningPeakEnd]
    #
    # elif morningPeakStart < start_obs_time.time() < morningPeakEnd:
    #     peakHours['Morning peak'] = [start_obs_time.time(), morningPeakEnd]
    #     peakHours['Off-peak'] = [morningPeakEnd, eveningPeakStart]
    #     peakHours['Evening peak'] = [eveningPeakStart, eveningPeakEnd]
    #
    # elif morningPeakEnd < start_obs_time.time() < eveningPeakStart:
    #     peakHours['Morning peak'] = None
    #     peakHours['Off-peak'] = [start_obs_time.time(), eveningPeakStart]
    #     peakHours['Evening peak'] = [eveningPeakStart, eveningPeakEnd]
    #
    # elif eveningPeakStart < start_obs_time.time() < eveningPeakEnd:
    #     peakHours['Morning peak'] = None
    #     peakHours['Off-peak'] = None
    #     peakHours['Evening peak'] = [start_obs_time.time(), eveningPeakEnd]
    #
    # if eveningPeakStart < end_obs_time.time() < eveningPeakEnd:
    #     peakHours['Evening peak'][1] = end_obs_time.time()
    #
    # elif morningPeakEnd < end_obs_time.time() < eveningPeakStart:
    #     peakHours['Evening peak'] = None
    #     peakHours['Off-peak'][1] = end_obs_time.time()
    #
    # elif morningPeakStart < end_obs_time.time() < morningPeakEnd:
    #     peakHours['Evening peak'] = None
    #     peakHours['Off-peak'] = None
    #     peakHours['Morning peak'][1] = end_obs_time.time()
    #
    # return peakHours

def ceil_time(time, m):
    if time.second == 0 and time.microsecond == 0 and time.minute % m == 0:
        return time
    minutes_by_m = time.minute // m
    # get the difference in times
    diff = (minutes_by_m + 1) * m - time.minute
    time = (time + datetime.timedelta(minutes=diff)).replace(second=0, microsecond=0)
    return time

def getObsStartEnd(session):
    first_linePass_time = session.query(func.min(LineCrossing.instant)).first()[0]
    last_linePass_time = session.query(func.max(LineCrossing.instant)).first()[0]

    first_zonePass_time = session.query(func.min(ZoneCrossing.instant)).first()[0]
    last_zonePass_time = session.query(func.max(ZoneCrossing.instant)).first()[0]

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

def calculateBinsEdges(start, end, interval=None):
    if start.date() != end.date():
        end = datetime.datetime.combine(start.date(), end.time())

    if cfg != [] and interval == None:
        interval = int(config_object['BINS']['binsminutes'])
    elif cfg == [] and interval == None:
        interval = 10

    period_minutes = (end - start).seconds / 60
    no_intervals = np.floor(period_minutes / interval)
    if no_intervals == 0:
        return []
    remainder = period_minutes % interval
    start = start + datetime.timedelta(minutes=round(remainder/2))

    # m2 = np.ceil((start.minute + start.second / 60) / interval)
    # if m2 == 60 / interval:
    #     start = datetime.datetime.combine(start.date(), datetime.time(start.hour + 1))
    # else:
    #     start = datetime.datetime.combine(start.date(),
    #                                       datetime.time(start.hour, int(m2 * interval)))

    bins = pd.date_range(start=start, end=end, freq=pd.offsets.Minute(interval))
    bins = [b.to_pydatetime() for b in bins]
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
