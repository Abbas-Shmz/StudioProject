#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: Abbas
"""

from enum import Enum, auto


class Gender(Enum):
    female  = auto()
    male    = auto()
    unknown = auto()


class Age(Enum):
    infant = auto()
    toddler = auto()
    child = auto()
    teen = auto()
    young_adult = auto()
    adult = auto()
    senior = auto()


class Disability(Enum):
    none = auto()
    Wheelchair = auto()
    Walker = auto()
    Cane = auto()
    While_cane = auto()


class activityTypes(Enum):
    strolling = auto()
    jogging = auto()
    shopping = auto()
    talking = auto()
    resting = auto()
    eating = auto()
    playing = auto()
    doing_exercise = auto()
    smoking = auto()
    using_cellphone = auto()
    observing = auto()
    reading_writing = auto()
    performing = auto()
    selling = auto()
    playing_with_pets = auto()
    taking_pet_for_walk = auto()


class siteTypes(Enum):
    street_section = auto()
    street_segment = auto()
    public_space = auto()
    intersection = auto()


class zoiTypes(Enum):
    school = auto()
    nursery = auto()
    shopping_center = auto()
    hypermarket = auto()
    convenience_store = auto()
    pharmacy = auto()
    beauty_center = auto()
    bank = auto()
    residential_building = auto()
    university_campus = auto()
    restaurant = auto()
    fast_food = auto()
    bistro = auto()
    bakery = auto()
    cinema = auto()
    park = auto()
    post_office = auto()
    gas_station = auto()
    library = auto()
    coffee_shop = auto()
    NA = auto()


class odTypes(Enum):
    sidewalk = auto()
    road_lane = auto()
    bus_lane = auto()
    cycling_path = auto()
    adjoining_ZOI = auto()
    on_street_parking_lot = auto()
    bicycle_rack = auto()
    informal_bicycle_parking = auto()
    bus_stop = auto()
    subway_station = auto()
    street = auto()
    alley = auto()


class vehicleTypes(Enum):
    # car_Sedan = auto()
    # car_SUV = auto()
    # mini = auto()
    private_car = auto()
    pickup_truck = auto()
    van = auto()
    taxi = auto()
    motorbike = auto()
    cargo_van = auto()
    mini_truck = auto()
    big_truck = auto()
    bus = auto()
    moped = auto()
    shared_eCar = auto()
    ambulance = auto()
    school_bus = auto()
    police_car = auto()
    fire_engine = auto()
    cleaning_service = auto()
    waste_collection = auto()
    autonomous_car = auto()


class streetCrossings(Enum):
    from_crosswalk = auto()
    jaywalking = auto()


class pedCarrying(Enum):
    none = auto()
    stroller = auto()
    shopping_bag = auto()
    bicycle = auto()
    skateboard = auto()
    luggage = auto()
    cart = auto()
    food_drink = auto()
    ball = auto()
    umbrella = auto()
    parasol = auto()
    box = auto()


class pedRolling(Enum):
    none = auto()
    scooter = auto()
    skateboard = auto()
    rollerblades = auto()
    segway = auto()
    uniwheel = auto()
    heelies = auto()


class OdDirection(Enum):
    NA = auto()
    start_point = auto()
    end_point = auto()


class stopActions(Enum):
    no = auto()
    loading_passenger = auto()
    unloading_passenger = auto()
    loading_objects = auto()
    unloading_objects = auto()
    deliver_objects = auto()