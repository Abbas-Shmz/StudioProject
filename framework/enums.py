#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: Abbas
"""

from enum import Enum


class Gender(Enum):
    female = 1
    male = 2
    unknown = 3


class Age(Enum):
    infant = 1
    toddler = 2
    child = 3
    teen = 4
    young_adult = 5
    adult = 6
    senior = 7


class Disability(Enum):
    none = 1
    Wheelchair = 2
    Walker = 3
    Cane = 4
    While_cane = 5


class activityTypes(Enum):
    strolling = 1
    jogging = 2
    shopping = 3
    talking = 4
    resting = 5
    eating = 6
    playing = 7
    doing_exercise = 8
    smoking = 9
    using_cellphone = 10
    observing = 11
    reading_writing = 12
    performing = 13
    selling = 14


class siteTypes(Enum):
    street_section = 1
    street_segment = 2
    public_space = 3
    intersection = 4


class zoiTypes(Enum):
    school = 1
    nursery = 2
    shopping_center = 3
    hypermarket = 4
    convenience_store = 5
    pharmacy = 6
    beauty_center = 7
    bank = 8
    residential_building = 9
    university_campus = 10
    restaurant = 11
    fast_food = 12
    bistro = 13
    bakery = 14
    cinema = 15
    park = 16
    post_office = 17
    gas_station = 18
    library = 19
    coffee_shop = 20
    NA = 21


class odTypes(Enum):
    sidewalk = 1
    road_lane = 2
    bus_lane = 3
    cycling_path = 4
    adjoining_ZOI = 5
    on_street_parking_lot = 6
    bicycle_rack = 7
    informal_bicycle_parking = 8
    bus_stop = 9
    subway_station = 10
    street = 11


class vehicleTypes(Enum):
    car_Sedan = 1
    car_SUV = 2
    bus = 3
    taxi = 4
    motorbike = 5
    mini_truck = 6
    moped = 7
    big_truck = 8
    electric_bike = 9
    shared_eCar = 10
    van = 11
    ambulance = 12
    school_buse = 13
    police_car = 14
    fire_engine = 15
    cleaning_service = 16
    waste_collection = 17
    autonomous_car = 18


class streetCrossings(Enum):
    from_crosswalk = 1
    jaywalking = 2


class pedCarrying(Enum):
    none = 1
    stroller = 2
    luggage = 3
    cart = 4
    food_drink = 5
    ball = 6
    umbrella = 7
    parasol = 8
    box = 9
    bicycle = 10
    shopping_bag = 11


class pedRolling(Enum):
    none = 1
    scooter = 2
    skateboard = 3
    rollerblades = 4
    segway = 5
    uniwheel = 6
    heelies = 7
