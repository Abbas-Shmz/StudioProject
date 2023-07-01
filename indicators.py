#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

@author: Abbas
"""
from scipy.interpolate import make_interp_spline
from scipy.stats import gaussian_kde
import numpy as np
from pathlib import Path
import datetime

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator
import matplotlib.colors as mcolors

import plotly.graph_objects as go
import plotly.io as pio

from random import randint
from sqlalchemy import func, or_, and_
from sqlalchemy.inspection import inspect
import sqlite3, os, subprocess, json
import ast
from configparser import ConfigParser

from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
from hachoir.core import config as HachoirConfig

import pandas as pd

from PyPDF2 import PdfFileMerger
from fpdf import FPDF

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
plotColors = ['deepskyblue', 'salmon', 'gold', 'forestgreen', 'violet', 'cadetblue', 'saddlebrown', 'yellowgreen',
              'chocolate', 'navy', 'purple', 'aqua', 'blue', 'darkkhaki', 'green', 'black', 'cyan', 'brown', 'gray', 'olive']

color_dict = {'walking':'mediumaquamarine', 'driving':'lightsalmon', 'cycling':'lightskyblue',
              'motorcycle':'darkred', 'car':'orange', 'bus':'yellow', 'truck':'silver', 'other':'burlywood',

              'adult':'goldenrod', 'child':'powderblue', 'young_adult':'lightsteelblue',
              'teen':'lightcoral', 'senior':'plum', 'toddler':'mistyrose', 'infant':'lightyellow',

              'male':'thistle', 'female':'lightskyblue',

              'unknown':'silver',

              'strolling':'palegoldenrod', 'jogging':'paleturquoise', 'shopping':'cornflowerblue',
              'sitting':'rosybrown', 'talking':'lightsteelblue', 'resting':'mintcream',
              'eating':'plum', 'playing':'deepskyblue', 'doing_exercise':'orange', 'smoking':'yellow',
              'using_cellphone':'powderblue', 'observing':'lightsteelblue',
              'reading_writing':'violet', 'performing':'yellow', 'selling':'lightsteelblue',
              'playing_with_pets':'red', 'taking_pet_for_walk':'blue'}

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
def tempDistHist(dbFiles, labels, transports, actionTypes, unitIdxs, directions=None,
                 ax=None, interval=20, plotType='Line plot', alpha=1, colors=plotColors, siteName=None,
                 drawMean=True, drawStd=0, smooth=False,
                 titleSize=8, xLabelSize=8, yLabelSize=8, xTickSize=8, yTickSize=7, legendFontSize=6):

    inputNo = len(dbFiles)
    first_obs_times = []
    last_obs_times = []

    for i in range(inputNo):
        session = connectDatabase(dbFiles[i])
        fobst, lobst = getObsStartEnd(session)
        first_obs_times.append(fobst)
        last_obs_times.append(lobst)

    obs_start_time = min(first_obs_times).time()
    obs_end_time = max(last_obs_times).time()

    query_list = getQueryList(dbFiles, transports, actionTypes, unitIdxs)
    if isinstance(query_list, str):
        return query_list

    time_lists = getTimeLists(query_list, actionTypes)

    if all([i == [] for i in time_lists]):
        return 'No observation!'

    for time_list in time_lists:
        if time_list == []:
            continue
        for i, time_ticks in enumerate(time_list):
            time_list[i] = datetime.datetime(2000, 1, 1, time_ticks.hour, time_ticks.minute, time_ticks.second)


    if ax == None:
        fig = plt.figure(tight_layout=True)  # figsize=(5, 5), dpi=200, tight_layout=True)
        ax = fig.add_subplot(111)  # plt.subplots(1, 1)

    to_timestamp = np.vectorize(lambda x: x.timestamp())

    if plotType == 'Line plot':
        bins_start = obs_start_time
        bins_end = obs_end_time

        start = datetime.datetime.combine(datetime.datetime(2000, 1, 1), bins_start)
        end = datetime.datetime.combine(datetime.datetime(2000, 1, 1), bins_end)

        bins = calculateBinsEdges(start, end, interval)

        if len(bins) < 3:
            err = 'The observation duration is not enough for the selected interval!'
            return err

        for l, time_list in enumerate(time_lists):
            if time_list == []:
                continue

            time_stamps = to_timestamp(time_list)

            bins_stamps = to_timestamp(bins)
            bins_stamps.sort()

            min_time_stamps = min(time_stamps)
            max_time_stamps = max(time_stamps)

            bins_idx_remove = []
            for i in range(len(bins_stamps) - 1):
                if bins_stamps[i] < min_time_stamps and bins_stamps[i + 1] > min_time_stamps:
                    bins_idx_remove.append(i)
                elif bins_stamps[i] < max_time_stamps and bins_stamps[i + 1] > max_time_stamps:
                    bins_idx_remove.append(i + 1)
                elif bins_stamps[i] < min_time_stamps and bins_stamps[i + 1] < min_time_stamps:
                    bins_idx_remove.append(i)
                    bins_idx_remove.append(i + 1)
                elif bins_stamps[i] > max_time_stamps and bins_stamps[i + 1] > max_time_stamps:
                    bins_idx_remove.append(i)
                    bins_idx_remove.append(i + 1)
                else:
                    continue

            if len(bins_idx_remove) > 0:
                bins_stamps = np.delete(bins_stamps, bins_idx_remove)

            if len(bins_stamps) < 3:
                err = 'The observation duration is not enough for the selected interval!'
                return err

            time_ticks = []
            for i in range(len(bins_stamps) - 1):
                mid_point = bins_stamps[i] + (bins_stamps[i + 1] - bins_stamps[i]) / 2
                time_ticks.append(datetime.datetime.fromtimestamp(mid_point))

            hist, bin_edges = np.histogram(time_stamps, bins=bins_stamps)
            if len(hist) == 0:
                err = 'There is no observation for the selected arguments!'
                return err

            # ax.plot(time_ticks, hist, label=labels[l])
            #------------------------
            if drawStd > 0:
                ax.axhspan(np.mean(hist) - np.std(hist), np.mean(hist) + np.std(hist),
                           label=f'Std. of {labels[l]}', alpha=0.1, color=plotColors[l])

            if not smooth:
                ax.plot(time_ticks, hist, label=labels[l], color=plotColors[l])
            else:
                date_np = np.array(time_ticks)
                date_num = mdates.date2num(date_np)
                date_num_smooth = np.linspace(date_num.min(), date_num.max(), len(time_ticks)*10)
                spl = make_interp_spline(date_num, hist, k=2)
                value_np_smooth = spl(date_num_smooth)
                ax.plot(mdates.num2date(date_num_smooth), value_np_smooth, label=labels[l], color=plotColors[l])
            #------------------------
            if drawMean:
                ax.axhline(y=np.mean(hist), color=plotColors[l], linestyle='--',
                          lw=1, label= 'Avg. of {}'.format(labels[l]))
            # ------------------------

    elif plotType == 'Scatter plot':
        if inputNo != 2:
            return 'The scatter plot is possible for only two datasets!'

        bins_start = max(first_obs_times).time()
        bins_end = min(last_obs_times).time()

        start = datetime.datetime.combine(datetime.datetime(2000, 1, 1), bins_start)
        end = datetime.datetime.combine(datetime.datetime(2000, 1, 1), bins_end)

        bins = calculateBinsEdges(start, end, interval)

        if len(bins) < 3:
            err = 'The observation duration is not enough for the selected interval!'
            return err

        bins_stamps = to_timestamp(bins)
        time_ticks = []
        for i in range(len(bins) - 1):
            mid_point = bins_stamps[i] + (bins_stamps[i + 1] - bins_stamps[i]) / 2
            time_ticks.append(datetime.datetime.fromtimestamp(mid_point))

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

        # corrcoef = round(np.corrcoef(hist1, hist2)[0, 1], 2)
        ax.text(0.85, 0.85, f'$\\frac{{{labels[1]}}}{{{labels[0]}}} = {round(m, 2)}$',
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

        # if inputNo == 1:
        #     xLabel = 'Time ({})'.format(bins_start.strftime('%A, %b %d, %Y'))
        # else:
        xLabel = 'Time of day'

        # ax.set_xticklabels(fontsize = 6, rotation = 45)#'vertical')
        ax.tick_params(axis='x', labelsize=xTickSize, rotation=0)
        ax.tick_params(axis='y', labelsize=yTickSize)
        ax.set_xlabel(xLabel, fontsize=xLabelSize)

        tm = getUserTitle(transports[0])

        if yLabelSize > 0:
            ax.set_ylabel('No. of {}s'.format(tm), fontsize=yLabelSize)

        ax.yaxis.set_major_locator(MaxNLocator(integer=True))

        if unitIdxs[0].split('_')[0] == 'all':
            title = f'No. of {tm}s every {interval} min.'
        else:
            title = f'No. of {tm}s {actionTypes[0]} #{unitIdxs[0]} every {interval} min.'
        if siteName != None:
            title = f'{title} in {siteName}'
        ax.set_title(title, fontsize=titleSize)

        if not all(l == '' for l in labels):
            ax.legend(loc='best', fontsize=legendFontSize)

    elif plotType == 'Scatter plot':

        # max_val = max(max(hist1), max(hist2))
        # ax.set_xlim(0, max_val + 10)
        # ax.set_ylim(0, max_val + 10)

        ax.tick_params(axis='both', labelsize=xTickSize)

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

        ax.set_xlabel(f'No. of {tm1}s ({labels[0]})', fontsize=xLabelSize)
        ax.set_ylabel(f'No. of {tm2}s ({labels[1]})', fontsize=yLabelSize)
        ax.set_title(f'Scatter plot of {tm1}s {actionTypes[0]} #{unitIdxs[0]}',
                     fontsize=titleSize)
        # ax.axis('equal')

    ax.grid(True, 'major', 'both', ls='--', lw=.5, c='k', alpha=.3)

    watermark(ax)

        # # plt.show()

# ==============================================================
def getQueryList(dbFiles, transports, actionTypes, unitIdxs, start_time=None, end_time=None):

    inputNo = len(dbFiles)
    sessions = []

    for i in range(inputNo):
        session = connectDatabase(dbFiles[i])
        sessions.append(session)

    q = [None]*inputNo
    for i in range(inputNo):
        if 'line' in actionTypes[i].split('_'):
            q[i] = sessions[i].query(LineCrossing.groupIdx, func.min(LineCrossing.instant), func.avg(LineCrossing.speed), Person.gender, Mode.transport, Person.age)\
                .join(Line, Line.idx == LineCrossing.lineIdx)\
                .join(GroupBelonging, GroupBelonging.groupIdx == LineCrossing.groupIdx)

            if unitIdxs[i] != 'all_lines':
                q[i] = q[i].filter(LineCrossing.lineIdx == unitIdxs[i])

            if 'RL' in actionTypes[i].split('_'):
                q[i] = q[i].filter(LineCrossing.rightToLeft == True)
            elif 'LR' in actionTypes[i].split('_'):
                q[i] = q[i].filter(LineCrossing.rightToLeft == False)

            if start_time != None and end_time != None:
                q[i] = q[i].filter(LineCrossing.instant >= start_time)\
                    .filter(LineCrossing.instant < end_time)

        elif 'zone' in actionTypes[i].split('_'):
            q[i] = sessions[i].query(ZoneCrossing.groupIdx, func.min(ZoneCrossing.instant), func.avg(ZoneCrossing.speed), Person.gender, Mode.transport, Person.age) \
                   .join(Zone, Zone.idx == ZoneCrossing.zoneIdx) \
                   .join(GroupBelonging, GroupBelonging.groupIdx == ZoneCrossing.groupIdx)

            if unitIdxs[i] != 'all_zones':
                q[i] = q[i].filter(ZoneCrossing.zoneIdx == unitIdxs[i])

            if 'entering' in actionTypes[i].split('_'):
                q[i] = q[i].filter(ZoneCrossing.entering == True)
            elif 'exiting' in actionTypes[i].split('_'):
                q[i] = q[i].filter(ZoneCrossing.entering == False)

            if start_time != None and end_time != None:
                q[i] = q[i].filter(ZoneCrossing.instant >= start_time)\
                    .filter(ZoneCrossing.instant < end_time)

        elif  actionTypes[i] == 'all_crossings' and unitIdxs[i] == 'all_units':
            q[i] = sessions[i].query(Group.idx, func.min(LineCrossing.instant), func.min(ZoneCrossing.instant), func.avg(LineCrossing.speed), func.avg(ZoneCrossing.speed), Person.gender, Mode.transport, Person.age) \
                .join(LineCrossing, LineCrossing.groupIdx == Group.idx, isouter=True) \
                .join(ZoneCrossing, ZoneCrossing.groupIdx == Group.idx, isouter=True) \
                .join(GroupBelonging, GroupBelonging.groupIdx == Group.idx, isouter=True) \
                .filter(or_(LineCrossing.instant != None, ZoneCrossing.instant != None))\
                .join(Line, Line.idx == LineCrossing.lineIdx, isouter=True)\
                .join(Zone, Zone.idx == ZoneCrossing.zoneIdx, isouter=True)

            if start_time != None and end_time != None:
                q[i] = q[i].filter(or_(and_(LineCrossing.instant >= start_time, LineCrossing.instant < end_time),
                                       and_(ZoneCrossing.instant >= start_time, ZoneCrossing.instant < end_time)))


        else:
            return 'ERROR: incompatible arguments!'

        q[i] = q[i].join(Person, Person.idx == GroupBelonging.personIdx)\
               .join(Mode, Mode.personIdx == Person.idx)

        if transports[i] != 'all_modes':
            q[i] = q[i].filter(Mode.transport == transports[i])

            if transports[i] != 'walking':
                q[i] = q[i].join(Vehicle, Vehicle.idx == Mode.vehicleIdx)

            # if transports[i] == 'cardriver':
            #     q = q.filter(Zone.type == 'roadbed')
                # .filter(Vehicle.category == 'car')

        q[i] = q[i].group_by(Person.idx)

    return q


# ================================================================
def getTimeLists(query_list, actionTypes):
    time_lists = []
    for i, q in enumerate(query_list):
        if q.all() == []:
            time_list = []

        if actionTypes[i] == 'all_crossings':
            time_list = [r[1] for r in q.all() if not r[1] is None] + \
                        [r[2] for r in q.all() if not r[2] is None]
        else:
            time_list = [r[1] for r in q.all()]

        time_lists.append(time_list)

    return time_lists

# ================================================================
def zonePassCheckup(dbFile, outputLog=None, threshold = 120, activities = []):
    session = connectDatabase(dbFile)

    q_enter = session.query(ZoneCrossing.groupIdx, ZoneCrossing.instant).filter(ZoneCrossing.entering == True)
    q_exit = session.query(ZoneCrossing.groupIdx, ZoneCrossing.instant).filter(ZoneCrossing.entering == False)

    enters = {k: v for k, v in q_enter.all()}
    exits = {k: v for k, v in q_exit.all()}

    without_exit = []
    without_enter = []
    incorrect_instant = []
    dwelling_indices = []

    for idx in enters.keys():
        if idx in exits.keys():
            if exits[idx] > enters[idx]:
                dwell_time = (exits[idx] - enters[idx]).total_seconds()
                if dwell_time > threshold:
                    dwelling_indices.append([idx, enters[idx], exits[idx]])
            else:
                incorrect_instant.append(idx)
        else:
            without_exit.append(idx)

    for idx in exits.keys():
        if not idx in enters.keys():
            without_enter.append(idx)

    print('dwelling_indices : ', [d[0] for d in dwelling_indices])
    print('without_exit', without_exit)
    print('without_enter', without_enter)
    print('incorrect_instant', incorrect_instant)

    if activities != []:
        for idx, start, end in dwelling_indices:
            grp = session.query(Group).filter(Group.idx == idx).first()
            for actv in activities:
                act = Activity(activity=actv, startTime=start, endTime=end, zone=None, group=grp)
                session.add(act)

        session.flush()
        session.commit()





# ==============================================================
def transportModePDF(dbFiles, labels, transports, actionTypes, unitIdxs, directions=None,
                 ax=None, siteName=None, alpha=1, colors=plotColors,
                     titleSize=8, xLabelSize=8, yLabelSize=8, xTickSize=8, yTickSize=7, legendFontSize=6):
    # TODO: Empirical peak hour
    inputNo = len(dbFiles)

    query_list = getQueryList(dbFiles, transports, actionTypes, unitIdxs)
    if isinstance(query_list, str):
        return query_list

    time_lists = getTimeLists(query_list, actionTypes)

    if all(tl == [] for tl in time_lists):
        return 'No observation!'

    for time_list in time_lists:
        if time_list == []:
            continue
        for i, time_ticks in enumerate(time_list):
            time_list[i] = datetime.datetime(2000, 1, 1, time_ticks.hour, time_ticks.minute, time_ticks.second)

    if ax == None:
        fig = plt.figure(tight_layout=True)  # figsize=(5, 5), dpi=200, tight_layout=True)
        ax = fig.add_subplot(111)  # plt.subplots(1, 1)

    for i, time_list in enumerate(time_lists):
        if time_list == []:
            continue
        date_np = np.array(time_list)
        date_num = mdates.date2num(date_np)

        density = gaussian_kde(date_num)
        x = np.linspace(date_num.min(), date_num.max(), 100)
        y = density(x)
        ax.plot(mdates.num2date(x), y, label=labels[i], color=colors[i])

    # locator = mdates.AutoDateLocator()
    # ax.xaxis.set_major_locator(locator)

    ax.xaxis.set_major_locator(mdates.HourLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

    ax.xaxis.set_minor_locator(mdates.MinuteLocator(byminute=30))

    xLabel = 'Time of day'

    ax.tick_params(axis='x', labelsize=xTickSize, rotation=0)

    # ax.tick_params(axis='y', labelsize=yTickSize)
    ax.tick_params(labelleft = False)

    ax.set_xlabel(xLabel, fontsize=xLabelSize)

    tm = transports[0]
    if len(transports) > 1 and transports[0] != transports[1]:
        tm = 'street user'
    else:
        tm = getUserTitle(transports[0])

    if yLabelSize > 0:
        ax.set_ylabel(f'Probability density', fontsize=yLabelSize)
    # ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    if unitIdxs[0].split('_')[0] == 'all':
        title = f'PDF of all observed {tm}s'
    else:
        title = f'PDF of {tm}s {actionTypes[0]} #{unitIdxs[0]}'
    if siteName != None:
        title = f'{title} in {siteName}'
    ax.set_title(title, fontsize=titleSize)
    if not all(l == '' for l in labels):
        ax.legend(loc='best', fontsize=legendFontSize)


    ax.grid(True, 'major', 'both', ls='--', lw=.5, c='k', alpha=.3)

    watermark(ax)


# ==============================================================
def stackedHistTransport(dbFiles, labels, transports, actionTypes, unitIdxs, directions, attr,
                         ax=None, interval=20, alpha=1, colors=color_dict, siteName=None, textRotation=90,
                         titleSize=8, xLabelSize=7, yLabelSize=7, xTickSize=4, yTickSize=6, legendFontSize=6):
    inputNo = len(dbFiles)
    sessions = []
    first_obs_times = []
    last_obs_times = []

    for i in range(inputNo):
        session = connectDatabase(dbFiles[i])
        sessions.append(session)
        fobst, lobst = getObsStartEnd(session)
        first_obs_times.append(fobst)
        last_obs_times.append(lobst)

    start_obs_time = max(first_obs_times).time()
    end_obs_time = min(last_obs_times).time()

    bins_start = datetime.datetime.combine(datetime.datetime(2000, 1, 1), start_obs_time)
    bins_end = datetime.datetime.combine(datetime.datetime(2000, 1, 1), end_obs_time)

    start = ceil_time(bins_start, interval)
    end = ceil_time(bins_end, interval) - datetime.timedelta(minutes=interval)

    bin_edges = calculateBinsEdges(start, end, interval)
    # bin_edges.insert(0, bins_start)
    # bin_edges.insert(-1, bins_end)

    if len(bin_edges) < 3:
        err = 'The observation duration is not enough for the selected interval!'
        return err

    times = [b.time() for b in bin_edges]

    bins = []
    for i in range(inputNo):
        date1 = first_obs_times[i].date()
        bins.append([datetime.datetime.combine(date1, t) for t in times])

    if ax == None:
        fig = plt.figure(tight_layout=True)
        ax = fig.add_subplot(111)

    bins_num = len(bins[i]) - 1
    ind = np.arange(bins_num)
    width = 0.5 / inputNo

    query_list = getQueryList(dbFiles, transports, actionTypes, unitIdxs)
    if isinstance(query_list, str):
        return query_list

    for i, q in enumerate(query_list):
        x = (ind - 0.25 + width / 2) + (width * i)
        y_offset = np.array([0] * bins_num)

        if transports[i] in ['walking', 'cycling'] and attr in ['age', 'gender']:
            field_ = getattr(Person, attr)
        elif transports[i] == 'cardriver' and attr in ['category']:
            field_ = getattr(Vehicle, attr)
        else:
            return 'The attribute does not match with the transport mode!'

        enum_list = field_.type.enums

        for val in enum_list:
            q_val = q.filter(field_ == val)

            time_list = getTimeLists([q_val], [actionTypes[i]])[0] #[i[0] for i in q_val.all()]
            if time_list != []:
                hist, _ = np.histogram(time_list, bins=bins[i])
                ax.bar(x, hist, color=colors[val], bottom=y_offset,
                        width=width, label=val, edgecolor='grey', lw=0.5)

                y_offset = y_offset + hist

        for k, t in enumerate(x):
            ax.text(t, y_offset[k] + 0.1, labels[i], ha='center', va='bottom', rotation=textRotation,
                    fontsize=5)


    # ax.set_xticklabels(fontsize = 6, rotation = 45)#'vertical')
    xticks = []
    for t in range(bins_num):
        xticks.append('{}-{}'.format(bins[0][t].strftime('%H:%M'), bins[0][t + 1].strftime('%H:%M')))

    ax.set_ylim((-0.03, int(ax.get_ylim()[1]) + 1))

    tm = getUserTitle(transports[0])

    tick_rotation = 0
    if bins_num >= 20:
        tick_rotation = 45

    ax.tick_params(axis='x', labelsize=xTickSize, rotation=tick_rotation)
    ax.tick_params(axis='y', labelsize=yTickSize)
    ax.set_xlabel('Time of day', fontsize=xLabelSize)
    ax.set_ylabel(f'No. of {tm}s', fontsize=yLabelSize)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xticks(ind, xticks)
    title = f'No. of {tm}s by {attr} every {interval} min.'
    if siteName != None:
        title = f'{title} in {siteName}'
    ax.set_title(title, fontsize=titleSize)
    ax.grid(True, 'major', 'y', ls='--', lw=.5, c='k', alpha=.3)
    # ax.legend(loc="upper right", fontsize=5)

    handles, labels = ax.get_legend_handles_labels()
    handle_list = []
    label_list = []
    for i, label in enumerate(labels):
        if not label in label_list:
            handle_list.append(handles[i])
            label_list.append(label)
    ax.legend(handle_list, label_list, loc='best', prop={'size': legendFontSize})


    watermark(ax)


# ==============================================================
def getUserTitle(transport):
    ut = transport
    if transport == 'cardriver':
        ut = 'car'
    elif transport == 'walking':
        ut = 'pedestrian'
    elif transport == 'cycling':
        ut = 'cyclist'
    elif transport == 'all_modes':
        ut = 'all street user'
    return ut



# ==============================================================
def sitesBAtransport(dbFileList, siteNames, transport, directions='both', BAlabels=['Before', 'After'],
                      actionType='all_crossings', unitIdxs='all_units', ax=None, colors=plotColors,
                     titleSize=8, xLabelSize=7, yLabelSize=7, xTickSize=6, yTickSize=6, legendFontSize=5):
    sitesNo = len(dbFileList)
    sites_sessions = []
    obs_durations = []

    for site_dbFiles in dbFileList:
        session_before = connectDatabase(site_dbFiles[0])
        session_after = connectDatabase(site_dbFiles[1])
        sites_sessions.append([session_before, session_after])
        # if 'line' in actionType.split(' '):
        #     cls_obs = LineCrossing
        # elif 'zone' in actionType.split(' '):
        #     cls_obs = ZoneCrossing

        first_obs_before, last_obs_before = getObsStartEnd(session_before)
        first_obs_after, last_obs_after = getObsStartEnd(session_after)

        # first_obs_before = session_before.query(func.min(cls_obs.instant)).first()[0]
        # last_obs_before = session_before.query(func.max(cls_obs.instant)).first()[0]
        #
        # first_obs_after = session_after.query(func.min(cls_obs.instant)).first()[0]
        # last_obs_after = session_after.query(func.max(cls_obs.instant)).first()[0]

        duration_before = last_obs_before - first_obs_before
        duration_before_in_s = duration_before.total_seconds()
        duration_before_hours = duration_before_in_s / 3600

        duration_after = last_obs_after - first_obs_after
        duration_after_in_s = duration_after.total_seconds()
        duration_after_hours = duration_after_in_s / 3600

        obs_durations.append([duration_before_hours, duration_after_hours])

    if ax == None:
        fig = plt.figure(tight_layout=True)
        ax = fig.add_subplot(111)


    y_list = [[0] * sitesNo, [0] * sitesNo]
    # for i in range(2):
    # y_list.append([0] * sitesNo)
    for j, site_dbFiles in enumerate(dbFileList):

        query_list = getQueryList(site_dbFiles, [transport, transport], [actionType, actionType], [unitIdxs, unitIdxs])
        if isinstance(query_list, str):
            continue
        time_lists = getTimeLists(query_list, [actionType, actionType])

        # if 'line' in actionType.split(' '):
        #     if unitIdxs == 'all_lines':
        #         q =sessions[i].query(func.min(LineCrossing.instant))
        #     else:
        #         q = sessions[i].query(LineCrossing.instant).filter(LineCrossing.lineIdx == unitIdxs)
        #
        #     q = q.join(Line, Line.idx == LineCrossing.lineIdx) \
        #         .join(GroupBelonging, GroupBelonging.groupIdx == LineCrossing.groupIdx) \
        #         .join(Person, Person.idx == GroupBelonging.personIdx) \
        #         .join(Mode, Mode.personIdx == Person.idx) \
        #         .filter(Mode.transport == transport)
        #
        #     if transport != 'walking':
        #         q = q.join(Vehicle, Vehicle.idx == Mode.vehicleIdx)
        #
        #     if transport == 'cardriver':
        #         q = q.filter(Line.type == 'roadbed')
        #             # .filter(Vehicle.category == 'car')
        #
        #     if directions[j] == 'Right to left':
        #         q = q.filter(LineCrossing.rightToLeft == True)
        #     elif directions[j] == 'Left to right':
        #         q = q.filter(LineCrossing.rightToLeft == False)
        #
        # elif 'zone' in actionType.split(' '):
        #     q = sessions[i].query(ZoneCrossing.instant).filter(ZoneCrossing.zoneIdx == unitIdxs). \
        #         join(GroupBelonging, GroupBelonging.groupIdx == ZoneCrossing.groupIdx)
        #     if 'entering' in actionTypes[i].split(' '):
        #         q = q.filter(ZoneCrossing.entering == True)
        #     elif 'exiting' in actionTypes[i].split(' '):
        #         q = q.filter(ZoneCrossing.entering == False)
        #
        # if unitIdxs == 'all_lines':
        #     q = q.group_by(Person.idx)
        # time_list = [t[0] for t in q.all()]

        for i, time_list in enumerate(time_lists):
            if time_list != [] and obs_durations[j][i] != 0:
                y_list[i][j] = len(time_list) / obs_durations[j][i]

    for i in range(len(y_list[0])):
        if y_list[0][i] == 0 and y_list[1][i] == 0:
            y_list[0][i] = None
            y_list[1][i] = None
            siteNames[i] = None

    y_list[0] = [i for i in y_list[0] if not i is None] #list(filter(None, y_list[0]))
    y_list[1] = [i for i in y_list[1] if not i is None]
    siteNames = [i for i in siteNames if not i is None]

    ind = np.arange(len(y_list[0]))
    width = 0.5 / 2
    for i in range(2):
        x = (ind - 0.25 + width / 2) + (width * i)
        ax.bar(x, y_list[i], color=colors[i], width=width, label=BAlabels[i], edgecolor='grey', lw=0.5)

    xticks = siteNames
    ax.set_ylim((-0.03, int(ax.get_ylim()[1]) + 1))

    tm = transport
    if transport == 'cardriver':
        tm = 'car'
    elif transport == 'walking':
        tm = 'pedestrian'
    elif transport == 'cycling':
        tm = 'cyclist'

    tick_rotation = 0
    if len(siteNames) >= 20:
        tick_rotation = 45

    ax.tick_params(axis='x', labelsize=xTickSize, rotation=tick_rotation)
    ax.tick_params(axis='y', labelsize=yTickSize)
    ax.set_xlabel('Name of sites', fontsize=xLabelSize)
    ax.set_ylabel(f'Number of {tm}s per hour', fontsize=yLabelSize)
    # ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xticks(ind, xticks)
    title = f'Flow of {tm}s in all sites'

    ax.set_title(title, fontsize=titleSize)
    ax.grid(True, 'major', 'y', ls='--', lw=.5, c='k', alpha=.3)
    ax.legend(loc="best", fontsize=legendFontSize)

    watermark(ax)


# ==============================================================
def sitesBAactivity(dbFileList, siteNames, BAlabels=['before', 'after'], ax=None, colors=plotColors,
                    titleSize=8, xLabelSize=7, yLabelSize=7, xTickSize=6, yTickSize=6, legendFontSize=6):
    sitesNo = len(dbFileList)
    sites_sessions = []
    obs_durations = []

    for site_dbFiles in dbFileList:
        session_before = connectDatabase(site_dbFiles[0])
        session_after = connectDatabase(site_dbFiles[1])
        sites_sessions.append([session_before, session_after])
        cls_obs = LineCrossing

        first_obs_before = session_before.query(func.min(cls_obs.instant)).first()[0]
        last_obs_before = session_before.query(func.max(cls_obs.instant)).first()[0]

        first_obs_after = session_after.query(func.min(cls_obs.instant)).first()[0]
        last_obs_after = session_after.query(func.max(cls_obs.instant)).first()[0]

        duration_before = last_obs_before - first_obs_before
        duration_before_in_s = duration_before.total_seconds()
        duration_before_hours = duration_before_in_s / 3600

        duration_after = last_obs_after - first_obs_after
        duration_after_in_s = duration_after.total_seconds()
        duration_after_hours = duration_after_in_s / 3600

        obs_durations.append([duration_before_hours, duration_after_hours])

    if ax == None:
        fig = plt.figure(tight_layout=True)
        ax = fig.add_subplot(111)

    y_list = []
    for i in range(2):
        y_list.append([0] * sitesNo)
        for j, sessions in enumerate(sites_sessions):

            q = sessions[i].query(Activity.startTime) \
                .join(GroupBelonging, GroupBelonging.groupIdx == Activity.groupIdx) \
                .join(Person, Person.idx == GroupBelonging.personIdx)

            time_list = [t[0] for t in q.all()]
            if time_list != [] and obs_durations[j][i] != 0:
                y_list[i][j] = len(time_list) / obs_durations[j][i]


    ind = np.arange(len(y_list[0]))
    width = 0.5 / 2
    for i in range(2):
        x = (ind - 0.25 + width / 2) + (width * i)
        ax.bar(x, y_list[i], color=colors[i], width=width, label=BAlabels[i], edgecolor='grey', lw=0.5)

    xticks = siteNames
    # ax.set_ylim((-0.03, int(ax.get_ylim()[1]) + 1))

    tick_rotation = 0
    if len(siteNames) >= 20:
        tick_rotation = 45

    ax.tick_params(axis='x', labelsize=xTickSize, rotation=tick_rotation)
    ax.tick_params(axis='y', labelsize=yTickSize)
    ax.set_xlabel('Name of sites', fontsize=xLabelSize)
    ax.set_ylabel('Number of activities per hour', fontsize=yLabelSize)
    # ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xticks(ind, xticks)
    title = 'Rate of activities in all sites'

    ax.set_title(title, fontsize=titleSize)
    ax.grid(True, 'major', 'y', ls='--', lw=.5, c='k', alpha=.3)
    ax.legend(loc="best", fontsize=legendFontSize)

    watermark(ax)


# ==============================================================
def stackedAllActivities(dbFiles, labels, attribute,
                        ax=None, interval=20, alpha=1, colors=color_dict, siteName=None, textRotation=90,
                        titleSize=8, xLabelSize=7, yLabelSize=7, xTickSize=4, yTickSize=6, legendFontSize=6):
    inputNo = len(dbFiles)
    sessions = []
    first_obs_times = []
    last_obs_times = []

    for i in range(inputNo):
        session = connectDatabase(dbFiles[i])
        sessions.append(session)
        fobst, lobst = getObsStartEnd(session)
        first_obs_times.append(fobst)
        last_obs_times.append(lobst)

    start_obs_time = max(first_obs_times).time()
    end_obs_time = min(last_obs_times).time()

    bins_start = datetime.datetime.combine(datetime.datetime(2000, 1, 1), start_obs_time)
    bins_end = datetime.datetime.combine(datetime.datetime(2000, 1, 1), end_obs_time)

    start = ceil_time(bins_start, interval)
    end = ceil_time(bins_end, interval) - datetime.timedelta(minutes=interval)

    bin_edges = calculateBinsEdges(start, end, interval)
    # bin_edges.insert(0, bins_start)
    # bin_edges.insert(-1, bins_end)

    if len(bin_edges) < 3:
        err = 'The observation duration is not enough for the selected interval!'
        return err

    times = [b.time() for b in bin_edges]

    bins = []
    for i in range(inputNo):
        date1 = first_obs_times[i].date()
        bins.append([datetime.datetime.combine(date1, t) for t in times])


    if ax == None:
        fig = plt.figure(tight_layout=True)
        ax = fig.add_subplot(111)

    bins_num = len(bins[i]) - 1
    ind = np.arange(bins_num)
    width = 0.5 / inputNo

    if attribute in ['age', 'gender']:
        field_ = getattr(Person, attribute)
    elif attribute == 'activity':
        field_ = getattr(Activity, attribute)

    enum_list = field_.type.enums

    for i in range(inputNo):
        x = (ind - 0.25 + width / 2) + (width * i)
        y_offset = np.array([0] * bins_num)

        q = sessions[i].query(Activity.startTime)\
            .join(GroupBelonging, GroupBelonging.groupIdx == Activity.groupIdx)\
            .join(Person, Person.idx == GroupBelonging.personIdx)

        for val in enum_list:
            q_val = q.filter(field_ == val)
            time_list = [i[0] for i in q_val.all()]
            if time_list != []:
                hist, _ = np.histogram(time_list, bins=bins[i])
                ax.bar(x, hist, color=colors[val], bottom=y_offset,
                        width=width, label=val, edgecolor='grey', lw=0.5)

                y_offset = y_offset + hist

        for k, t in enumerate(x):
            ax.text(t, y_offset[k] + 0.1, labels[i], ha='center', va='bottom', rotation=textRotation,
                    fontsize=5)


    # ax.set_xticklabels(fontsize = 6, rotation = 45)#'vertical')
    xticks = []
    for t in range(bins_num):
        xticks.append('{}-{}'.format(bins[0][t].strftime('%H:%M'), bins[0][t + 1].strftime('%H:%M')))

    ax.set_ylim((-0.03, int(ax.get_ylim()[1]) + 1))

    tick_rotation = 0
    if bins_num >= 20:
        tick_rotation = 45

    ax.tick_params(axis='x', labelsize=xTickSize, rotation=tick_rotation)
    ax.tick_params(axis='y', labelsize=yTickSize)
    ax.set_xlabel('Time of day', fontsize=xLabelSize)
    ax.set_ylabel('No. of activities', fontsize=yLabelSize)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xticks(ind, xticks)

    if attribute == 'activity':
        attribute = 'activity type'
    title = f'Number of activities by {attribute} every {interval} minute'
    if siteName != None:
        title = f'{title} in {siteName}'
    ax.set_title(title, fontsize=titleSize)

    ax.grid(True, 'major', 'y', ls='--', lw=.5, c='k', alpha=.3)

    handles, labels = ax.get_legend_handles_labels()
    handle_list = []
    label_list = []
    for i, label in enumerate(labels):
        if not label in label_list:
            handle_list.append(handles[i])
            label_list.append(label)
    ax.legend(handle_list, label_list, loc='best', prop={'size': legendFontSize})


    watermark(ax)


# ==============================================================
def HistActivity(dbFiles, labels, activity,
                 ax=None, interval=20, alpha=1, colors=plotColors, siteName=None, textRotation=90,
                 titleSize=8, xLabelSize=7, yLabelSize=7, xTickSize=4, yTickSize=6, legendFontSize=6):
    inputNo = len(dbFiles)
    sessions = []
    first_obs_times = []
    last_obs_times = []

    for i in range(inputNo):
        session = connectDatabase(dbFiles[i])
        sessions.append(session)
        fobst, lobst = getObsStartEnd(session)
        first_obs_times.append(fobst)
        last_obs_times.append(lobst)

    start_obs_time = max(first_obs_times).time()
    end_obs_time = min(last_obs_times).time()

    bins_start = datetime.datetime.combine(datetime.datetime(2000, 1, 1), start_obs_time)
    bins_end = datetime.datetime.combine(datetime.datetime(2000, 1, 1), end_obs_time)

    start = ceil_time(bins_start, interval)
    end = ceil_time(bins_end, interval) - datetime.timedelta(minutes=interval)

    bin_edges = calculateBinsEdges(start, end, interval)
    # bin_edges.insert(0, bins_start)
    # bin_edges.insert(-1, bins_end)

    if len(bin_edges) < 3:
        err = 'The observation duration is not enough for the selected interval!'
        return err

    times = [b.time() for b in bin_edges]

    bins = []
    for i in range(inputNo):
        date1 = first_obs_times[i].date()
        bins.append([datetime.datetime.combine(date1, t) for t in times])


    if ax == None:
        fig = plt.figure(tight_layout=True)
        ax = fig.add_subplot(111)

    bins_num = len(bins[i]) - 1
    ind = np.arange(bins_num)
    width = 0.5 / inputNo

    for i in range(inputNo):
        x = (ind - 0.25 + width / 2) + (width * i)
        y_offset = np.array([0] * bins_num)

        q = sessions[i].query(Activity.startTime)\
            .filter(Activity.activity == activity)\
            .join(GroupBelonging, GroupBelonging.groupIdx == Activity.groupIdx)\
            .join(Person, Person.idx == GroupBelonging.personIdx)

        time_list = [i[0] for i in q.all()]
        if time_list != []:
            hist, _ = np.histogram(time_list, bins=bins[i])
            ax.bar(x, hist, color=plotColors[i], bottom=y_offset,
                    width=width, label=activity, edgecolor='grey', lw=0.5)

            y_offset = y_offset + hist

        for k, t in enumerate(x):
            ax.text(t, y_offset[k] + 0.1, labels[i], ha='center', va='bottom', rotation=textRotation,
                    fontsize=5)


    # ax.set_xticklabels(fontsize = 6, rotation = 45)#'vertical')
    xticks = []
    for t in range(bins_num):
        xticks.append('{}-{}'.format(bins[0][t].strftime('%H:%M'), bins[0][t + 1].strftime('%H:%M')))

    ax.set_ylim((-0.03, int(ax.get_ylim()[1]) + 1))

    tick_rotation = 0
    if bins_num >= 20:
        tick_rotation = 45

    ax.tick_params(axis='x', labelsize=xTickSize, rotation=tick_rotation)
    ax.tick_params(axis='y', labelsize=yTickSize)
    ax.set_xlabel('Time of day', fontsize=xLabelSize)
    ax.set_ylabel('No. of people', fontsize=yLabelSize)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xticks(ind, xticks)

    title = f'No. of people engaged in {activity} every {interval} minute'
    if siteName != None:
        title = f'{title} in {siteName}'
    ax.set_title(title, fontsize=titleSize)

    ax.grid(True, 'major', 'y', ls='--', lw=.5, c='k', alpha=.3)

    handles, labels = ax.get_legend_handles_labels()
    handle_list = []
    label_list = []
    for i, label in enumerate(labels):
        if not label in label_list:
            handle_list.append(handles[i])
            label_list.append(label)
    # ax.legend(handle_list, label_list, loc='best', prop={'size': legendFontSize})


    watermark(ax)


# ==============================================================

def stackedActivity(dbFiles, labels, activity, attribute,
                        ax=None, interval=20, alpha=1, colors=color_dict, siteName=None, textRotation=90,
                        titleSize=8, xLabelSize=7, yLabelSize=7, xTickSize=4, yTickSize=6, legendFontSize=6):
    inputNo = len(dbFiles)
    sessions = []
    first_obs_times = []
    last_obs_times = []

    for i in range(inputNo):
        session = connectDatabase(dbFiles[i])
        sessions.append(session)
        fobst, lobst = getObsStartEnd(session)
        first_obs_times.append(fobst)
        last_obs_times.append(lobst)

    start_obs_time = max(first_obs_times).time()
    end_obs_time = min(last_obs_times).time()

    bins_start = datetime.datetime.combine(datetime.datetime(2000, 1, 1), start_obs_time)
    bins_end = datetime.datetime.combine(datetime.datetime(2000, 1, 1), end_obs_time)

    start = ceil_time(bins_start, interval)
    end = ceil_time(bins_end, interval) - datetime.timedelta(minutes=interval)

    bin_edges = calculateBinsEdges(start, end, interval)
    # bin_edges.insert(0, bins_start)
    # bin_edges.insert(-1, bins_end)

    if len(bin_edges) < 3:
        err = 'The observation duration is not enough for the selected interval!'
        return err

    times = [b.time() for b in bin_edges]

    bins = []
    for i in range(inputNo):
        date1 = first_obs_times[i].date()
        bins.append([datetime.datetime.combine(date1, t) for t in times])


    if ax == None:
        fig = plt.figure(tight_layout=True)
        ax = fig.add_subplot(111)

    bins_num = len(bins[i]) - 1
    ind = np.arange(bins_num)
    width = 0.5 / inputNo

    if attribute in ['age', 'gender']:
        field_ = getattr(Person, attribute)

    enum_list = field_.type.enums

    for i in range(inputNo):
        x = (ind - 0.25 + width / 2) + (width * i)
        y_offset = np.array([0] * bins_num)

        q = sessions[i].query(Activity.startTime)\
            .filter(Activity.activity == activity)\
            .join(GroupBelonging, GroupBelonging.groupIdx == Activity.groupIdx)\
            .join(Person, Person.idx == GroupBelonging.personIdx)

        for val in enum_list:
            q_val = q.filter(field_ == val)
            time_list = [i[0] for i in q_val.all()]
            if time_list != []:
                hist, _ = np.histogram(time_list, bins=bins[i])
                ax.bar(x, hist, color=colors[val], bottom=y_offset,
                        width=width, label=val, edgecolor='grey', lw=0.5)

                y_offset = y_offset + hist

        for k, t in enumerate(x):
            ax.text(t, y_offset[k] + 0.1, labels[i], ha='center', va='bottom', rotation=textRotation,
                    fontsize=5)


    # ax.set_xticklabels(fontsize = 6, rotation = 45)#'vertical')
    xticks = []
    for t in range(bins_num):
        xticks.append('{}-{}'.format(bins[0][t].strftime('%H:%M'), bins[0][t + 1].strftime('%H:%M')))

    ax.set_ylim((-0.03, int(ax.get_ylim()[1]) + 1))

    tick_rotation = 0
    if bins_num >= 20:
        tick_rotation = 45

    ax.tick_params(axis='x', labelsize=xTickSize, rotation=tick_rotation)
    ax.tick_params(axis='y', labelsize=yTickSize)
    ax.set_xlabel('Time of day', fontsize=xLabelSize)
    ax.set_ylabel(f'No. of people', fontsize=yLabelSize)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xticks(ind, xticks)

    title = f'No. of {activity}s by {attribute} every {interval} minute'
    if siteName != None:
        title = f'{title} in {siteName}'
    ax.set_title(title, fontsize=titleSize)

    ax.grid(True, 'major', 'y', ls='--', lw=.5, c='k', alpha=.3)

    handles, labels = ax.get_legend_handles_labels()
    handle_list = []
    label_list = []
    for i, label in enumerate(labels):
        if not label in label_list:
            handle_list.append(handles[i])
            label_list.append(label)
    ax.legend(handle_list, label_list, loc='best', prop={'size': legendFontSize})


    watermark(ax)


# ==============================================================

def speedHistogram(dbFiles, labels, transports, actionTypes, unitIdxs, directions,
                 ax=None, interval=20, alpha=1, colors=plotColors, ec='k', rwidth=0.9, siteName=None,
                   titleSize=8, xLabelSize=8, yLabelSize=8, xTickSize=8, yTickSize=7, legendFontSize=6):
    inputNo = len(dbFiles)
    speed_lists = []
    # sessions = []
    # for i in range(inputNo):
    #     session = connectDatabase(dbFiles[i])
    #
    #     if unitIdxs[i] == 'all_lines':
    #         q = session.query(func.sum(LineCrossing.speed), func.count(LineCrossing.speed))
    #     else:
    #         q = session.query(LineCrossing.speed).filter(LineCrossing.lineIdx == unitIdxs[i])
    #
    #     q = q.join(Line, Line.idx == LineCrossing.lineIdx) \
    #         .join(GroupBelonging, GroupBelonging.groupIdx == LineCrossing.groupIdx) \
    #         .join(Person, Person.idx == GroupBelonging.personIdx) \
    #         .join(Mode, Mode.personIdx == Person.idx) \
    #         .join(Vehicle, Vehicle.idx == Mode.vehicleIdx) \
    #         .filter(Mode.transport == transports[i]) \
    #         .filter(Vehicle.category == 'car') \
    #         .filter(Line.type == 'roadbed')
    #
    #     if directions[i] == 'Right to left':
    #         q = q.filter(LineCrossing.rightToLeft == True)
    #     elif directions[i] == 'Left to right':
    #         q = q.filter(LineCrossing.rightToLeft == False)
    #
    #     if unitIdxs[i] == 'all_lines':
    #         q = q.group_by(Person.idx)
    #         speed_lists.append([i[0]/i[1] for i in q.all() if i[0] is not None])
    #     else:
    #         speed_lists.append([i[0] for i in q.all() if i[0] is not None])

    query_list = getQueryList(dbFiles, transports, actionTypes, unitIdxs)
    if isinstance(query_list, str):
        return query_list

    for i, q in enumerate(query_list):
        if actionTypes[i] == 'all_crossings':
            speed_list = [r[3] for r in q.all() if not r[3] is None] + \
                         [r[4] for r in q.all() if not r[4] is None]
        else:
            speed_list = [r[2] for r in q.all() if not r[2] is None]
        speed_lists.append(speed_list)


    # # bins_start = int(np.floor(min([min(speed_list1), min(speed_list2)])))
    # bins_end = np.ceil(max([max(speed_list) for speed_list in speed_lists if speed_list != []]))
    # bins_end = int(((bins_end // 10) + 1) * 10)
    #
    # bins = [b for b in range(0, bins_end, interval)]
    # bins_ticks = [(bins[i] + bins[i+1])/2 for i in range(len(bins) - 1)]

    if all(sl==[] for sl in speed_lists):
        return 'No observation!'

    if ax == None:
        fig = plt.figure(tight_layout=True)
        ax = fig.add_subplot(111)

    for i in range(inputNo):
        if speed_lists[i] == []:
            continue
        speed_mean = np.mean(speed_lists[i])
        speed_std = np.std(speed_lists[i])
        density = gaussian_kde(speed_lists[i])
        x = np.linspace(min(speed_lists[i]), max(speed_lists[i]), 300)
        y = density(x)

        ax.axvspan(speed_mean - speed_std, speed_mean + speed_std, label=f'Std. of {labels[i]}',
                   alpha=0.1, color=plotColors[i])
        ax.plot(x, y, label=f'Prob. of {labels[i]}', color=plotColors[i])
        ax.axvline(x=speed_mean, label=f'Avg. of {labels[i]}', ls='--', lw=1, color=plotColors[i])

        # hist, bin_edges = np.histogram(speed_lists[i], bins=bins, density=True)
        # bins_np = np.array(bins_ticks)
        # bins_np_smooth = np.linspace(bins_np.min(), bins_np.max(), len(bins_ticks) * 10)
        # spl = make_interp_spline(bins_np, hist, k=2)
        # value_np_smooth = spl(bins_np_smooth)
        # ax.plot(bins_np_smooth, value_np_smooth, label=labels[i], color=plotColors[i])
        # # ax.hist(speed_lists[i], alpha=alpha, color=colors[i], ec=ec, label=labels[i],
        # #         rwidth=rwidth, bins=bins, density=True)

    ax.tick_params(axis='x', labelsize=xTickSize, rotation=0)
    ax.tick_params(axis='y', labelsize=yTickSize)
    ax.set_xlabel('Speed (km/h)', fontsize=xLabelSize)
    ax.set_ylabel('Probability density', fontsize=yLabelSize)
    ax.legend(fontsize=legendFontSize)
    # ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    userTitle = getUserTitle(transports[0])

    if unitIdxs[0] == 'all_lines':
        title = f'PDF of speed for all observed {userTitle}s'
    else:
        title = f'PDF of speed for {userTitle}s {actionTypes[0]} #{unitIdxs[0]}'
    if siteName != None:
        title = f'{title} in {siteName}'
    ax.set_title(title, fontsize=titleSize)
    ax.grid(True, 'major', 'y', ls='--', lw=.5, c='k', alpha=.3)

    watermark(ax)


# ==============================================================
def speedBoxPlot(dbFiles, labels, transports, actionTypes, unitIdxs, directions,
                 ax=None, interval=20, alpha=1, colors=plotColors, siteName=None,
                 titleSize=8, xLabelSize=8, yLabelSize=8, xTickSize=6, yTickSize=7, legendFontSize=6):

    inputNo = len(dbFiles)
    sessions = []
    first_obs_times = []
    last_obs_times = []

    for i in range(inputNo):
        session = connectDatabase(dbFiles[i])
        sessions.append(session)
        fobst, lobst = getObsStartEnd(session)
        first_obs_times.append(fobst)
        last_obs_times.append(lobst)

    start_obs_time = max(first_obs_times).time()
    end_obs_time = min(last_obs_times).time()


    # for i in range(inputNo):
    #     session = connectDatabase(dbFiles[i])
    #     sessions.append(session)

    # for i in range(inputNo):
    #     if 'line' in actionTypes[i].split(' '):
    #         cls_obs = LineCrossing
    #     elif 'zone' in actionTypes[i].split(' '):
    #         cls_obs = ZoneCrossing
    #
    #     first_obs_time = session.query(func.min(cls_obs.instant)).first()[0]
    #     last_obs_time = session.query(func.max(cls_obs.instant)).first()[0]
    #
    #     first_obs_times.append(first_obs_time.time())
    #     last_obs_times.append(last_obs_time.time())
    #
    # start_obs_time = max(first_obs_times)
    # end_obs_time = min(last_obs_times)

    bins_start = datetime.datetime.combine(datetime.datetime(2000, 1, 1), start_obs_time)
    bins_end = datetime.datetime.combine(datetime.datetime(2000, 1, 1), end_obs_time)

    start = ceil_time(bins_start, interval)
    end = ceil_time(bins_end, interval) - datetime.timedelta(minutes=interval)

    bin_edges = calculateBinsEdges(start, end, interval)

    if len(bin_edges) < 3:
        err = 'The observation duration is not enough for the selected interval!'
        return err

    times = [b.time() for b in bin_edges]

    bins = []
    for i in range(inputNo):
        date1 = getObsStartEnd(sessions[i])[0].date()
        bins.append([datetime.datetime.combine(date1, t) for t in times])

    query_list = getQueryList(dbFiles, transports, actionTypes, unitIdxs)
    if isinstance(query_list, str):
        return query_list

    grouped_speeds = []
    for j, q in enumerate(query_list):
        time_list = getTimeLists([q], [actionTypes[j]])[0]

        if actionTypes[j] == 'all_crossings':
            speed_list = [r[3] for r in q.all()] + \
                         [r[4] for r in q.all()]
        else:
            speed_list = [r[2] for r in q.all()]

        # speed_list = [i[2] for i in q.all()]


    # for j, session in enumerate(sessions):
    #     time_list = []
    #     if 'line' in actionTypes[j].split(' '):
    #         if unitIdxs[j] == 'all_lines':
    #             q = session.query(func.min(LineCrossing.instant), func.sum(LineCrossing.speed),
    #                               func.count(LineCrossing.speed))
    #         else:
    #             q = session.query(LineCrossing.instant, LineCrossing.speed)\
    #                        .filter(LineCrossing.lineIdx == unitIdxs[j])
    #
    #         q = q.join(GroupBelonging, GroupBelonging.groupIdx == LineCrossing.groupIdx) \
    #             .join(Person, Person.idx == GroupBelonging.personIdx) \
    #             .join(Mode, Mode.personIdx == Person.idx) \
    #             .filter(Mode.transport == transports[j])
    #
    #         # q = session.query(LineCrossing.instant, LineCrossing.speed).\
    #         #     filter(LineCrossing.lineIdx == unitIdxs[j]). \
    #         #     join(GroupBelonging, GroupBelonging.groupIdx == LineCrossing.groupIdx)
    #         if directions[j] == 'Right to left':
    #             q = q.filter(LineCrossing.rightToLeft == True)
    #         elif directions[j] == 'Left to right':
    #             q = q.filter(LineCrossing.rightToLeft == False)
    #     elif 'zone' in actionTypes[j].split(' '):
    #         return 'Under developement!'
    #     # q = q.join(Mode, Mode.personIdx == GroupBelonging.personIdx)\
    #     #     .filter(Mode.transport == transports[j])
    #
    #     if unitIdxs[j] == 'all_lines':
    #         q = q.group_by(Person.idx)
    #         time_list = [i[0] for i in q.all()]
    #         speed_list = [i[1]/i[2] if i[1] is not None else None for i in q.all()]
    #     else:
    #         time_list = [i[0] for i in q.all()]
    #         speed_list = [i[1] for i in q.all()]
    #
    #     # time_list = [i[0] for i in q.all()]
    #     # speed_list = [i[1] for i in q.all()]

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

    
    # ticks = []
    # for i in range(len(bins[0]) - 1):
    #     t = (bins[0][i] + (bins[0][i + 1] - bins[0][i]) / 2).time()
    #     ticks.append(t.strftime('%H:%M'))

    ticks = []
    for t in range(len(bins[0]) - 1):
        ticks.append('{}-{}'.format(bins[0][t].strftime('%H:%M'), bins[0][t + 1].strftime('%H:%M')))

    tick_rotation = 0
    if len(bins[0]) - 1 >= 10:
        tick_rotation = 45

    def set_box_color(bp, color):
        plt.setp(bp['boxes'], color=color)
        plt.setp(bp['whiskers'], color=color)
        plt.setp(bp['caps'], color=color)
        plt.setp(bp['medians'], color=color)
        plt.setp(bp['means'], color=color)

    if ax == None:
        fig = plt.figure(tight_layout=True)
        ax = fig.add_subplot(111)

    for i in range(inputNo):
        bp = ax.boxplot(grouped_speeds[i],
                        positions=np.array(range(len(grouped_speeds[i]))) * 2.0 - (-1)**i * 0.4 * (inputNo -1),
                        sym='', widths=0.6, showmeans=False, patch_artist=False)
        set_box_color(bp, colors[i])
        # draw temporary red and blue lines and use them to create a legend
        ax.plot([], c=colors[i], label=labels[i])

    ax.legend(fontsize=legendFontSize)

    # ----------------------
    # locator = mdates.AutoDateLocator()
    # ax.xaxis.set_major_locator(locator)
    # ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    # ax.xaxis.set_minor_locator(mdates.MinuteLocator(byminute=30))
    # ----------------------------

    ax.set_xticks(range(0, len(ticks) * 2, 2))
    ax.set_xticklabels(ticks)
    ax.set_xlim(-1, len(ticks) * 2)

    ax.tick_params(axis='x', labelsize=xTickSize, rotation=tick_rotation)
    ax.tick_params(axis='y', labelsize=yTickSize)
    ax.set_xlabel('Time of day', fontsize=xLabelSize)
    ax.set_ylabel('Speed (km/h)', fontsize=yLabelSize)
    # ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    userTitle = getUserTitle(transports[0])

    if unitIdxs[0] == 'all_lines':
        title = f'Speed of all observed {userTitle}s every {interval} min.'
    else:
        title = f'Speed of {userTitle}s {actionTypes[0]} #{unitIdxs[0]} every {interval} min.'
    if siteName != None:
        title = f'{title} in {siteName}'
    ax.set_title(title, fontsize=titleSize)

    ax.grid(True, 'major', 'y', ls='--', lw=.5, c='k', alpha=.3)

    watermark(ax)


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

    # for i in range(inputNo):
    #     if 'line' in actionTypes[i].split(' '):
    #         cls_obs = LineCrossing
    #     elif 'zone' in actionTypes[i].split(' '):
    #         cls_obs = ZoneCrossing
    #
    #     first_obs_time = session.query(func.min(cls_obs.instant)).first()[0]
    #     last_obs_time = session.query(func.max(cls_obs.instant)).first()[0]
    #
    #     first_obs_times.append(first_obs_time.time())
    #     last_obs_times.append(last_obs_time.time())
    #
    # bins_start = max(first_obs_times)
    # bins_end = min(last_obs_times)

    # start = datetime.datetime.combine(datetime.datetime(2000, 1, 1), bins_start)
    # end = datetime.datetime.combine(datetime.datetime(2000, 1, 1), bins_end)
    # bin_edges = calculateBinsEdges(start, end, interval)
    # if len(bin_edges) < 3:
    #     err = 'The observation duration is not enough for the selected interval!'
    #     return err
    # times = [b.time() for b in bin_edges]

    # times = [bins_start, bins_end]

    # bins = []
    # for i in range(inputNo):
    #     date1 = getObsStartEnd(sessions[i])[0].date()
    #     bins.append([datetime.datetime.combine(date1, t) for t in times])

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
                .join(Vehicle, Vehicle.idx == Mode.vehicleIdx) \
                .filter(Mode.transport == transports[j]) \
                .filter(Vehicle.category == 'car') #\
                # .filter(LineCrossing.instant >= bins[j][0]) \
                # .filter(LineCrossing.instant < bins[j][1])


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

        db_Idx_0 = list(traj_DB_Idxs.keys())[0]
        con = sqlite3.connect(metadataFile)
        cur = con.cursor()
        cur.execute('SELECT cameraViewIdx FROM video_sequences WHERE idx=?', (db_Idx_0,))
        row = cur.fetchall()
        cam_view_id = row[0][0]
        cur.execute('SELECT siteIdx, cameraTypeIdx, homographyFilename FROM camera_views WHERE idx=?',
                    (cam_view_id,))
        row = cur.fetchall()
        site_idx = row[0][0]
        cam_type_idx = row[0][1]
        homoFile = row[0][2]
        cur.execute('SELECT name FROM sites WHERE idx=?', (site_idx,))
        row = cur.fetchall()
        site_name = row[0][0]
        cur.execute(
            'SELECT intrinsicCameraMatrixStr, distortionCoefficientsStr, frameRate FROM camera_types WHERE idx=?',
            (cam_type_idx,))
        row = cur.fetchall()
        intrinsicCameraMatrix = np.array(ast.literal_eval(row[0][0]))
        distortionCoefficients = np.array(ast.literal_eval(row[0][1]))
        frameRate = row[0][2]

        mdbPath = Path(metadataFile).parent
        site_folder = mdbPath / site_name
        homographyFile = site_folder / homoFile
        homography = np.loadtxt(homographyFile, delimiter=' ')

        x_arrays = []
        speed_arrays = []
        for db_Idx in traj_DB_Idxs.keys():
            cur.execute('SELECT databaseFilename FROM video_sequences WHERE idx=?', (db_Idx,))
            row = cur.fetchall()
            date_dbName = row[0][0]

            trjDBFile = mdbPath / site_name / date_dbName
            objects = storage.loadTrajectoriesFromSqlite(trjDBFile, 'object')
            for trj_idx in traj_DB_Idxs[db_Idx]:
                for traj in objects:
                    if str(traj.getNum()) == trj_idx:
                        x_arrays.append(traj.positions.asArray()[0])
                        speed_arrays.append(np.round(traj.getSpeeds()* frameRate * 3.6, 1))
                            # np.array([np.round(v[0]* frameRate * 3.6, 1) for v in traj.getVelocities()]))
                        break
        all_x_arrays.append(x_arrays)
        all_speed_arrays.append(speed_arrays)

    x_mins = []
    x_maxs = []
    for i, x_arrs in enumerate(all_x_arrays):
        x_mins.append(np.min([np.min(x_arr) for x_arr in x_arrs]))
        x_maxs.append(np.max([np.max(x_arr) for x_arr in x_arrs]))

    x_min = 90 #np.max(x_mins)
    x_max = np.min(x_maxs) # 131
    bins = np.arange(x_min, x_max, interval).tolist()

    grouped_speeds = []
    for i, x_arrs in enumerate(all_x_arrays):
        grouped_speed = None

        # for _ in range(len(bins) - 1):
        #     grouped_speed.append(np.array([]))

        for j, x_arr in enumerate(x_arrs):

            x_arr_grouped_speed = []
            for _ in range(len(bins) - 1):
                x_arr_grouped_speed.append(np.array([]))

            inds = np.digitize(x_arr, bins)

            for k, ind in enumerate(inds):
                if 0 < ind < len(bins):
                    x_arr_grouped_speed[ind - 1] = np.append(x_arr_grouped_speed[ind - 1],
                                                             all_speed_arrays[i][j][k])

            avg_speed_bins = []
            for m in range(len(bins) - 1):
                if x_arr_grouped_speed[m].shape[0] != 0:
                    avg_speed_bins.append(np.mean(x_arr_grouped_speed[m]))
                else:
                    avg_speed_bins.append(np.nan)

            if grouped_speed is None:
                grouped_speed = np.array([avg_speed_bins])
            else:
                grouped_speed = np.vstack([grouped_speed, avg_speed_bins])

        grouped_speeds.append(grouped_speed)


    if ax == None:
        fig = plt.figure(tight_layout=True)
        ax = fig.add_subplot(111)

    x = []
    for n in range(len(bins) - 1):
        x.append(bins[n] + (interval / 2))

    for i, grouped_speed in enumerate(grouped_speeds):

        speed = np.nanmean(grouped_speed, axis=0)
        std_speed = np.nanstd(grouped_speed, axis=0)

        # for j, speeds in enumerate(grouped_speed):
        #     if speeds != np.array([]):
        #         # [abs(speeds - np.mean(speeds)) < 1.5 * np.std(speeds)]
        #         speed = np.append(speed, np.mean(speeds))
        #         std_speed = np.append(std_speed, np.std(speeds))
        #     else:
        #         x[j] = None
        # x = [n for n in x if n is not None]
        # [abs(speeds - np.mean(speeds)) < 1.5 * np.std(speeds)]
        # speed = np.array([np.mean(speeds) for speeds in grouped_speed if speeds != np.array([])])
        # std_speed = np.array([np.std(speeds) for speeds in grouped_speed if speeds != np.array([])])

        ax.fill_between(x, speed - std_speed, speed + std_speed,
                        color=colors[i], ec=colors[i], alpha=0.2, label='Std. of {}'.format(labels[i]))
        ax.plot(x, speed, c=colors[i], label=labels[i])

    q_line = sessions[0].query(Line)
    if unitIdxs[0] == 'all_lines':
        for line in q_line.all():
            if line.type.name == 'roadbed':
                x_list = [p.x for p in line.points]
                y_list = [p.y for p in line.points]
                points = np.array([x_list, y_list], dtype=np.float64)
                prj_points = imageToWorldProject(points, intrinsicCameraMatrix, distortionCoefficients, homography)
                ax.axvline(np.average(prj_points[0]), lw=1, alpha=0.5)
    else:
        line = q_line.filter(Line.idx == unitIdxs[0]).first()
        x_list = [p.x for p in line.points]
        y_list = [p.y for p in line.points]
        points = np.array([x_list, y_list], dtype=np.float64)
        prj_points = imageToWorldProject(points, intrinsicCameraMatrix, distortionCoefficients, homography)
        ax.axvline(np.average(prj_points[0]), lw=1, alpha=0.5)


    ax.legend(fontsize=5)

    # ax.set_xticks(range(0, len(ticks) * 2, 2))
    # ax.set_xticklabels(ticks)
    # ax.set_xlim(-1, len(ticks) * 2)

    ax.tick_params(axis='x', labelsize=8, rotation=0)
    ax.tick_params(axis='y', labelsize=7)
    ax.set_xlabel('Location (m.)', fontsize=8)
    ax.set_ylabel('Speed (km/h)', fontsize=8)
    # ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    userTitle = getUserTitle(transports[0])

    ax.set_title('Speed of {}s {} #{}'.format(userTitle, actionTypes[0], unitIdxs[0]), fontsize=8)
    ax.grid(True, 'major', 'y', ls='--', lw=.5, c='k', alpha=.3)

    watermark(ax)


# ==============================================================
def speedSpaceTimePlot(dbFiles, labels, transports, actionTypes, unitIdxs, directions, metadataFile,
                 axs=None, interval_space=0.5, interval_time=10, colors=plotColors):
    inputNo = len(dbFiles)
    first_obs_times = []
    last_obs_times = []

    for i in range(inputNo):
        session = connectDatabase(dbFiles[i])
        fobst, lobst = getObsStartEnd(session)
        first_obs_times.append(fobst)
        last_obs_times.append(lobst)

    bins_start = max(first_obs_times).time()
    bins_end = min(last_obs_times).time()

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



    # ---------------
    query_list = getQueryList(dbFiles, transports, actionTypes, unitIdxs)
    if isinstance(query_list, str):
        return query_list

    time_lists = getTimeLists(query_list, actionTypes)

    if all([i == [] for i in time_lists]):
        return 'No observation!'

    for time_list in time_lists:
        if time_list == []:
            continue
        for i, time_ticks in enumerate(time_list):
            time_list[i] = datetime.datetime(2000, 1, 1, time_ticks.hour, time_ticks.minute, time_ticks.second)

    if ax == None:
        fig = plt.figure(tight_layout=True)  # figsize=(5, 5), dpi=200, tight_layout=True)
        ax = fig.add_subplot(111)  # plt.subplots(1, 1)

    # ------------------------------------









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
                .join(Vehicle, Vehicle.idx == Mode.vehicleIdx) \
                .filter(Mode.transport == transports[j]) \
                .filter(Vehicle.category == 'car') #\
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

        db_Idx_0 = list(traj_DB_Idxs.keys())[0]
        con = sqlite3.connect(metadataFile)
        cur = con.cursor()
        cur.execute('SELECT cameraViewIdx FROM video_sequences WHERE idx=?', (db_Idx_0,))
        row = cur.fetchall()
        cam_view_id = row[0][0]
        cur.execute('SELECT siteIdx, cameraTypeIdx, homographyFilename FROM camera_views WHERE idx=?',
                    (cam_view_id,))
        row = cur.fetchall()
        site_idx = row[0][0]
        cam_type_idx = row[0][1]
        homoFile = row[0][2]
        cur.execute('SELECT name FROM sites WHERE idx=?', (site_idx,))
        row = cur.fetchall()
        site_name = row[0][0]
        cur.execute(
            'SELECT intrinsicCameraMatrixStr, distortionCoefficientsStr, frameRate FROM camera_types WHERE idx=?',
            (cam_type_idx,))
        row = cur.fetchall()
        intrinsicCameraMatrix = np.array(ast.literal_eval(row[0][0]))
        distortionCoefficients = np.array(ast.literal_eval(row[0][1]))
        frameRate = row[0][2]

        mdbPath = Path(metadataFile).parent
        site_folder = mdbPath / site_name
        homographyFile = site_folder / homoFile
        homography = np.loadtxt(homographyFile, delimiter=' ')

        for db_Idx in traj_DB_Idxs.keys():
            cur.execute('SELECT databaseFilename FROM video_sequences WHERE idx=?', (db_Idx,))
            row = cur.fetchall()
            date_dbName = row[0][0]

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
    # print('time bins: ', time_bins)
    # print(all_trj_time_inds)
    x_mins = []
    x_maxs = []
    for i, x_arrs in enumerate(all_x_arrays):
        x_mins.append(np.min([np.min(x_arr) for x_arr in x_arrs]))
        x_maxs.append(np.max([np.max(x_arr) for x_arr in x_arrs]))

    x_min = 90 #np.max(x_mins)
    x_max = np.min(x_maxs) #131
    space_bins = np.arange(x_min, x_max, interval_space).tolist()

    grouped_speeds = []
    for i, x_arrs in enumerate(all_x_arrays):

        grouped_speed = []
        for r in range(len(time_bins[i]) - 1):
            grouped_speed.append(None)   #.append([])
            # for c in range(len(space_bins) - 1):
            #     grouped_speed[r].append(np.array([]))

        for j, x_arr in enumerate(x_arrs):

            x_arr_grouped_speed = []
            for _ in range(len(space_bins) - 1):
                x_arr_grouped_speed.append(np.array([]))

            space_inds = np.digitize(x_arr, space_bins)

            for k, ind in enumerate(space_inds):
                if 0 < ind < len(space_bins):
                    x_arr_grouped_speed[ind - 1] = np.append(x_arr_grouped_speed[ind - 1],
                                                             all_speed_arrays[i][j][k])
            # print(x_arr_grouped_speed)
            avg_speed_bins = []
            for m in range(len(space_bins) - 1):
                if x_arr_grouped_speed[m].shape[0] != 0:
                    avg_speed_bins.append(np.mean(x_arr_grouped_speed[m]))
                else:
                    avg_speed_bins.append(np.nan)
            # print(avg_speed_bins)
            # print(all_trj_time_inds[i][j])
            if 0 < all_trj_time_inds[i][j] < len(time_bins[i]):
                if grouped_speed[-all_trj_time_inds[i][j]] is None:
                    grouped_speed[-all_trj_time_inds[i][j]] = np.array([avg_speed_bins])
                else:
                    grouped_speed[-all_trj_time_inds[i][j]] = np.vstack([grouped_speed[-all_trj_time_inds[i][j]],
                                                                        avg_speed_bins])

                    # if 0 < all_trj_time_inds[i][j] < len(time_bins[i]):
                    #     grouped_speed[-all_trj_time_inds[i][j]][ind - 1] = \
                    #         np.append(grouped_speed[-all_trj_time_inds[i][j]][ind - 1],
                    #                                  all_speed_arrays[i][j][k])
        # print(grouped_speed)
        grouped_speeds.append(grouped_speed)

    if axs is None:
        fig = plt.figure(tight_layout=True)
        axs = fig.subplots(1, inputNo, sharey='row')

    if inputNo == 1:
        ax = [axs]
    elif inputNo == 2:
        ax = [axs[0], axs[1]]

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

        speed = None

        for trajs_speed in grouped_speed:
            if trajs_speed is not None:
                new_row = np.nanmean(trajs_speed, axis=0)
            else:
                new_row = np.array([np.nan]*(len(space_bins) - 1))

            if speed is None:
                speed = np.array([new_row])
            else:
                speed = np.vstack([speed, new_row])

            # for c, speeds in enumerate(speeds_list):
            #     if speeds != np.array([]):
            #         speed[r][c] = round(np.mean(speeds),2)
            #         #[abs(speeds - np.mean(speeds)) < 1.5 * np.std(speeds)]), 2)

        t_num = mdates.date2num(t)
        X, T = np.meshgrid(x, t_num)
        contour = ax[i].contourf(X, T, speed, 10, cmap='RdYlBu_r')
        # im = ax.imshow(speed, extent=[x[0], x[-1], t_num[0], t_num[-1]], origin='lower',
        #                cmap='RdYlBu_r', aspect='auto') #np.array(speed, dtype=float))


        q_line = sessions[i].query(Line)
        if unitIdxs[i] == 'all_lines':
            for line in q_line.all():
                if line.type.name == 'roadbed':
                    x_list = [p.x for p in line.points]
                    y_list = [p.y for p in line.points]
                    points = np.array([x_list, y_list], dtype=np.float64)
                    prj_points = imageToWorldProject(points, intrinsicCameraMatrix, distortionCoefficients, homography)
                    ax[i].axvline(np.average(prj_points[0]), lw=1, alpha=0.5)
        else:
            line = q_line.filter(Line.idx == unitIdxs[i]).first()
            x_list = [p.x for p in line.points]
            y_list = [p.y for p in line.points]
            points = np.array([x_list, y_list], dtype=np.float64)
            prj_points = imageToWorldProject(points, intrinsicCameraMatrix, distortionCoefficients, homography)
            ax[i].axvline(np.average(prj_points[0]), lw=1, alpha=0.5)

        ax[i].yaxis_date()
        # locator = mdates.AutoDateLocator()
        # ax.xaxis.set_major_locator(locator)
        date_format = mdates.DateFormatter('%H:%M')
        ax[i].yaxis.set_major_formatter(date_format)


        ax[i].tick_params(axis='x', labelsize=6, rotation=0)
        ax[i].tick_params(axis='y', labelsize=6)
        ax[i].set_xlabel('Location (m.)', fontsize=7)
        if i == 0:
            ax[i].set_ylabel('Time of day', fontsize=7)
        # ax.yaxis.set_major_locator(MaxNLocator(integer=True))

        ax[i].set_title(labels[i], fontsize=6)

        watermark(ax[i])

    if axs is not None:
        fig = ax[0].get_figure()

    fig.subplots_adjust(bottom=0.15, top=0.9, left=0.1, right=0.8,
                        wspace=0.04, hspace=0.03)

    # add an axes, lower left corner in [0.83, 0.15] with axes width 0.02 and height 0.75
    cb_ax = fig.add_axes([0.83, 0.15, 0.02, 0.75])
    cbar = fig.colorbar(contour, cax=cb_ax)
    cbar.set_label(label='Speed (km/h)', size=6)
    cbar.ax.tick_params(labelsize=6)

    userTitle = getUserTitle(transports[0])

    plt.suptitle('Speed of {}s {} #{} over time'.format(userTitle, actionTypes[0], unitIdxs[0]), fontsize=8)
    # ax.grid(True, 'major', 'y', ls='--', lw=.5, c='k', alpha=.3)


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
def pieChart(dbFiles, chartLabels, transport, attr, axs=None, startTimes=None, endTimes=None, siteName=None,
             titleSize=12, percTextSize=10, labelSize=10):

    inputNo = len(dbFiles)
    sessions = []
    first_obs_times = []
    last_obs_times = []

    for i in range(inputNo):
        session = connectDatabase(dbFiles[i])
        sessions.append(session)

    if axs is None:
        fig = plt.figure(tight_layout=True)
        fig.set_figheight(5)
        fig.set_figwidth(10)
        axs = fig.subplots(1, inputNo)#, sharex=True, sharey=True)


    for i in range(inputNo):
        if inputNo > 1:
            ax = axs[i]
        else:
            ax = axs
        ax.axis('equal')
        session = sessions[i]

        labels_sizes = getLabelSizePie(transport, attr, session)
        if not isinstance(labels_sizes, str):
            labels, sizes = labels_sizes
        else:
            return labels_sizes
        explode = [0.02]*len(labels)

        wedges, texts, autotexts = ax.pie(sizes, explode=explode, labels=labels, autopct='%1.1f%%',
                                          shadow=False, startangle=90,
                                          textprops={'size': percTextSize, 'weight':'normal'})

        for pie_wedge in wedges:
            # pie_wedge.set_edgecolor('gray')
            pie_wedge.set_facecolor(color_dict[pie_wedge.get_label()])

        # ax.axis('equal')
        # ax.legend(wedges, labels,
        #           title="title",
        #           loc="upper right")

        ax.set_title(chartLabels[i], fontsize=titleSize, y=-0.05, weight="bold")
        plt.setp(autotexts, size=labelSize, weight="normal")

    if transport == 'all_modes':
        suptitle = f'Mode share'
    elif transport == 'cardriver':
        suptitle = f'Vehicle types'
    elif transport == 'walking':
        suptitle = f'Pedestrians by {attr}'
    elif transport == 'cycling':
        suptitle = f'Cyclists by {attr}'
    elif transport == 'Activity':
        if attr == 'activity':
            attr_str = 'activity type'
        else:
            attr_str = attr
        suptitle = f'Activities by {attr_str}'

    if siteName != None:
        suptitle = f'{suptitle} in {siteName}'

    plt.suptitle(suptitle, fontsize=titleSize, weight="bold")

    # watermark(axs[0])


# =====================================================================
def generateReportTransit(dbFileName, transport, actionType, unitIdx, direction, interval,
                   start_time=None, end_time=None, showReport=False, ax=None, outputFile=None,
                   mainDirection='both', labelRtoL=None, labelLtoR=None):

    session = connectDatabase(dbFileName)
    start_obs_time, end_obs_time = getObsStartEnd(session)
    obs_date = start_obs_time.date()

    if start_time != None and end_time != None:
        start_time = datetime.datetime.combine(obs_date, start_time)
        end_time = datetime.datetime.combine(obs_date, end_time)

    query_list = getQueryList([dbFileName], [transport], [actionType], [unitIdx], start_time, end_time)
    if isinstance(query_list, str):
        return query_list

    q = query_list[0]

    if q.count() == 0:
        err = 'No observation!'
        return err

    if start_time == None and end_time == None:
        start_time = start_obs_time
        end_time = end_obs_time

    entP_peakHours = getPeakHours(start_time, end_time, interval)

    indDf = pd.DataFrame(columns=list(entP_peakHours.keys()))#, index=['Start time', 'End time', 'Duration'])

    duration = end_time - start_time
    duration_in_s = duration.total_seconds()
    duration_hours = duration_in_s / 3600

    # if 'line' in actionType.split('_'):
    #     if unitIdx == 'all_lines':
    #         q = session.query(LineCrossing.groupIdx, func.sum(LineCrossing.speed), func.count(LineCrossing.speed))
    #     else:
    #         q = session.query(LineCrossing.groupIdx, LineCrossing.speed) \
    #             .filter(LineCrossing.lineIdx == unitIdx)
    #
    #     q = q.join(Line, Line.idx == LineCrossing.lineIdx) \
    #         .join(GroupBelonging, GroupBelonging.groupIdx == LineCrossing.groupIdx) \
    #         .join(Person, Person.idx == GroupBelonging.personIdx) \
    #         .join(Mode, Mode.personIdx == Person.idx) \
    #         .filter(Mode.transport == transport) \
    #         .filter(LineCrossing.instant >= start_obs_time) \
    #         .filter(LineCrossing.instant < end_obs_time)
    #
    #     if transport != 'walking':
    #         q = q.join(Vehicle, Vehicle.idx == Mode.vehicleIdx)
    #
    #     if transport == 'cardriver':
    #         q = q.filter(Line.type == 'roadbed')
    #         # .filter(Vehicle.category == 'car')
    #
    #     if direction == 'Right to left':
    #         q = q.filter(LineCrossing.rightToLeft == True)
    #     elif direction == 'Left to right':
    #         q = q.filter(LineCrossing.rightToLeft == False)
    #
    # elif 'zone' in actionType.split('_'):
    #     q = session.query(ZoneCrossing.idx) \
    #         .filter(ZoneCrossing.instant >= start_obs_time) \
    #         .filter(ZoneCrossing.instant < end_obs_time) \
    #         .join(GroupBelonging, GroupBelonging.groupIdx == ZoneCrossing.groupIdx)
    #
    # if unitIdx == 'all_lines':
    #     q = q.group_by(Person.idx)


    if transport == 'walking':
        # if 'line' in actionType.split('_'):
        indicators = ['No. of all pedestrians',  # 0
                      'No. of females',  # 1
                      'No. of males',  # 2
                      'No. of children',  # 3
                      'No. of elderly people',  # 4
                      'No. of people with pet',  # 5
                      'No. of disabled people',  # 6
                      'Flow of pedestrians (ped/h)',  # 7
                      'No. of all groups',  # 8
                      'No. of pedestrians alone',  # 9
                      'No. of groups with size = 2',  # 10
                      'No. of groups with size = 3',  # 11
                      'No. of groups with size > 3',  # 12
                      'People walking on roadbed'    # 13
                      ]

        no_all_peds = q.count()

        for p in entP_peakHours.keys():
            if entP_peakHours[p] is None:
                continue

            lowerBound = datetime.datetime.combine(obs_date, entP_peakHours[p][0])
            upperBound = datetime.datetime.combine(obs_date, entP_peakHours[p][1])

            duration = upperBound - lowerBound
            duration_in_s = duration.total_seconds()
            duration_hours = duration_in_s / 3600

            if p == indDf.columns[0]:
                q_all_peaks = q
            else:
                if 'line' in actionType.split('_'):
                    q_all_peaks = q.filter(LineCrossing.instant >= lowerBound)\
                                   .filter(LineCrossing.instant < upperBound)
                elif 'zone' in actionType.split('_'):
                    q_all_peaks = q.filter(ZoneCrossing.instant >= lowerBound)\
                                   .filter(ZoneCrossing.instant < upperBound)
                elif actionType == 'all_crossings':
                    q_all_peaks = q.filter(or_(and_(LineCrossing.instant >= lowerBound, LineCrossing.instant < upperBound),
                                               and_(ZoneCrossing.instant >= lowerBound, ZoneCrossing.instant < upperBound)))


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
                            pct = round((groups_count[1] / len(sizes_list)) * 100, 1)
                            indDf.loc[ind, p] = '{} ({}%)'.format(groups_count[1], pct)
                        elif i == 10 and 2 in groups_count:
                            pct = round((groups_count[2] / len(sizes_list)) * 100, 1)
                            indDf.loc[ind, p] = '{} ({}%)'.format(groups_count[2], pct)
                        elif i == 11 and 3 in groups_count:
                            pct = round((groups_count[3] / len(sizes_list)) * 100, 1)
                            indDf.loc[ind, p] = '{} ({}%)'.format(groups_count[3], pct)
                        elif i == 12 and 4 in groups_count:
                            n = sum([groups_count[i] for i in groups_count.keys() if i > 3])
                            pct = round((n / len(sizes_list)) * 100, 1)
                            indDf.loc[ind, p] = '{} ({}%)'.format(n, pct)
                        else:
                            indDf.loc[ind, p] = '{} ({}%)'.format(0, 0)
                    else:
                        indDf.loc[ind, p] = '{}'.format(0)

                elif i == 13:
                    if 'line' in actionType.split('_'):
                        no_road_peak = q_all_peaks.filter(Line.type == 'roadbed').count()
                    elif 'zone' in actionType.split('_'):
                        no_road_peak = q_all_peaks.filter(Zone.type == 'roadbed').count()
                    elif actionType == 'all_crossings':
                        no_road_peak = q_all_peaks.filter(or_(Line.type == 'roadbed', Zone.type == 'roadbed')).count()
                    pct = round((no_road_peak / noAll) * 100, 1) if noAll != 0 else 0
                    indDf.loc[ind, p] = '{} ({}%)'.format(no_road_peak, pct)



    elif transport == 'cardriver':
        # if 'line' in actionType.split('_'):
        indicators = ['No. of all vehicles',   # 0
                      f'No. of vehicles towards {labelLtoR}',  # 1
                      f'No. of vehicles towards {labelRtoL}',  # 2
                      f'Flow of vehicles towards {labelLtoR} (veh/h)', # 3
                      f'Flow of vehicles towards {labelRtoL} (veh/h)',  # 4
                      'Flow of all vehicles (veh/h)', # 5
                      'Speed: average (km/h)',    # 6
                      'Speed: std (km/h)',  # 7
                      'Speed: median (km/h)',  # 8
                      'Speed: 85th percentile (km/h)',  # 9
                      'Percent of drivers comply with speed limit' # 10
                      ]

        no_all_vehs = q.count()

        if no_all_vehs == 0:
            return indDf

        for p in entP_peakHours.keys():
            if entP_peakHours[p] is None:
                continue

            lowerBound = datetime.datetime.combine(obs_date, entP_peakHours[p][0])
            upperBound = datetime.datetime.combine(obs_date, entP_peakHours[p][1])

            duration = upperBound - lowerBound
            duration_in_s = duration.total_seconds()
            duration_hours = duration_in_s / 3600

            if p == indDf.columns[0]:
                q_all_peaks = q
            else:
                if 'line' in actionType.split('_'):
                    q_all_peaks = q.filter(LineCrossing.instant >= lowerBound) \
                        .filter(LineCrossing.instant < upperBound)
                elif 'zone' in actionType.split('_'):
                    q_all_peaks = q.filter(ZoneCrossing.instant >= lowerBound) \
                        .filter(ZoneCrossing.instant < upperBound)
                elif actionType == 'all_crossings':
                    q_all_peaks = q.filter(or_(and_(LineCrossing.instant >= lowerBound, LineCrossing.instant < upperBound),
                                               and_(ZoneCrossing.instant >= lowerBound, ZoneCrossing.instant < upperBound)))

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

                elif i == 1 and mainDirection == 'both':
                    no_lToR_peak = q_all_peaks.filter(LineCrossing.rightToLeft == False).count()
                    pct = round((no_lToR_peak / noAll) * 100, 1) if noAll != 0 else 0
                    indDf.loc[ind, p] = '{} ({}%)'.format(no_lToR_peak, pct)

                elif i == 2 and mainDirection == 'both':
                    no_rToL_peak = q_all_peaks.filter(LineCrossing.rightToLeft == True).count()
                    pct = round((no_rToL_peak / noAll) * 100, 1) if noAll != 0 else 0
                    indDf.loc[ind, p] = '{} ({}%)'.format(no_rToL_peak, pct)

                elif i ==3 and mainDirection == 'both':
                    no_lToR_peak = q_all_peaks.filter(LineCrossing.rightToLeft == False).count()
                    indDf.loc[ind, p] = '{}'.format(round(no_lToR_peak / duration_hours, 1))

                elif i == 4 and mainDirection == 'both':
                    no_rToL_peak = q_all_peaks.filter(LineCrossing.rightToLeft == True).count()
                    indDf.loc[ind, p] = '{}'.format(round(no_rToL_peak / duration_hours, 1))

                elif i == 5 and mainDirection != 'both':
                    indDf.loc[ind, p] = '{}'.format(round(no_all_peak / duration_hours, 1))

                elif 5 < i < 10:
                    rec_list = q_all_peaks.all()
                    if rec_list != []:
                        if actionType == 'all_crossings':
                            speed_list = [r[3] for r in rec_list if not r[3] is None] + \
                                         [r[4] for r in rec_list if not r[4] is None]
                        else:
                            speed_list = [r[2] for r in rec_list if not r[2] is None]
                        # speed_list = [i[2] for i in rec_list if i[2] != None]
                        if i == 6:
                            stat_val = round(np.mean(speed_list), 1)
                        elif i == 7:
                            stat_val = round(np.std(speed_list), 1)
                        elif i == 8:
                            stat_val = round(np.median(speed_list), 1)
                        elif i == 9:
                            stat_val = round(np.percentile(speed_list, 85), 1)
                    else:
                        stat_val = 0
                    indDf.loc[ind, p] = '{}'.format(stat_val)


    elif transport == 'cycling':
        # if 'line' in actionType.split('_'):
        indicators = ['No. of all cyclists',  # 0
                      'Flow of cyclists (bik/h)',  # 1
                      'Cyclists riding on sidewalk',  # 2
                      'Cyclists riding against traffic',  # 3
                      'No. of female cyclists',  #4
                      'No. of children cycling',  # 5
                      'Speed: average (km/h)',   # 6
                      'Speed: std (km/h)',       # 7
                      'Speed: median (km/h)',    # 8
                      'Speed: 85th percentile (km/h)',  # 9
                      'Percent of cyclists comply with speed limit'  # 10
                      ]

        no_all_biks = q.count()

        if no_all_biks == 0:
            return indDf

        for p in entP_peakHours.keys():
            if entP_peakHours[p] is None:
                continue

            lowerBound = datetime.datetime.combine(obs_date, entP_peakHours[p][0])
            upperBound = datetime.datetime.combine(obs_date, entP_peakHours[p][1])

            duration = upperBound - lowerBound
            duration_in_s = duration.total_seconds()
            duration_hours = duration_in_s / 3600

            if p == indDf.columns[0]:
                q_all_peaks = q
            else:
                if 'line' in actionType.split('_'):
                    q_all_peaks = q.filter(LineCrossing.instant >= lowerBound) \
                        .filter(LineCrossing.instant < upperBound)
                elif 'zone' in actionType.split('_'):
                    q_all_peaks = q.filter(ZoneCrossing.instant >= lowerBound) \
                        .filter(ZoneCrossing.instant < upperBound)
                elif actionType == 'all_crossings':
                    q_all_peaks = q.filter(or_(and_(LineCrossing.instant >= lowerBound, LineCrossing.instant < upperBound),
                                               and_(ZoneCrossing.instant >= lowerBound, ZoneCrossing.instant < upperBound)))

            no_all_peak = q_all_peaks.count()

            for i, ind in enumerate(indicators):

                if p == indDf.columns[0]:
                    noAll = no_all_biks
                elif p != indDf.columns[0] and ind in list(indDf.index):
                    noAll = float(indDf.loc[ind].iloc[0].split(' ')[0])

                # i = indicators.index(ind)
                if i == 0:
                    if p == indDf.columns[0]:
                        indDf.loc[ind, p] = '{}'.format(no_all_biks)
                    else:
                        pct = round((no_all_peak / noAll) * 100, 1) if noAll != 0 else 0
                        indDf.loc[ind, p] = '{} ({}%)'.format(no_all_peak, pct)

                elif i == 1:
                    no_all_peak = q_all_peaks.count()
                    flow_all_peak = round(no_all_peak / duration_hours, 1)
                    indDf.loc[ind, p] = '{}'.format(flow_all_peak)

                elif i == 2:
                    if unitIdx != 'all_units':
                        continue
                    if 'line' in actionType.split('_'):
                        q_lineType_peak = q_all_peaks.filter(Line.type == 'sidewalk')
                    elif 'zone' in actionType.split('_'):
                        q_lineType_peak = q_all_peaks.filter(Zone.type == 'sidewalk')
                    elif actionType == 'all_crossings':
                        q_lineType_peak = q_all_peaks.filter(or_(Line.type == 'sidewalk', Zone.type == 'sidewalk'))

                    no_sdwk_peak = q_lineType_peak.count()
                    pct = round((no_sdwk_peak / noAll) * 100, 1) if noAll != 0 else 0
                    indDf.loc[ind, p] = '{} ({}%)'.format(no_sdwk_peak, pct)

                elif i ==3:
                    if mainDirection == 'both':
                        continue
                    elif mainDirection == 'right-to-left':
                        against_tf = False
                    elif mainDirection == 'left-to-right':
                        against_tf = True
                    q_against = q_all_peaks.filter(LineCrossing.rightToLeft == against_tf)
                    no_agst_peak = q_against.count()
                    pct = round((no_agst_peak / noAll) * 100, 1) if noAll != 0 else 0
                    indDf.loc[ind, p] = '{} ({}%)'.format(no_agst_peak, pct)

                elif i == 4:
                    q_femaleCyclist_peak = q_all_peaks.filter(Person.gender == 'female')
                    no_femCylist_peak = q_femaleCyclist_peak.count()
                    pct = round((no_femCylist_peak / noAll) * 100, 1) if noAll != 0 else 0
                    indDf.loc[ind, p] = '{} ({}%)'.format(no_femCylist_peak, pct)

                elif i == 5:
                    q_childCyclist_peak = q_all_peaks.filter(Person.age == 'child')
                    no_childCylist_peak = q_childCyclist_peak.count()
                    pct = round((no_childCylist_peak / noAll) * 100, 1) if noAll != 0 else 0
                    indDf.loc[ind, p] = '{} ({}%)'.format(no_childCylist_peak, pct)

                elif 5 < i < 10:
                    rec_list = q_all_peaks.all()
                    if rec_list != []:
                        if actionType == 'all_crossings':
                            speed_list = [r[3] for r in rec_list if not r[3] is None] + \
                                         [r[4] for r in rec_list if not r[4] is None]
                        else:
                            speed_list = [r[2] for r in rec_list if not r[2] is None]
                        # speed_list = [i[2] for i in rec_list if i[2] != None]
                        if i == 6:
                            stat_val = round(np.mean(speed_list), 1)
                        elif i == 7:
                            stat_val = round(np.std(speed_list), 1)
                        elif i == 8:
                            stat_val = round(np.median(speed_list), 1)
                        elif i == 9:
                            stat_val = round(np.percentile(speed_list, 85), 1)
                    else:
                        stat_val = 0
                    indDf.loc[ind, p] = '{}'.format(stat_val)


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

    # ----- Deleting second and last column
    indDf = indDf.drop([indDf.columns[1], indDf.columns[-1]], axis=1)

    # ----------- Plotting the report ------------------
    if (showReport == True and ax == None) or outputFile != None:
        row_num, col_num = indDf.shape

        if showReport == False:
            plt.ioff()

        if ax == None:
            fig, ax = plt.subplots(tight_layout=True)  # , figsize=(6,2))
            fig.patch.set_visible(False)
            ax.axis('off')
            fig.set_figheight(fig.get_figheight() * (0.0450937950937951 * (row_num + 1)))
        else:
            fig = ax.get_figure()

        norm_indDf = pd.DataFrame()
        for i in range(indDf.shape[0]):
            for j in range(indDf.shape[1]):
                if j == 0:
                    norm_indDf.loc[i, j] = np.nan
                    continue
                val_str = str(indDf.iloc[i, j]).split(' ')[0]
                if val_str.isdigit():
                    value = int(val_str)
                elif val_str.replace('.', '', 1).isdigit():
                    value = float(val_str)
                else:
                    value = np.nan
                norm_indDf.loc[i, j] = value
            min_val = np.nanmin(norm_indDf.loc[i, :])
            max_val = np.nanmax(norm_indDf.loc[i, :])
            range_val = max_val - min_val
            if range_val != 0:
                norm_indDf.loc[i, :] = norm_indDf.loc[i, :].apply(lambda x: (x - min_val) / range_val)
            else:
                norm_indDf.loc[i, :] = 0

        norm_indDf.iloc[:, 0] = np.nan

        cmap = matplotlib.cm.get_cmap('Wistia')
        cellColours = cmap(norm_indDf.values)

        the_table = ax.table(cellText=indDf.values,
                             cellLoc='center',
                             cellColours=cellColours,
                             colLabels=indDf.columns,
                             colLoc='center',
                             colColours=['lavender']*col_num,
                             rowLabels=indDf.index,
                             rowColours=['lavender']*row_num,
                             rowLoc='right',
                             # bbox=(0, 0, 1, 1),
                             # edges='horizontal',
                             loc='center')

        the_table.auto_set_font_size(False)
        the_table.set_fontsize(6)

        # the_table.scale(1, 1.5)

        # ax.text(-0.22, 0.85, str('StudioProject'),
        #         fontsize=7, color='gray',
        #         ha='left', va='bottom',
        #         transform=ax.transAxes,
        #         weight="bold", alpha=.5)

        if outputFile != None:
            plt.savefig(outputFile, bbox_inches='tight')
            if showReport == False:
                plt.close(fig)

        if showReport == True:
            plt.show()

    return indDf


# =====================================================================
def generateReportPlace(dbFileName, interval,start_time=None, end_time=None,
                        showReport=False, ax=None, outputFile=None):

    session = connectDatabase(dbFileName)

    if start_time == None and end_time == None:
        start_obs_time, end_obs_time = getObsStartEnd(session)

    elif start_time != None and end_time != None:
        obs_date = getObsStartEnd(session)[0].date()
        start_obs_time = datetime.datetime.combine(obs_date, start_time)
        end_obs_time = datetime.datetime.combine(obs_date, end_time)
    else:
        return 'The input arguments are not correct!'

    entP_peakHours = getPeakHours(start_obs_time, end_obs_time, interval)

    indDf = pd.DataFrame(columns=list(entP_peakHours.keys()))#, index=['Start time', 'End time', 'Duration'])

    duration = end_obs_time - start_obs_time
    duration_in_s = duration.total_seconds()
    duration_hours = duration_in_s / 3600


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

    # ----- Deleting second and last column
    indDf = indDf.drop([indDf.columns[1], indDf.columns[-1]], axis=1)

    # ----------- Plotting the report ------------------
    if (showReport == True and ax == None) or outputFile != None:
        row_num, col_num = indDf.shape

        if showReport == False:
            plt.ioff()

        if ax == None:
            fig, ax = plt.subplots(tight_layout=True)  # , figsize=(6,2))
            fig.patch.set_visible(False)
            ax.axis('off')
            fig.set_figheight(fig.get_figheight() * (0.0450937950937951 * (row_num + 1)))
        else:
            fig = ax.get_figure()

        norm_indDf = pd.DataFrame()
        for i in range(indDf.shape[0]):
            for j in range(indDf.shape[1]):
                if j == 0:
                    norm_indDf.loc[i, j] = np.nan
                    continue
                val_str = str(indDf.iloc[i, j]).split(' ')[0]
                if val_str.isdigit():
                    value = int(val_str)
                elif val_str.replace('.', '', 1).isdigit():
                    value = float(val_str)
                else:
                    value = np.nan
                norm_indDf.loc[i, j] = value
            min_val = np.nanmin(norm_indDf.loc[i, :])
            max_val = np.nanmax(norm_indDf.loc[i, :])
            range_val = max_val - min_val
            if range_val != 0:
                norm_indDf.loc[i, :] = norm_indDf.loc[i, :].apply(lambda x: (x - min_val) / range_val)
            else:
                norm_indDf.loc[i, :] = 0

        norm_indDf.iloc[:, 0] = np.nan

        cmap = matplotlib.cm.get_cmap('Wistia')
        cellColours = cmap(norm_indDf.values)

        the_table = ax.table(cellText=indDf.values,
                             cellLoc='center',
                             cellColours=cellColours,
                             colLabels=indDf.columns,
                             colLoc='center',
                             colColours=['lavender']*col_num,
                             rowLabels=indDf.index,
                             rowColours=['lavender']*row_num,
                             rowLoc='right',
                             # bbox=(0, 0, 1, 1),
                             # edges='horizontal',
                             loc='center')

        the_table.auto_set_font_size(False)
        the_table.set_fontsize(6)

        # the_table.scale(1, 1.5)

        # ax.text(-0.22, 0.85, str('StudioProject'),
        #         fontsize=7, color='gray',
        #         ha='left', va='bottom',
        #         transform=ax.transAxes,
        #         weight="bold", alpha=.5)

        if outputFile != None:
            plt.savefig(outputFile, bbox_inches='tight')
            if showReport == False:
                plt.close(fig)

        if showReport == True:
            plt.show()

    return indDf



# =====================================================================
def compareIndicators(dbFiles, labels, transports, actionTypes, unitIdxs, directions, interval,
                      showReport=False, ax=None, outputFile=None, mainDirection='both',
                      labelRtoL=None, labelLtoR=None, streetFunction='transit'):

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

    if streetFunction == 'transit':
        indDf1 = generateReportTransit(dbFiles[0], transports[0], actionTypes[0], unitIdxs[0], directions[0],
                                       interval, start_time, end_time, mainDirection=mainDirection,
                                       labelRtoL=labelRtoL, labelLtoR=labelLtoR)
        indDf2 = generateReportTransit(dbFiles[1], transports[1], actionTypes[1], unitIdxs[1], directions[1],
                                       interval, start_time, end_time, mainDirection=mainDirection,
                                       labelRtoL=labelRtoL, labelLtoR=labelLtoR)
    elif streetFunction == 'place':
        indDf1 = generateReportPlace(dbFiles[0], interval, start_time, end_time)
        indDf2 = generateReportPlace(dbFiles[1], interval, start_time, end_time)

    if isinstance(indDf1, str) or isinstance(indDf2, str):
        return 'Error: No observation!'

    indDf = pd.DataFrame()
    # indDf = indDf1.iloc[0:3, :].copy()

    idx1 = indDf1.index #[3:]
    idx2 = indDf2.index #[3:]

    idx2_idx1 = list(set(idx2) - set(idx1))
    idx1_idx2 = list(set(idx1) - set(idx2))

    if len(idx2_idx1) > 0:
        for idx in idx2_idx1:
            new_idx = indDf2.loc[[idx]]    #loc[idx].copy()
            new_idx[(new_idx != noDataSign) & (new_idx != 'NA')] = 0
            # indDf1 = indDf1.append(new_idx)
            indDf1 = pd.concat([indDf1, new_idx], ignore_index=False, axis=0)

    if len(idx1_idx2) > 0:
        for idx in idx1_idx2:
            new_idx = indDf1.loc[[idx]]     #.loc[idx].copy()
            new_idx[(new_idx != noDataSign) & (new_idx != 'NA')] = 0
            # indDf2 = indDf2.append(new_idx)
            indDf2 = pd.concat([indDf2, new_idx], ignore_index=False, axis=0)

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

    # ----------- Plotting the report ------------------
    if (showReport == True and ax == None) or outputFile != None:
        row_num, col_num = indDf.shape

        if showReport == False:
            plt.ioff()

        if ax == None:
            fig, ax = plt.subplots(tight_layout=True)  # , figsize=(6,2))
            fig.patch.set_visible(False)
            ax.axis('off')
            fig.set_figheight(fig.get_figheight() * (0.0450937950937951 * (row_num + 1)))
        else:
            fig = ax.get_figure()

        cellColours = pd.DataFrame()
        for i in range(indDf.shape[0]):
            for j in range(indDf.shape[1]):
                # if j == 0:
                #     norm_indDf.loc[i, j] = np.nan
                #     continue
                val_sign = str(indDf.iloc[i, j]).split(' ')[0][0]
                if val_sign == '+':
                    value = 'palegreen'
                elif val_sign == '-':
                    value = 'lightpink'
                elif val_sign == '0':
                    value = 'lightyellow'
                else:
                    value = np.nan
                cellColours.loc[i, j] = value

        the_table = ax.table(cellText=indDf.values,
                             cellLoc='center',
                             cellColours=cellColours.values,
                             colLabels=indDf.columns,
                             colLoc='center',
                             colColours=['lavender']*col_num,
                             rowLabels=indDf.index,
                             rowColours=['lavender']*row_num,
                             rowLoc='right',
                             # bbox=(0, 0, 1, 1),
                             # edges='horizontal',
                             loc='center')

        the_table.auto_set_font_size(False)
        the_table.set_fontsize(6)

        # the_table.scale(1, 1.5)

        # ax.text(-0.22, 0.85, str('StudioProject'),
        #         fontsize=7, color='gray',
        #         ha='left', va='bottom',
        #         transform=ax.transAxes,
        #         weight="bold", alpha=.5)

        if outputFile != None:
            plt.savefig(outputFile, bbox_inches='tight')
            if showReport == False:
                plt.close(fig)

        if showReport == True:
            plt.show()


    return indDf


# =====================================================================
def plotTrajectory(trjDBFile, intrinsicCameraMatrix, distortionCoefficients, homographyFile, ax, session):
    objects = storage.loadTrajectoriesFromSqlite(trjDBFile, 'object')
    homography = np.loadtxt(homographyFile, delimiter=' ')
    traj_line = {}
    for traj in objects:
        xy_arr = traj.positions.asArray()
        x = xy_arr[0]
        y = xy_arr[1]
        userType = traj.getUserType()
        line, = ax.plot(x, y, color=userTypeColors[userType], lw=0.3, label=userTypeNames[userType],
                        marker = 'o', markersize=0.3)
        traj_line[str(traj.getNum())] = [traj, line]

    q_line = session.query(Line)
    q_zone = session.query(Zone)

    if q_line.all() != []:
        for line in q_line:
            x_list = [p.x for p in line.points]
            y_list = [p.y for p in line.points]

            points = np.array([x_list, y_list], dtype = np.float64)
            prj_points = imageToWorldProject(points, intrinsicCameraMatrix, distortionCoefficients, homography)
            ax.plot(prj_points[0], prj_points[1], lw=0.4)

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
            zone = Polygon(prj_xy, fc=fc, ec=ec, lw=0.3)
            ax.add_patch(zone)

    # Invert the y-axis to convert to image coordinate system
    ax.invert_yaxis()

    ax.axis('equal')
    ax.tick_params(axis='both', labelsize=3)
    handles, labels = ax.get_legend_handles_labels()
    handle_list = []
    label_list = []
    for i, label in enumerate(labels):
        if not label in label_list:
            handle_list.append(handles[i])
            label_list.append(label)
    ax.legend(handle_list, label_list, loc='upper left', prop={'size': 3})

    return traj_line


# =====================================================================
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

# =====================================================================
def batchPlots(metaDataFile, outputFolder, site = 'all', camView = 'all', labelRtoL=None, labelLtoR=None):
    plt.ioff()
    # fig = plt.figure(tight_layout=True)  # figsize=(5, 5), dpi=200, tight_layout=True)
    # ax = fig.add_subplot(111)
    transportType = ['driving', 'walking', 'cycling']
    actionType = ['crossing_line', 'crossing_line_RL', 'crossing_line_LR',
                  'crossing_zone', 'entering_zone', 'exiting_zone',
                  'all_crossings']
    directionTypes = ['both', 'Right to left', 'Left to right']
    attrTransitList = ['age', 'gender', 'category']
    attrActivityList = ['age', 'gender', 'activity']

    con = sqlite3.connect(metaDataFile)
    cur = con.cursor()

    # ====================== Check if database is a metadata file ====================
    cur.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='video_sequences' ''')
    if cur.fetchone()[0] == 0:
        return 'The selected database is NOT a metadata file! Select a proper file.'

    # ======================= Retrieve sites and camera views =========================
    mainDirections = {}
    if site == 'all':
        cur.execute('SELECT name, description FROM sites')
    else:
        cur.execute('SELECT name, description FROM sites WHERE name=?', (site,))
    sites_dirs = cur.fetchall()
    site = [s[0] for s in sites_dirs]
    direc = [s[1] for s in sites_dirs]

    if site == []:
        return 'Error: No site is selected!'
    for i, s in enumerate(site):
        mainDirections[s] = direc[i]

    site_camView = {}

    for s in site:
        site_camView[s] = {}
        if camView == 'all':
            cur.execute('SELECT idx FROM sites WHERE name=?', (s,))
            siteIdx = cur.fetchall()[0][0]
            cur.execute('SELECT description, homographyFilename FROM camera_views WHERE siteIdx=?', (siteIdx,))
            views = cur.fetchall()
            view = [[v[0], v[1]] for v in views]

            for v in view:
                site_camView[s][v[0]] = Path(metaDataFile).parent/s/Path(v[1]).parent
        else:
            cur.execute('SELECT idx FROM sites WHERE name=?', (s,))
            siteIdx = cur.fetchall()[0][0]
            cur.execute('SELECT homographyFilename FROM camera_views WHERE siteIdx=? AND description=?',
                        (siteIdx, camView))
            homoFile = cur.fetchall()

            site_camView[s][camView] = Path(metaDataFile).parent/s/Path(homoFile[0][0]).parent

    # ========================== FUNCTION Folders ==========================
    transit_path = f'{outputFolder}/Transit'
    access_path = f'{outputFolder}/Access'
    place_path = f'{outputFolder}/Place'

    # ---------------------- ACROSS ALL SITES Folders ----------------------
    allSitesTransit_path = f'{transit_path}/Across all sites'
    allSitesAccess_path = f'{access_path}/Across all sites'
    allSitesPlace_path = f'{place_path}/Across all sites'

    # ========================== Making the folders ========================
    Path(allSitesTransit_path).mkdir(parents=True, exist_ok=True)
    Path(allSitesAccess_path).mkdir(parents=True, exist_ok=True)
    Path(allSitesPlace_path).mkdir(parents=True, exist_ok=True)

    vehicleDbfileList = []
    vehicleSiteNames = []
    vehicleDirections = []

    walkCycDbfileList = []
    walkCycSiteNames = []
    walkCycDirections = []

    for site in site_camView.keys():

        # ======================== Making TRANSIT Folders ========================
        transitCount_path = f'{transit_path}/{site}/Number of users over time'
        transitCountAllmodes_path = f'{transitCount_path}/All modes'
        Path(transitCountAllmodes_path).mkdir(parents=True, exist_ok=True)
        transitSpeed_path = f'{transit_path}/{site}/Speed of users over time'

        # ========================== ACCESS Folders ==========================
        accessCount_path = f'{access_path}/{site}/Number of users over time'

        # ========================== PLACE Folders ==========================
        activitiesCount_path = f'{place_path}/{site}/Number of activities over time'
        # Path(transit_path).mkdir(parents=True, exist_ok=True)

        # ========================== Creat Folders ==========================
        for transport in transportType:
            transitCountMode_path = f'{transitCount_path}/{transport}'
            Path(transitCountMode_path).mkdir(parents=True, exist_ok=True)

            transitSpeedMode_path = f'{transitSpeed_path}/{transport}'
            Path(transitSpeedMode_path).mkdir(parents=True, exist_ok=True)

            accessCountMode_path = f'{accessCount_path}/{transport}'
            Path(accessCountMode_path).mkdir(parents=True, exist_ok=True)


        dbFiles = []
        labels = []
        for view in site_camView[site].keys():
            dbFilePath = site_camView[site][view]/f'{site}.sqlite'
            if dbFilePath.exists():
                # Path(outputFolder + '/' + site).mkdir(exist_ok=True)
                dbFiles.append(str(dbFilePath))
                labels.append(str(view).capitalize())

                current_session = connectDatabase(str(dbFilePath))
                unitIdx_line = [[str(id[0]), id[1].name]
                                for id in current_session.query(Line.idx, Line.type).all()]
                if len(unitIdx_line) > 1:
                    unitIdx_line.insert(0, ['all_lines', 'all_types'])

                unitIdx_zone = [[str(id[0]), id[1].name]
                                for id in current_session.query(Zone.idx, Zone.type).all()]
                if len(unitIdx_zone) > 1:
                    unitIdx_zone.insert(0, ['all_zones', 'all_types'])

                unitIdx_all = [['all_units', 'all_types']]

            else:
                continue

        if dbFiles == []:
            continue

        for dir in ['South', 'North']:
            vehicleDbfileList.append(dbFiles)
            vehicleSiteNames.append(site.capitalize() + f' ({dir[0]})')

        walkCycDbfileList.append(dbFiles)
        walkCycSiteNames.append(site.capitalize())

        # ++++++++++++++++++++++ PDF all modes plots ++++++++++++++++++++++
        fig = plt.figure(tight_layout=True)
        fig.set_figheight(5)
        fig.set_figwidth(15)
        axs = fig.subplots(1, 2, sharey='row')
        for i, dbFile in enumerate(dbFiles):
            # fig, ax = plt.subplots(tight_layout=True)
            if i == 0:
                YlabSize = 12
            else:
                YlabSize = 0
            err = transportModePDF([dbFile]*2, ['Pedestrian', 'Cyclist'],
                                   ['walking', 'cycling'],
                                   ['all_crossings', 'all_crossings'],
                                   ['all_units', 'all_units'],
                                   ['both', 'both'],
                                   ax=axs[i],
                                   siteName=f'{site.capitalize()} ({labels[i]})',
                                   colors=[userTypeColors[2], userTypeColors[4]],
                                   titleSize=14, xLabelSize=12, yLabelSize=YlabSize, xTickSize=8, yTickSize=8,
                                   legendFontSize=10)
        if err == None:
            plt.savefig(f'{transitCountAllmodes_path}/PDF_All-modes_' + '-'.join(labels) + f'_{site.capitalize()}.pdf') #{labels[i].capitalize()}
        plt.close(fig)

        # ========================== PLACE FUNCTION ==========================
        Path(activitiesCount_path).mkdir(parents=True, exist_ok=True)
        for attr in attrActivityList:
            fig, ax = plt.subplots(tight_layout=True)
            err = stackedAllActivities(dbFiles, labels, attr, ax=ax, interval=60, textRotation=0, titleSize=12,
                                       xLabelSize=12, yLabelSize=12, xTickSize=5, yTickSize=8, legendFontSize=10)
            if err == None:
                plt.savefig(f'{activitiesCount_path}/Activities_by-{attr}_{site.capitalize()}.pdf')
            plt.close(fig)

        # +++++++++++++++ Histogram of each activity (shopping) ++++++++++++++++
        fig, ax = plt.subplots(tight_layout=True)
        err = HistActivity(dbFiles, labels, 'shopping', ax=ax, interval=30, colors=plotColors,
                                  siteName=site.capitalize(),
                                  titleSize=12, xLabelSize=12, yLabelSize=12, xTickSize=5, yTickSize=8,
                                  legendFontSize=10, textRotation=0)
        if err == None:
            plt.savefig(f'{activitiesCount_path}/Activities_Shopping_{site.capitalize()}.pdf')
        plt.close(fig)

        # +++++++++++++++ Stacked Histogram of each activity (shopping) ++++++++++++++++
        for attr in ['age', 'gender']:
            fig, ax = plt.subplots(tight_layout=True)
            err = stackedActivity(dbFiles, labels, 'shopping', attr, ax=ax, interval=30,
                               siteName=site.capitalize(),
                               titleSize=12, xLabelSize=12, yLabelSize=12, xTickSize=5, yTickSize=8,
                               legendFontSize=10, textRotation=0)
            if err == None:
                plt.savefig(f'{activitiesCount_path}/Activities_Shopping_By_{attr}_{site.capitalize()}.pdf')
            plt.close(fig)

        # ++++++++++++++++++++++ Place indicator reports ++++++++++++++++++++++
        for i, dbFile in enumerate(dbFiles):
            outputFile = f'{activitiesCount_path}/Table_{labels[i]}_Activities_{site.capitalize()}.pdf'
            generateReportPlace(dbFile, 60, outputFile=outputFile)

        # -------------------- Place indicator Difference ---------------------
        outputFile = f'{activitiesCount_path}/Diff-Table_Activities_{site.capitalize()}.pdf'
        compareIndicators(dbFiles, labels, ['Activity', 'Activity'], [actionType[0], actionType[0]],
                          ['all_lines', 'all_lines'], ['both', 'both'], 60,
                          outputFile=outputFile, mainDirection=mainDirections[site],
                          labelRtoL='south', labelLtoR='north', streetFunction='place')

        # ====================== Pie chart, Activity TYPE, AGE, GENDER  ==========================
        for attr in ['activity', 'age', 'gender']:
            fig = plt.figure(tight_layout=True)
            fig.set_figheight(5)
            fig.set_figwidth(10)
            axs = fig.subplots(1, 2)

            err = pieChart(dbFiles, labels, 'Activity', attr, axs=axs,
                           siteName=site.capitalize(),
                           titleSize=14, percTextSize=12, labelSize=12)

            if err == None:
                plt.savefig(
                    f'{activitiesCount_path}/Pie_{attr.capitalize()}_' + '-'.join(labels) + f'_{site.capitalize()}.pdf')
            plt.close(fig)

        # ========================= Sankey Diagram, Activity ========================
        for dbFile, label in zip(dbFiles, labels):
            outFile = f'{activitiesCount_path}/Sankey_Activity_Age-Gender_{label}_{site.capitalize()}.pdf'
            sankeyPlotActivity(dbFile, outFile, siteName= f'{site.capitalize()} ({label})')


        # ========================== Sankey Diagram, Transit =========================
        for dbFile, label in zip(dbFiles, labels):
            outFile = f'{transitCountAllmodes_path}/Sankey_Transit_Age-Gender_{label}_{site.capitalize()}.pdf'
            sankeyPlotTransit(dbFile, 'all_crossings', 'all_units', outFile, siteName= f'{site.capitalize()} ({label})')

        # ========================== Pie chart, MODE SHARE  ==========================
        fig = plt.figure(tight_layout=True)
        fig.set_figheight(5)
        fig.set_figwidth(10)
        axs = fig.subplots(1, 2)

        err = pieChart(dbFiles, labels, 'all_modes', 'transport', axs=axs,
                       siteName=site.capitalize(),
                       titleSize=14, percTextSize=12, labelSize=12)

        if err == None:
            plt.savefig(
                f'{transitCountAllmodes_path}/Pie_Mode-share_' + '-'.join(labels) + f'_{site.capitalize()}.pdf')
        plt.close(fig)

        # ========================== Pie chart, VEHICLE Type  ==========================
        fig = plt.figure(tight_layout=True)
        fig.set_figheight(5)
        fig.set_figwidth(10)
        axs = fig.subplots(1, 2)

        err = pieChart(dbFiles, labels, 'cardriver', 'category', axs=axs, siteName=site.capitalize(),
                       titleSize=14, percTextSize=12, labelSize=12)
        if err == None:
            plt.savefig(
                f'{transitCount_path}/cardriver/Pie_Vehicle-type_' + '-'.join(labels) + f'_{site.capitalize()}.pdf')
        plt.close(fig)

        # ========================== Pie chart, PEDESTRIAN age  ==========================
        fig = plt.figure(tight_layout=True)
        fig.set_figheight(5)
        fig.set_figwidth(10)
        axs = fig.subplots(1, 2)

        err = pieChart(dbFiles, labels, 'walking', 'age', axs=axs,
                       siteName=site.capitalize(),
                       titleSize=14, percTextSize=12, labelSize=12)
        if err == None:
            plt.savefig(
                f'{transitCount_path}/walking/Pie_Pedestrian-age_' + '-'.join(labels) + f'_{site.capitalize()}.pdf')
        plt.close(fig)

        # ========================== Pie chart, PEDESTRIAN gender  ==========================
        fig = plt.figure(tight_layout=True)
        fig.set_figheight(5)
        fig.set_figwidth(10)
        axs = fig.subplots(1, 2)

        err = pieChart(dbFiles, labels, 'walking', 'gender', axs=axs,
                       siteName=site.capitalize(),
                       titleSize=14, percTextSize=12, labelSize=12)
        if err == None:
            plt.savefig(
                f'{transitCount_path}/walking/Pie_Pedestrian-gender_' + '-'.join(labels) + f'_{site.capitalize()}.pdf')
        plt.close(fig)

        # ++++++++++++++++++ Density of all street users in Zones ++++++++++++++++++++++
        fig, ax = plt.subplots(tight_layout=True)
        err = zoneDensityPlot(dbFiles, labels, ['all_modes']* len(dbFiles), ['1'] * len(dbFiles), zoneArea=345,
                              ax=ax, interval=1, colors=plotColors,
                              siteName=site.capitalize(),
                              titleSize=14, xLabelSize=12, yLabelSize=12, xTickSize=8, yTickSize=8,
                              legendFontSize=10)
        if err == None:
            plt.savefig(
                f'{transitCountAllmodes_path}/Density_All-modes_' + '-'.join(labels) + f'_{site.capitalize()}.pdf')
        plt.close(fig)

        # ++++++++++++++++++ Cumulative sum of all street users enter/exit in Zones ++++++++++++++++++++++
        fig, ax = plt.subplots(tight_layout=True)
        err = cumEnterExitPlot(dbFiles, labels, ['all_modes'] * len(dbFiles), ['1'] * len(dbFiles),
                              ax=ax, siteName=site.capitalize(), colors=plotColors,
                              titleSize=12, xLabelSize=12, yLabelSize=12, xTickSize=8, yTickSize=8,
                              legendFontSize=10)
        if err == None:
            plt.savefig(
                f'{transitCountAllmodes_path}/Cumulative-sum_All-modes_' + '-'.join(labels) + f'_{site.capitalize()}.pdf')
        plt.close(fig)

        # ++++++++++++++++++ Number of all street users over time ++++++++++++++++++++++
        fig, ax = plt.subplots(tight_layout=True)
        err = tempDistHist(dbFiles, labels, ['all_modes'] * len(dbFiles), ['all_crossings'] * len(dbFiles),
                           ['all_units'] * len(dbFiles),
                           ax=ax, interval=10, drawStd=1,
                              siteName=site.capitalize(),
                              titleSize=14, xLabelSize=12, yLabelSize=12, xTickSize=8, yTickSize=8,
                              legendFontSize=10)
        if err == None:
            plt.savefig(
                f'{transitCountAllmodes_path}/Number_of_All-modes_' + '-'.join(labels) + f'_{site.capitalize()}.pdf')
        plt.close(fig)


        #--------------------------------------------------------------------
        for transport in transportType:
            transports = [transport] * len(dbFiles)

            # transitCountMode_path = f'{transitCount_path}/{transport}'
            # Path(transitCountMode_path).mkdir(parents=True, exist_ok=True)
            #
            # accessCountMode_path = f'{accessCount_path}/{transport}'
            # Path(accessCountMode_path).mkdir(parents=True, exist_ok=True)

            # if transport == 'cardriver':
            #     transitSpeedMode_path = f'{transitSpeed_path}/{transport}'
            #     Path(transitSpeedMode_path).mkdir(parents=True, exist_ok=True)

            # ++++++++++++++++++ Density of pedestrians / cyclists in Zones ++++++++++++++++++++++
            fig, ax = plt.subplots(tight_layout=True)
            err = zoneDensityPlot(dbFiles, labels, transports, ['1']*len(dbFiles), zoneArea=345,
                                   ax=ax, interval=1, colors=plotColors,
                                  siteName=site.capitalize(),
                                  titleSize=14, xLabelSize=12, yLabelSize=12, xTickSize=8, yTickSize=8,
                                   legendFontSize=10)
            if err == None:
                plt.savefig(
                    f'{transitCount_path}/{transport}/Density_' + '-'.join(
                        labels) + f'_{transport}_{site.capitalize()}.pdf')
            plt.close(fig)

            # ++++++++++++++++++ Cumulative sum of pedestrians / cyclists in Zones ++++++++++++++++++++++
            fig, ax = plt.subplots(tight_layout=True)
            err = cumEnterExitPlot(dbFiles, labels, transports, ['1'] * len(dbFiles),
                                  ax=ax, siteName=site.capitalize(), colors=plotColors,
                                  titleSize=12, xLabelSize=12, yLabelSize=12, xTickSize=8, yTickSize=8,
                                  legendFontSize=10)
            if err == None:
                plt.savefig(
                    f'{transitCount_path}/{transport}/Cumulative-sum_' + '-'.join(
                        labels) + f'_{transport}_{site.capitalize()}.pdf')
            plt.close(fig)

            # ++++++++++++++++++++++ PDF all observed users Before-vs-After ++++++++++++++++++++++
            fig, ax = plt.subplots(tight_layout=True)
            err = transportModePDF(dbFiles, labels, transports,
                                   ['all_crossings', 'all_crossings'],
                                   ['all_units', 'all_units'],
                                   ['both', 'both'],
                                   ax=ax, colors=plotColors,
                                   siteName=site.capitalize(),
                                   titleSize=14, xLabelSize=12, yLabelSize=12, xTickSize=8, yTickSize=8,
                                   legendFontSize=10)
            if err == None:
                plt.savefig(
                    f'{transitCount_path}/{transport}/PDF_' + '-'.join(labels) + f'_All-observed-{transport}_{site.capitalize()}.pdf')
            plt.close(fig)

            # ++++++++++++++++++++++ TRANSIT Stacked plots ++++++++++++++++++++++
            for attr in attrTransitList:
                fig, ax = plt.subplots(tight_layout=True)
                err = stackedHistTransport(dbFiles, labels, transports, ['all_crossings', 'all_crossings'],
                                   ['all_units', 'all_units'], ['both', 'both'], attr, ax=ax, interval=60,
                                           siteName=site.capitalize(),
                                           titleSize=14, xLabelSize=12, yLabelSize=12, xTickSize=5, yTickSize=8,
                                           legendFontSize=10)
                if err == None:
                    plt.savefig(
                        f'{transitCount_path}/{transport}/Stacked_All-units_{transport}_by-{attr}_{site.capitalize()}.pdf')
                plt.close(fig)

            # ++++++++++++++++++++++ Transit indicator reports ++++++++++++++++++++++
            for i, dbFile in enumerate(dbFiles):
                if transport == 'cycling':
                    acType = 'crossing_zone'
                    uId = 'all_zones'
                elif transport == 'walking':
                    acType = 'all_crossings'
                    uId = 'all_units'
                elif transport == 'driving':
                    acType = 'crossing_line'
                    uId = 'all_lines'
                outputFile = f'{transitCount_path}/{transport}/Table_{labels[i]}_{transport}_{acType}_{uId}_{site.capitalize()}.pdf'
                generateReportTransit(dbFile, transport, acType, uId, 'both', 60, outputFile=outputFile,
                                      mainDirection=mainDirections[site], labelRtoL='south', labelLtoR='north')

            # ------------------ Transit indicator Difference ----------------------
            if transport == 'cycling':
                acType = 'crossing_zone'
                uId = 'all_zones'
            elif transport == 'walking':
                acType = 'all_crossings'
                uId = 'all_units'
            elif transport == 'driving':
                acType = 'crossing_line'
                uId = 'all_lines'
            outputFile = f'{transitCount_path}/{transport}/Diff-Table_{transport}_{acType}_{uId}_{site.capitalize()}.pdf'
            compareIndicators(dbFiles, labels, transports, [acType, acType],  [uId, uId],
                              ['both', 'both'], 60,
                              outputFile=outputFile, mainDirection=mainDirections[site],
                              labelRtoL='south', labelLtoR='north')

                # elif transport == 'cardriver':
                #     for direction in directionTypes:
                #         outputFile = f'{transitCount_path}/{transport}/Table_{labels[i]}_{transport}_{direction}_{site.capitalize()}.pdf'
                #         generateReport(dbFile, transport, actionType[0], 'all_lines', direction, 120,
                #                        outputFile=outputFile, mainDirection=mainDirections[site],
                #                        labelRtoL='south', labelLtoR='north')

            # ------------------------------------------------------------------
            for action in actionType:
                actions = [action]*len(dbFiles)

                if 'line' in action.split('_'):
                    unitIdx_list = unitIdx_line
                elif 'zone' in action.split('_'):
                    unitIdx_list = unitIdx_zone
                elif action == 'all_crossings':
                    unitIdx_list = unitIdx_all

                for unitIdx in unitIdx_list:
                    unitIdxs = [unitIdx[0]]*len(dbFiles)

                    if 'zone' in action.split('_') and transport == 'cardriver' and unitIdx[0] == 'on_street_parking_lot':
                        fig, ax = plt.subplots(tight_layout=True)
                        err = tempDistHist(dbFiles, labels, transports, actions,
                                           unitIdxs, ax=ax, interval=30, siteName=site.capitalize())
                        if err == None:
                            plt.savefig(
                                f'{accessCount_path}/{transport}/Zone_{unitIdx[0]}_{unitIdx[1]}_{action}_{transport}_{site.capitalize()}.pdf')
                        plt.close(fig)
                        continue

                    # for direction in directionTypes:
                    #     directions = [direction]*len(dbFiles)

                    # --------------- Number of Users Over Time ------------------------
                    fig, ax = plt.subplots(tight_layout=True)
                    err = tempDistHist(dbFiles, labels, transports, actions,
                                       unitIdxs, ['both']*len(dbFiles), ax, 10,
                                       siteName=site.capitalize(),
                                       drawStd=1,
                                       titleSize=14, xLabelSize=12, yLabelSize=12, xTickSize=8, yTickSize=8,
                                       legendFontSize=10)
                    if err == None:
                        if unitIdx[1] == 'adjoining_ZOI':
                            save_path = f'{accessCount_path}/{transport}'
                        else:
                            save_path = f'{transitCount_path}/{transport}'

                        # if 'line' in action.split('_'):
                        plt.savefig(
                            f'{save_path}/{actions[0]}-{unitIdx[0]}-{unitIdx[1]}-{transport}-{site.capitalize()}.pdf')

                    plt.close(fig)

                    # --------------- Speed of Users Over Time ------------------------
                    # +++++++++++++++ Speed Probability density function ++++++++++++++
                    fig, ax = plt.subplots(tight_layout=True)

                    err = speedHistogram(dbFiles, labels, transports, actions,
                                       unitIdxs, ['both']*len(dbFiles), ax, 30,
                                         siteName=site.capitalize(),
                                         titleSize=14, xLabelSize=12, yLabelSize=12, xTickSize=8,
                                         yTickSize=8, legendFontSize=10)
                    if err == None:
                        plt.savefig(
                            f'{transitSpeed_path}/{transport}/PDF-Speed-{actions[0]}-{unitIdx[0]}-{transport}-{site.capitalize()}.pdf')
                    plt.close(fig)

                    # +++++++++++++++++++++++++ Speed Box Plot ++++++++++++++++++++++++
                    fig, ax = plt.subplots(tight_layout=True)
                    err = speedBoxPlot(dbFiles, labels, transports, actions,
                                         unitIdxs, ['both']*len(dbFiles), ax, 60,
                                       siteName=site.capitalize(),
                                       titleSize=14, xLabelSize=12, yLabelSize=12, xTickSize=7, yTickSize=8,
                                       legendFontSize=10)
                    if err == None:
                        plt.savefig(
                            f'{transitSpeed_path}/{transport}/Box-Speed-{actions[0]}-{unitIdx[0]}-{transport}-{site.capitalize()}.pdf')
                    plt.close(fig)

    for i in range(len(walkCycSiteNames)):
        vehicleDirections.append('Right to left')
        vehicleDirections.append('Left to right')
        walkCycDirections.append('both')

    # ================= Flow of users across all sites ============================
    fig, ax = plt.subplots(tight_layout=True)
    err = sitesBAtransport(vehicleDbfileList, vehicleSiteNames, 'cardriver', vehicleDirections, ax=ax,
                           titleSize=14, xLabelSize=11, yLabelSize=11, xTickSize=8, yTickSize=8,
                           legendFontSize=10)
    if err == None:
        plt.savefig(f'{allSitesTransit_path}/Flow-vehicles_' + '-'.join(labels) + f'_All-sites.pdf')
    plt.close(fig)

    for transit in ['walking', 'cycling']:
        fig, ax = plt.subplots(tight_layout=True)
        err = sitesBAtransport(walkCycDbfileList, walkCycSiteNames, transit, walkCycDirections, ax=ax,
                               titleSize=14, xLabelSize=11, yLabelSize=11, xTickSize=8, yTickSize=8,
                               legendFontSize=10)
        if err == None:
            plt.savefig(f'{allSitesTransit_path}/Flow-{transit}_' + '-'.join(labels) + f'_All-sites.pdf')
        plt.close(fig)

    # =================== Number of vehicles over time across all sites =============
    vehicleDbfilesBefore = [i[0] for i in vehicleDbfileList]
    vehicleDbfilesAfter = [i[1] for i in vehicleDbfileList]

    # fig, ax = plt.subplots(tight_layout=True)
    fig = plt.figure(tight_layout=True)
    fig.set_figheight(5)
    fig.set_figwidth(15)
    axs = fig.subplots(1, 2, sharey='row')
    err = tempDistHist(vehicleDbfilesBefore, vehicleSiteNames, ['cardriver']*len(vehicleSiteNames),
                       ['crossing_line']*len(vehicleSiteNames), ['all_lines']*len(vehicleSiteNames),
                       vehicleDirections, axs[0], 20, siteName=f'all sites ({labels[0]})', drawMean=False,
                       titleSize=14, xLabelSize=11, yLabelSize=11, xTickSize=8, yTickSize=8, legendFontSize=10)

    # if err == None:
    #     plt.savefig(f'{allSitesTransit_path}/No-vehicles_Before_All-sites.pdf')
    # plt.close(fig)
    #
    # fig, ax = plt.subplots(tight_layout=True)
    err = tempDistHist(vehicleDbfilesAfter, vehicleSiteNames, ['cardriver'] * len(vehicleSiteNames),
                       ['crossing_line'] * len(vehicleSiteNames), ['all_lines'] * len(vehicleSiteNames),
                       vehicleDirections, axs[1], 20, siteName=f'all sites ({labels[1]})', drawMean=False,
                       titleSize=14, xLabelSize=11, yLabelSize=0, xTickSize=8, yTickSize=8, legendFontSize=10)
    if err == None:
        plt.savefig(f'{allSitesTransit_path}/No-vehicles_' + '-'.join(labels) + f'_All-sites.pdf')
    plt.close(fig)

    # =================== Number of pedestrians and cyclists over time across all sites =============
    walkCycDbfileBefore = [i[0] for i in walkCycDbfileList]
    walkCycDbfileAfter = [i[1] for i in walkCycDbfileList]

    for transit in ['walking', 'cycling']:
        # fig, ax = plt.subplots(tight_layout=True)
        fig = plt.figure(tight_layout=True)
        fig.set_figheight(5)
        fig.set_figwidth(15)
        axs = fig.subplots(1, 2, sharey='row')
        err = tempDistHist(walkCycDbfileBefore, walkCycSiteNames, [transit] * len(walkCycSiteNames),
                           ['all_crossings'] * len(walkCycSiteNames), ['all_units'] * len(walkCycSiteNames),
                           walkCycDirections, axs[0], 20, siteName=f'all sites ({labels[0]})', drawMean=False,
                           titleSize=14, xLabelSize=11, yLabelSize=11, xTickSize=8, yTickSize=8, legendFontSize=10)

        err = tempDistHist(walkCycDbfileAfter, walkCycSiteNames, [transit] * len(walkCycSiteNames),
                           ['all_crossings'] * len(walkCycSiteNames), ['all_units'] * len(walkCycSiteNames),
                           walkCycDirections, axs[1], 20, siteName=f'all sites ({labels[1]})', drawMean=False,
                           titleSize=14, xLabelSize=11, yLabelSize=0, xTickSize=8, yTickSize=8, legendFontSize=10)
        if err == None:
            plt.savefig(f'{allSitesTransit_path}/No-{transit}_' + '-'.join(labels) + f'_All-sites.pdf')
        plt.close(fig)

    # for transit in ['walking', 'cycling']:
    #     fig, ax = plt.subplots(tight_layout=True)
    #     err = tempDistHist(walkCycDbfileAfter, walkCycSiteNames, [transit] * len(walkCycSiteNames),
    #                        ['crossing line'] * len(walkCycSiteNames), ['all_lines'] * len(walkCycSiteNames),
    #                        walkCycDirections, ax, 20, siteName='all sites (After)', drawMean=False,
    #                        titleSize=14, xLabelSize=11, yLabelSize=11, xTickSize=8, yTickSize=8, legendFontSize=10)
    #     if err == None:
    #         plt.savefig(f'{allSitesTransit_path}/No-{transit}_After_All-sites.pdf')
    #     plt.close(fig)


    # ===================== South v.s North in Before and After ==============================
    for site in site_camView.keys():
        for view in site_camView[site]:
            dbFilePath = site_camView[site][view]/f'{site}.sqlite'
            if dbFilePath.exists():
                dbFiles = [str(dbFilePath), str(dbFilePath)]
            else:
                continue

            fig, ax = plt.subplots(tight_layout=True)
            err = tempDistHist(dbFiles, ['South', 'North'], ['cardriver', 'cardriver'],
                               ['crossing_line', 'crossing_line'], ['all_lines', 'all_lines'],
                               ['Right to left', 'Left to right'],
                               ax=ax, interval=30, siteName=f'{site.capitalize()} ({view.capitalize()})',
                               titleSize=14, xLabelSize=11, yLabelSize=11, xTickSize=8, yTickSize=8, legendFontSize=10)
            if err == None:
                plt.savefig(
                    f'{transit_path}/{site}/Number of users over time/cardriver/South-vs-North_{view}_Vehicles_{site.capitalize()}.pdf')
            plt.close(fig)

            # ++++++++++++++++++++++ PDF South v.s North in Before and After ++++++++++++++++++++++
            fig, ax = plt.subplots(tight_layout=True)
            err = transportModePDF(dbFiles, ['South', 'North'], ['cardriver', 'cardriver'],
                                   ['crossing_line', 'crossing_line'], ['all_lines', 'all_lines'],
                                   ['Right to left', 'Left to right'],
                                   ax=ax,
                                   siteName=f'{site.capitalize()} ({view.capitalize()})',
                                   colors=plotColors,
                                   titleSize=14, xLabelSize=12, yLabelSize=12, xTickSize=8, yTickSize=8,
                                   legendFontSize=10)
            if err == None:
                plt.savefig(
                    f'{transit_path}/{site}/Number of users over time/cardriver/PDF_South-vs-North_{view}_Vehicles_{site.capitalize()}.pdf')
            plt.close(fig)

        # ++++++++++++++++++++++ PDF Before v.s After in South and North  ++++++++++++++++++++++
        dbFiles = []
        labels = []
        for view in site_camView[site]:
            dbFilePath = site_camView[site][view] /f'{site}.sqlite'
            if dbFilePath.exists():
                dbFiles.append(str(dbFilePath))
                labels.append(view)
            else:
                continue
        if len(dbFiles) < 2:
            continue
        for dir in ['Right to left', 'Left to right']:
            fig, ax = plt.subplots(tight_layout=True)
            err = transportModePDF(dbFiles, labels, ['cardriver', 'cardriver'],
                                   ['crossing_line', 'crossing_line'], ['all_lines', 'all_lines'],
                                   [dir, dir],
                                   ax=ax,
                                   siteName=site.capitalize(),
                                   colors=plotColors,
                                   titleSize=14, xLabelSize=12, yLabelSize=12, xTickSize=8, yTickSize=8,
                                   legendFontSize=10)

            if err == None:
                if dir == 'Right to left':
                    d = 'South'
                else:
                    d = 'North'
                plt.savefig(
                    f'{transit_path}/{site}/Number of users over time/cardriver/PDF_' + '-'.join(labels) + f'_{d}_Vehicles_{site.capitalize()}.pdf')
            plt.close(fig)


    # ------------------- Activities ACROSS ALL SITES --------------------------
    fig, ax = plt.subplots(tight_layout=True)
    err = sitesBAactivity(walkCycDbfileList, walkCycSiteNames, ax=ax,
                          titleSize=14, xLabelSize=12, yLabelSize=12, xTickSize=8, yTickSize=8,
                          legendFontSize=10)
    if err == None:
        plt.savefig(f'{allSitesPlace_path}/Rate-activities_' + '-'.join(labels) + f'_All_sites.pdf')
    plt.close(fig)


    print('Done! .....')

# from indicators import batchPlots
# from pathlib import Path
# def rm_tree(pth):
#     pth = Path(pth)
#     for child in pth.glob('*'):
#         if child.is_file():
#             child.unlink()
#         else:
#             rm_tree(child)
#     pth.rmdir()
# metaDataFile = '/Users/abbas/Documents/PhD/video_files/metadata.sqlite'
# outputFolder = '/Users/abbas/Desktop/plots'
# if Path(outputFolder).exists():
#     rm_tree(outputFolder)
# batchPlots(metaDataFile, outputFolder)

# =====================================================================
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


# =====================================================================
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
        fig = plt.figure(tight_layout=True)
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
            labels1, sizes1 = getLabelSizePie('all_modes', 'transport', startTime1, endTime1, sessions[i])
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

        watermark(ax[i])
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


# ===================================================================
def zoneDensityPlot(dbFiles, labels, transports, unitIdxs, zoneArea, ax=None, interval=20, alpha=1,
                    colors=plotColors, siteName=None, drawMean=True, smooth=False,
                    titleSize=8, xLabelSize=8, yLabelSize=8, xTickSize=8, yTickSize=7, legendFontSize=6):

    inputNo = len(dbFiles)
    sessions = []
    first_obs_times = []
    last_obs_times = []

    for i in range(inputNo):
        session = connectDatabase(dbFiles[i])
        sessions.append(session)

        fobst, lobst = getObsStartEnd(session)
        first_obs_times.append(fobst.time())
        last_obs_times.append(lobst.time())

        # cls_obs = ZoneCrossing
        #
        # first_obs_time = session.query(func.min(cls_obs.instant)).first()[0]
        # last_obs_time = session.query(func.max(cls_obs.instant)).first()[0]
        #
        # first_obs_times.append(first_obs_time.time())
        # last_obs_times.append(last_obs_time.time())

    actionTypes_entries = ['entering_zone'] * inputNo
    query_list_entries = getQueryList(dbFiles, transports, actionTypes_entries, unitIdxs)
    if isinstance(query_list_entries, str):
        return query_list_entries
    entries_lists = getTimeLists(query_list_entries, actionTypes_entries)

    actionTypes_exits = ['exiting_zone'] * inputNo
    query_list_exits = getQueryList(dbFiles, transports, actionTypes_exits, unitIdxs)
    if isinstance(query_list_exits, str):
        return query_list_exits
    exits_lists = getTimeLists(query_list_exits, actionTypes_exits)


    # entries_lists = []
    # exits_lists = []
    # for i in range(inputNo):
    #     q = sessions[i].query(ZoneCrossing.instant).filter(ZoneCrossing.zoneIdx == unitIdxs[i])
    #
    #     q = q.join(Zone, Zone.idx == ZoneCrossing.lineIdx) \
    #         .join(GroupBelonging, GroupBelonging.groupIdx == ZoneCrossing.groupIdx) \
    #         .join(Person, Person.idx == GroupBelonging.personIdx) \
    #         .join(Mode, Mode.personIdx == Person.idx)
    #
    #     if transports[i] != 'all_modes':
    #         q = q.filter(Mode.transport == transports[i])
    #
    #         if transports[i] != 'walking':
    #             q = q.join(Vehicle, Vehicle.idx == Mode.vehicleIdx)
    #
    #         if transports[i] == 'cardriver':
    #             q = q.filter(Zone.type == 'roadbed')
    #             # .filter(Vehicle.category == 'car')
    #
    #     if unitIdxs[i] == 'all_zones':
    #         q = q.group_by(Person.idx)
    #
    #     q_entry = q.filter(ZoneCrossing.entering == True)
    #     q_exit = q.filter(ZoneCrossing.entering == False)
    #
    #     entries_lists.append([i[0] for i in q_entry.all()])
    #     exits_lists.append([i[0] for i in q_exit.all()])

    if all([i == [] for i in entries_lists]) or all([i == [] for i in exits_lists]):
        return 'No observation!'

    for entries in entries_lists:
        if entries == []:
            continue
        i = 0
        for time_ticks in entries:
            entries[i] = datetime.datetime(2000, 1, 1, time_ticks.hour, time_ticks.minute, time_ticks.second)
            i += 1

    for exits in exits_lists:
        if exits == []:
            continue
        i = 0
        for time_ticks in exits:
            exits[i] = datetime.datetime(2000, 1, 1, time_ticks.hour, time_ticks.minute, time_ticks.second)
            i += 1


    if ax == None:
        fig = plt.figure(tight_layout=True)  # figsize=(5, 5), dpi=200, tight_layout=True)
        ax = fig.add_subplot(111)  # plt.subplots(1, 1)

    to_timestamp = np.vectorize(lambda x: x.timestamp())

    startTime = datetime.datetime.combine(datetime.datetime(2000, 1, 1), max(first_obs_times))
    endTime = datetime.datetime.combine(datetime.datetime(2000, 1, 1), min(last_obs_times))

    # if len(bins) < 3:
    #     err = 'The observation duration is not enough for the selected interval!'
    #     return err

    for i in range(inputNo):
        if entries_lists == [] or exits_lists == []:
            continue

        diff = []
        current_time = startTime
        while current_time <= endTime:
            entry_count = sum(1 for entry_time in entries_lists[i] if entry_time <= current_time)
            exit_count = sum(1 for exit_time in exits_lists[i] if exit_time <= current_time)
            diff.append((current_time, (entry_count - exit_count)/zoneArea))
            current_time += datetime.timedelta(minutes=interval)

        if not smooth:
            ax.plot(*zip(*diff), label=labels[i], color=plotColors[i])
        else:
            date_np = np.array([d[0] for d in diff])
            date_num = mdates.date2num(date_np)
            date_num_smooth = np.linspace(date_num.min(), date_num.max(), len([d[0] for d in diff])*10)
            spl = make_interp_spline(date_num, [d[1] for d in diff], k=2)
            value_np_smooth = spl(date_num_smooth)
            ax.plot(mdates.num2date(date_num_smooth), value_np_smooth, label=labels[i], color=plotColors[i])
        #------------------------
        if drawMean:
            ax.axhline(y=np.mean([d[1] for d in diff]), color=plotColors[i], linestyle='--',
                      lw=1, label= 'Avg. of {}'.format(labels[i]))
        # ------------------------


    locator = mdates.AutoDateLocator()
    ax.xaxis.set_major_locator(locator)

    # ax.xaxis.set_major_locator(mdates.HourLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

    ax.xaxis.set_minor_locator(mdates.MinuteLocator(byminute=30))

    # if inputNo == 1:
    #     xLabel = 'Time ({})'.format(bins_start.strftime('%A, %b %d, %Y'))
    # else:
    xLabel = 'Time of day'

    # ax.set_xticklabels(fontsize = 6, rotation = 45)#'vertical')
    ax.tick_params(axis='x', labelsize=xTickSize, rotation=0)
    ax.tick_params(axis='y', labelsize=yTickSize)
    ax.set_xlabel(xLabel, fontsize=xLabelSize)

    tm = getUserTitle(transports[0])

    if yLabelSize > 0:
        ax.set_ylabel('{}s / m$^2$'.format(tm.capitalize()), fontsize=yLabelSize)

    ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    if unitIdxs[0].split('_')[0] == 'all':
        title = f'Density of {tm}s in all zones'
    else:
        title = f'Density of {tm}s in zone #{unitIdxs[0]}'
    if siteName != None:
        title = f'{title} in {siteName}'
    ax.set_title(title, fontsize=titleSize)

    if not all(l == '' for l in labels):
        ax.legend(loc='best', fontsize=legendFontSize)


    ax.grid(True, 'major', 'both', ls='--', lw=.5, c='k', alpha=.3)

    watermark(ax)

# ======================================================================
def sankeyPlotActivity(dbFileName, outputFile, siteName=None, colors_dict=color_dict):
    session = connectDatabase(dbFileName)
    q = session.query(Person.gender, Activity.activity, Person.age)\
        .join(GroupBelonging, GroupBelonging.personIdx == Person.idx)\
        .join(Activity, Activity.groupIdx == GroupBelonging.groupIdx)\
        .filter(Activity.activity != None)

    results = q.all()

    # Convert the results to a DataFrame
    df = pd.DataFrame.from_records(results, columns=['Gender', 'Activity', 'Age'])
    for column in df.columns:
        df[column] = df[column].apply(lambda x: x.name)

    title = 'Activities by age and gender'
    if siteName != None:
        title = f'{title} in {siteName}'

    create_sankey_diagram(df, outputFile, colors_dict, title)

# =======================================================================

def sankeyPlotTransit(dbFileName, actionType, unitIdx, outputFile, siteName=None, colors_dict=color_dict):

    q = getQueryList([dbFileName], ['all_modes'], [actionType], [unitIdx])[0]
    results = q.all()
    # Convert the results to a DataFrame
    df = pd.DataFrame.from_records(results)
    if actionType == 'all_crossings' and unitIdx == 'all_units':
        df = df.iloc[:, 5:8]
    else:
        df = df.iloc[:, 3:6]

    df.columns = ['Gender', 'Transport', 'Age']

    for column in df.columns:
        df[column] = df[column].apply(lambda x: x.name)

    title = 'Transport modes by age and gender'
    if siteName != None:
        title = f'{title} in {siteName}'

    create_sankey_diagram(df, outputFile, colors_dict, title)

# =======================================================================

def create_sankey_diagram(df, outputFile, colors_dict=None, title=None):

    labels_0 = df.iloc[:, 0].unique().tolist()
    labels_1 = df.iloc[:, 1].unique().tolist()
    labels_2 = df.iloc[:, 2].unique().tolist()
    labels = labels_0 + labels_1 + labels_2

    sources = []
    targets = []
    values = []

    for label_0 in labels_0:
        for label_1 in labels_1:
            value = df[(df.iloc[:, 0] == label_0) & (df.iloc[:, 1] == label_1)].shape[0]
            sources.append(labels.index(label_0))
            targets.append(labels.index(label_1))
            values.append(value)

    for label_2 in labels_2:
        for label_1 in labels_1:
            value = df[(df.iloc[:, 2] == label_2) & (df.iloc[:, 1] == label_1)].shape[0]
            sources.append(labels.index(label_1))
            targets.append(labels.index(label_2))
            values.append(value)

    if colors_dict is None:
        colors = [(randint(0, 255), randint(0, 255), randint(0, 255), 1) for i in range(len(labels))]
    else:
        colors = [mcolors.to_rgba(colors_dict[l]) for l in labels]

    node_color = [f'rgba({r},{g},{b},{a})' for r, g, b, a in colors]
    node_label_color = {x: y for x, y in zip(labels, node_color)}

    link_color = [None]*len(sources)
    i = 0
    for s,t in zip(sources, targets):
        if labels[s] in labels_0:
            link_color[i] = f'rgba({colors[s][0]},{colors[s][1]},{colors[s][2]}, 0.5)'
        else:
            link_color[i] = f'rgba({colors[t][0]},{colors[t][1]},{colors[t][2]}, 0.5)'
        i=i+1

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=labels,
            color=node_color
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=link_color
        ))])

    fig.update_layout(title_text=title, title_font_size=20, title_x=0.5, title_xanchor="center",
                      margin_b=40, margin_r=40, margin_l=40, margin_t=60)
    # fig.write_image('sankey_diagram.pdf', engine='orca')
    pio.kaleido.scope.mathjax = None
    pio.write_image(fig, outputFile, scale=2)
    # fig.show()


# =================================================================
def cumEnterExitPlot(dbFiles, labels, transports, unitIdxs,
                 ax=None, alpha=1, colors=plotColors, siteName=None,
                 titleSize=8, xLabelSize=8, yLabelSize=8, xTickSize=8, yTickSize=7, legendFontSize=6):

    # # Sample data
    # date_times = ['2022-01-01 00:00:00', '2022-01-01 00:01:00', '2022-01-01 00:03:00', '2022-01-01 00:05:00',
    #               '2022-01-01 00:06:00', '2022-01-01 00:09:00']
    #
    # # Convert date-times to pandas datetime object
    # date_times = pd.to_datetime(date_times)

    inputNo = len(dbFiles)
    sessions = []
    first_obs_times = []
    last_obs_times = []

    for i in range(inputNo):
        session = connectDatabase(dbFiles[i])
        sessions.append(session)

        fobst, lobst = getObsStartEnd(session)
        first_obs_times.append(fobst.time())
        last_obs_times.append(lobst.time())

    actionTypes_entries = ['entering_zone'] * inputNo
    query_list_entries = getQueryList(dbFiles, transports, actionTypes_entries, unitIdxs)
    if isinstance(query_list_entries, str):
        return query_list_entries
    entries_lists = getTimeLists(query_list_entries, actionTypes_entries)

    actionTypes_exits = ['exiting_zone'] * inputNo
    query_list_exits = getQueryList(dbFiles, transports, actionTypes_exits, unitIdxs)
    if isinstance(query_list_exits, str):
        return query_list_exits
    exits_lists = getTimeLists(query_list_exits, actionTypes_exits)

    if all([i == [] for i in entries_lists]) or all([i == [] for i in exits_lists]):
        return 'No observation!'

    for entries in entries_lists:
        if entries == []:
            continue
        i = 0
        for time_ticks in entries:
            entries[i] = datetime.datetime(2000, 1, 1, time_ticks.hour, time_ticks.minute, time_ticks.second)
            i += 1

    for exits in exits_lists:
        if exits == []:
            continue
        i = 0
        for time_ticks in exits:
            exits[i] = datetime.datetime(2000, 1, 1, time_ticks.hour, time_ticks.minute, time_ticks.second)
            i += 1

    if ax == None:
        fig = plt.figure(tight_layout=True)  # figsize=(5, 5), dpi=200, tight_layout=True)
        ax = fig.add_subplot(111)  # plt.subplots(1, 1)

    to_timestamp = np.vectorize(lambda x: x.timestamp())

    startTime = datetime.datetime.combine(datetime.datetime(2000, 1, 1), max(first_obs_times))
    endTime = datetime.datetime.combine(datetime.datetime(2000, 1, 1), min(last_obs_times))

    for i in range(inputNo):
        entries = pd.to_datetime([ent for ent in entries_lists[i] if ent >= startTime and ent <= endTime]).sort_values()
        exits = pd.to_datetime([ext for ext in exits_lists[i] if ext >= startTime and ext <= endTime]).sort_values()

        # # Sort the dates in ascending order
        # date_times = date_times.sort_values()

        # Create a new DataFrame with a count of events at each time
        df_entries = pd.DataFrame({'count': range(1, len(entries) + 1)}, index=entries)
        df_exits = pd.DataFrame({'count': range(1, len(exits) + 1)}, index=exits)

        # Compute the empirical cumulative sum of the counts
        ecdf_entries = df_entries['count']
        ecdf_exits = df_exits['count']

        # Create an empirical cumulative plot
        ax.step(ecdf_entries.index, ecdf_entries, label=f'Enter ({labels[i]})', where='post', lw=0.5)
        ax.step(ecdf_exits.index, ecdf_exits, label=f'Exit ({labels[i]})', where='post', lw=0.5)

    locator = mdates.AutoDateLocator()
    ax.xaxis.set_major_locator(locator)

    # ax.xaxis.set_major_locator(mdates.HourLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

    ax.xaxis.set_minor_locator(mdates.MinuteLocator(byminute=30))

    # if inputNo == 1:
    #     xLabel = 'Time ({})'.format(bins_start.strftime('%A, %b %d, %Y'))
    # else:
    xLabel = 'Time of day'

    # ax.set_xticklabels(fontsize = 6, rotation = 45)#'vertical')
    ax.tick_params(axis='x', labelsize=xTickSize, rotation=0)
    ax.tick_params(axis='y', labelsize=yTickSize)
    ax.set_xlabel(xLabel, fontsize=xLabelSize)

    tm = getUserTitle(transports[0])

    if yLabelSize > 0:
        ax.set_ylabel('No. of {}s'.format(tm), fontsize=yLabelSize)

    ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    if unitIdxs[0].split('_')[0] == 'all':
        title = f'Cumulative sum of {tm}s enter/exit in all zones'
    else:
        title = f'Cumulative sum of {tm}s enter/exit in zone #{unitIdxs[0]}'
    if siteName != None:
        title = f'{title} in {siteName}'
    ax.set_title(title, fontsize=titleSize)

    if not all(l == '' for l in labels):
        ax.legend(loc='best', fontsize=legendFontSize)

    ax.grid(True, 'major', 'both', ls='--', lw=.5, c='k', alpha=.3)

    watermark(ax)


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


# =====================================================================
def getLabelSizePie(transport, fieldName, session, startTime=None, endTime=None, threshold=0.02):

    if transport == 'all_modes':
        field_ = getattr(Mode, fieldName)
        q = session.query(field_, func.count(func.distinct(Mode.idx))) \
            .join(GroupBelonging, GroupBelonging.personIdx == Mode.personIdx)

    elif transport == 'walking':
        field_ = getattr(Person, fieldName)
        q = session.query(field_, func.count(field_)) \
            .join(Mode, Person.idx == Mode.personIdx) \
            .filter(Mode.transport == transport) \
            .join(GroupBelonging, GroupBelonging.personIdx == Person.idx)

    elif transport == 'cardriver':
        field_ = getattr(Vehicle, fieldName)
        q = session.query(field_, func.count(field_)) \
            .join(Mode, Vehicle.idx == Mode.vehicleIdx) \
            .filter(Mode.transport == transport) \
            .join(GroupBelonging, GroupBelonging.personIdx == Mode.personIdx)

    elif transport == 'Activity':
        if fieldName == 'activity':
            field_ = getattr(Activity, fieldName)
            q = session.query(field_, func.count(field_)) \
                .join(GroupBelonging, GroupBelonging.groupIdx == Activity.groupIdx)
        elif fieldName in ['age', 'gender']:
            field_ = getattr(Person, fieldName)
            q = session.query(field_, func.count(func.distinct(Person.idx))) \
                .join(GroupBelonging, GroupBelonging.personIdx == Person.idx)\
                .join(Activity, Activity.groupIdx == GroupBelonging.groupIdx)\
                .filter(Activity.activity != None)

    if startTime != None and endTime != None:
        q = q.join(ZoneCrossing, ZoneCrossing.groupIdx == GroupBelonging.groupIdx)\
            .filter(LineCrossing.instant >= startTime)\
            .filter(LineCrossing.instant < endTime)

    q = q.group_by(field_)

    labels = [i[0].name if not isinstance(i[0], str) else i[0] for i in q.all()]
    sizes = [int(i[1]) for i in q.all()]

    if len(labels) == 0 or len(sizes) == 0:
        return 'Error: No observation!'

    sizes_percent = np.array(sizes) / np.sum(sizes)
    other_indices = []
    for i, s in enumerate(sizes_percent):
        if s < threshold:
            other_indices.append(i)

    if len(other_indices) > 1:

        other_sum = 0
        for i in other_indices:
            other_sum = other_sum + sizes[i]

        sizes = [sizes[i] for i in range(len(sizes)) if not i in other_indices]
        labels = [labels[i] for i in range(len(labels)) if not i in other_indices]

        if round(other_sum / np.sum(sizes), 2) > 0:
            sizes.append(other_sum)
            labels.append('other')
    elif len(other_indices) == 1:
        if round(sizes[other_indices[0]] / np.sum(sizes), 2) == 0:
            sizes = [sizes[i] for i in range(len(sizes)) if not i in other_indices]
            labels = [labels[i] for i in range(len(labels)) if not i in other_indices]

    labels = list(map(lambda x: x.replace('cardriver', 'driving'), labels))

    return labels, sizes


# =====================================================================
def getPeakHours(start_obs_time, end_obs_time, interval):
    # morningPeakStart = morningPeakStart,
    # morningPeakEnd = morningPeakEnd,
    # eveningPeakStart = eveningPeakStart,
    # eveningPeakEnd = eveningPeakEnd):

    peakHours = {}
    key_config = '{} - {}'
    key_format = '%H:%M'

    if interval <= 60:
        c_m = interval
    else:
        c_m = 60

    bins_start = ceil_time(start_obs_time, c_m)
    no_bins = (end_obs_time - bins_start).seconds // (interval*60)
    bins_end = bins_start + datetime.timedelta(minutes=(interval*no_bins))

    key = key_config.format(start_obs_time.strftime(key_format), end_obs_time.strftime(key_format))
    peakHours[key] = [start_obs_time.time(), end_obs_time.time()]

    key = key_config.format(start_obs_time.strftime(key_format), bins_start.strftime(key_format))
    peakHours[key] = [start_obs_time.time(), bins_start.time()]

    bin_edge = bins_start
    for i in range(no_bins):
        bin_edge2 = bin_edge + datetime.timedelta(minutes=interval)
        key = key_config.format(bin_edge.strftime(key_format), bin_edge2.strftime(key_format))
        peakHours[key] = [bin_edge.time(), bin_edge2.time()]
        bin_edge = bin_edge2

    if bins_end < end_obs_time:
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


# =====================================================================
def ceil_time(time, m):
    if time.second == 0 and time.microsecond == 0 and time.minute % m == 0:
        return time
    minutes_by_m = time.minute // m
    # get the difference in times
    diff = (minutes_by_m + 1) * m - time.minute
    time = (time + datetime.timedelta(minutes=diff)).replace(second=0, microsecond=0)
    return time


# =====================================================================
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


# =====================================================================
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


# =====================================================================
def calculateNoBins(session, minutes=binsMinutes):
    start_obs_time, end_obs_time = getObsStartEnd(session)
    duration = end_obs_time - start_obs_time
    duration_in_s = duration.total_seconds()
    bins = round(duration_in_s/(60*minutes))
    if bins == 0:
        bins = 1
    return bins


# =====================================================================
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


# =====================================================================
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


# =====================================================================
# def getVideoMetadata(filename):
#     HachoirConfig.quiet = True
#     parser = createParser(filename)
#
#     with parser:
#         try:
#             metadata = extractMetadata(parser, 7)
#         except Exception as err:
#             print("Metadata extraction error: %s" % err)
#             metadata = None
#     if not metadata:
#         print("Unable to extract metadata")
#
#     # creationDatetime_text = metadata.exportDictionary()['Metadata']['Creation date']
#     # creationDatetime = datetime.strptime(creationDatetime_text, '%Y-%m-%d %H:%M:%S')
#
#     metadata_dict = metadata._Metadata__data
#     # for key in metadata_dict.keys():
#     #     if metadata_dict[key].values:
#     #         print(key, metadata_dict[key].values[0].value)
#     creationDatetime = metadata_dict['creation_date'].values[0].value
#     width = metadata_dict['width'].values[0].value
#     height = metadata_dict['height'].values[0].value
#
#     return creationDatetime, width, height


def getVideoMetadata(file_path):
    cmd = f"ffprobe -v error -select_streams v:0 -show_entries stream_tags=timecode,codec_type -show_entries stream=height,width -show_entries format_tags=creation_time -of json {file_path}"
    result = subprocess.check_output(cmd, shell=True)
    metadata = json.loads(result.decode('utf-8'))

    timecode_str = metadata['streams'][0]['tags']['timecode']
    creation_time_str = metadata['format']['tags']['creation_time']

    if 'height' in metadata['streams'][0]['tags']:
        height = metadata['streams'][0]['tags']['height']
        width = metadata['streams'][0]['tags']['width']
    else:
        height = metadata['streams'][0]['height']
        width = metadata['streams'][0]['width']

    creation_time = datetime.datetime.strptime(creation_time_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=None)
    timecode = datetime.datetime.strptime(timecode_str, "%H:%M:%S:%f").replace(tzinfo=None)
    timecode = timecode.replace(year=creation_time.year, month=creation_time.month, day=creation_time.day)

    return timecode, width, height







# =====================================================================
def watermark(ax):
    ax.text(0.02, 0.95, str('StudioProject'),
            fontsize=8, color='gray',
            ha='left', va='bottom',
            transform=ax.transAxes,
            weight="bold", alpha=.5)


# =====================================================================
def pdf_merge(pdfs_list):
    merger = PdfFileMerger()
    [merger.append(pdf) for pdf in pdfs_list]
    with open(os.path.join(pdfs_dir, "All_plots.pdf"), "wb") as new_file:
        merger.write(new_file)


# =====================================================================
def text_to_pdf(text, fontsize_pt, filename):
    a4_width_mm = 121.92
    pt_to_mm = 0.35
    # fontsize_pt = 30
    fontsize_mm = fontsize_pt * pt_to_mm
    margin_bottom_mm = 10
    character_width_mm = 7 * pt_to_mm
    width_text = a4_width_mm / character_width_mm

    pdf = FPDF(unit='mm', format=[162.56, 121.92])
    pdf.set_auto_page_break(True, margin=margin_bottom_mm)
    pdf.add_page()
    pdf.set_font(family='Helvetica', size=fontsize_pt)
    splitted = text.split('\n')

    for line in splitted:
        # lines = textwrap.wrap(line, width_text)

        if len(line) == 0:
            pdf.ln()

        # for wrap in lines:
        pdf.cell(0, fontsize_mm, line, ln=1, align = 'L')

    pdf.output(filename, 'F')


# =====================================================================
def plots_compile(plots_dir):
    pdfs_list = []
    text_to_pdf('\n\n\nAll Plots\n[StudioProject]', 40, f'{plots_dir}/title_page.pdf')
    pdfs_list.append(os.path.join(plots_dir, 'title_page.pdf'))
    for path, subdirs, files in os.walk(plots_dir):
        pdfs_sub_list = []
        for name in files:
            file_name, file_ext = os.path.splitext(name)
            if file_ext == '.pdf' and (not file_name in ['All_plots', 'title_page']):
                pdfs_sub_list.append(os.path.join(path, name))
        if len(pdfs_sub_list) > 0:
            title_page_text = ''
            relative_paths = os.path.relpath(path, plots_dir)
            for i, item in enumerate(relative_paths.split('/')):
                title_page_text = title_page_text + '\n' + ' '*4*i + '-' + item.capitalize()
            text_to_pdf(title_page_text, 25, f'{path}/title_page.pdf')
            pdfs_list.append(os.path.join(path, 'title_page.pdf'))
            pdfs_list.extend(pdfs_sub_list)

    merger = PdfFileMerger()
    [merger.append(pdf) for pdf in pdfs_list]
    with open(os.path.join(plots_dir, "All_plots.pdf"), "wb") as new_file:
        merger.write(new_file)
    print('Done!......')



# =====================================================================
# def count_difference(entries, exits, startTime, endTime, time_interval):
#     # Create a datetime object for the startTime and endTime
#     start_time = datetime.datetime.strptime(startTime, '%Y-%m-%d %H:%M:%S')
#     end_time = datetime.datetime.strptime(endTime, '%Y-%m-%d %H:%M:%S')
#
#     # Initialize a variable to keep track of the cumulative count difference
#     cumulative_count_difference = 0
#
#     # Initialize a variable to keep track of the current time
#     current_time = start_time
#
#     # Initialize a list to store the time-stamped cumulative count differences
#     result = []
#
#     # Loop through the time range between the start and end time at the specified interval
#     while current_time <= end_time:
#         # Calculate the cumulative count of entries up to the current time
#         entries_count = sum(
#             [entry[1] for entry in entries if datetime.datetime.strptime(entry[0], '%Y-%m-%d %H:%M:%S') <= current_time])
#
#         # Calculate the cumulative count of exits up to the current time
#         exits_count = sum(
#             [exit[1] for exit in exits if datetime.datetime.strptime(exit[0], '%Y-%m-%d %H:%M:%S') <= current_time])
#
#         # Calculate the cumulative count difference up to the current time
#         cumulative_count_difference = entries_count - exits_count
#
#         # Append the current time and cumulative count difference to the result list
#         result.append((current_time, cumulative_count_difference))
#
#         # Increment the current time by the specified interval
#         current_time += datetime.timedelta(minutes=time_interval)
#
#     return result


# ======================================================================
def entryExitDiff(entries, exits, startTime, endTime, time_lag):
    diff = []
    current_time = startTime
    while current_time <= endTime:
        entry_count = sum(1 for entry_time in entries if entry_time <= current_time)
        exit_count = sum(1 for exit_time in exits if exit_time <= current_time)
        diff.append((current_time, entry_count - exit_count))
        current_time += datetime.timedelta(minutes=time_lag)
    return diff


# ======================= DEMO MODE ============================
if __name__ == '__main__':
    from indicators import batchPlots
    import os, shutil

    outputFolder = '/Users/abbas/Desktop/plots_Bernard'
    metaDataFile = '/Users/abbas/Documents/PhD/video_files/metadata-ped-streets.sqlite'

    for filename in os.listdir(outputFolder):
        file_path = os.path.join(outputFolder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))

    batchPlots(metaDataFile, outputFolder, site='bernard-outremont')




    # dbFile1 = '/Users/abbas/Test_StudioProject/Hartland_2019.sqlite'
    # dbFile2 = '/Users/abbas/Test_StudioProject/Hartland_2020.sqlite'
    # transportModePDF([dbFile1, dbFile2], ['2019', '2020'], ['cardriver', 'cardriver'],
    #                  ['crossing line', 'crossing line'], ['1', '1'], ['both', 'both'])

