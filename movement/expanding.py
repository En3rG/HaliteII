
import heapq
import MyCommon
import initialization.astar as astar
import math
import logging
from models.data import Matrix_val
import numpy as np
import sys
import traceback



def get_next_target_planet(MyMoves, ship_id):
    """
    GET NEXT PLANET TO CONQUER

    GETS CALLED BY NEW SHIPS OR IF OLD PLANET TARGET OF A SHIP DIED RECENTLY
    """
    from_planet_id = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['from_planet']

    ## BASED ON DISTANCE ONLY
    if from_planet_id:
        distances_to_other_planets = MyMoves.EXP.planets_distance_matrix[from_planet_id]
        length = len(distances_to_other_planets)

        ## GET LOWEST TO HIGHEST VALUE OF THE LIST PROVIDED
        least_distance_order = heapq.nsmallest(length, ((v, i) for i, v in enumerate(distances_to_other_planets)))

    else:
        ## from_planet_id IS NONE
        ## NO from_planet SET, MUST BE OLD SHIP WITH NO TARGET
        ## NEED TO FIGURE OUT WHICH PLANET TO TAKE
        ship_section = MyCommon.get_section_num(MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords'])
        distance_table = MyMoves.EXP.sections_planet_distance_table[ship_section]
        length = len(distance_table)

        ## GET LOWEST TO HIGHEST VALUE OF THE LIST PROVIDED
        least_distance_order = heapq.nsmallest(length, ((distance, id) for id, distance in distance_table.items()))

    for distance, planet_id in least_distance_order:
        ## NOT OWNED BY ANYBODY YET
        if planet_id in MyMoves.myMap.planets_unowned:
            ## ORIGINAL
            if has_room_to_dock(MyMoves, planet_id):
                return planet_id

            ## CHECK IF WE HAVE MULTIPLE SHIPS NEARBY
            ## SEEMS TO BE WORST (SEE BOT 65 vs 66)
            # num_ally_nearby = get_num_ally_ships_nearby(MyMoves, planet_id)
            # planet_docks = MyMoves.EXP.planets[planet_id]['docks']
            # if has_room_to_dock(MyMoves, planet_id) and num_ally_nearby < planet_docks*MyCommon.Constants.PLANET_DOCK_MIN_MULTIPLIER:
            #     return planet_id



        ## I OWN THE PLANET, BUT CHECK IF THERE IS DOCKING SPACE AVAILABLE
        elif planet_id in MyMoves.myMap.planets_owned:
            ## ORIGINAL
            if has_room_to_dock(MyMoves, planet_id):
                return planet_id

            ## NOW ONLY IF ITS FROM THERE AND HAS ROOM
            # if has_room_to_dock(MyMoves, planet_id) and planet_id == from_planet_id:
            #     return planet_id



    return None  ## NO MORE PLANETS


    ## GETTING SCORE, NOT DISTANCE
    # if from_planet_id:
    #     scores_to_other_planets = MyMoves.EXP.planets_score_matrix[from_planet_id]
    #     length = len(scores_to_other_planets)
    #
    #     ## GET LOWEST TO HIGHEST VALUE OF THE LIST PROVIDED
    #     most_score_order = heapq.nlargest(length, ((v, i) for i, v in enumerate(scores_to_other_planets)))
    #
    # else:
    #     ## from_planet_id IS NONE
    #     ## NO from_planet SET, MUST BE OLD SHIP WITH NO TARGET
    #     ## NEED TO FIGURE OUT WHICH PLANET TO TAKE
    #     ship_section = MyCommon.get_section_num(MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords'])
    #     score_table = MyMoves.EXP.sections_planet_score_table[ship_section]
    #     length = len(score_table)
    #
    #     ## GET LOWEST TO HIGHEST VALUE OF THE LIST PROVIDED
    #     most_score_order = heapq.nlargest(length, ((score, id) for id, score in score_table.items()))
    #
    # for distance, planet_id in most_score_order:
    #     ## NOT OWNED BY ANYBODY YET
    #     if planet_id in MyMoves.myMap.planets_unowned:
    #         if has_room_to_dock(MyMoves, planet_id):
    #             return planet_id
    #
    #     ## I OWN THE PLANET, BUT CHECK IF THERE IS DOCKING SPACE AVAILABLE
    #     elif planet_id in MyMoves.myMap.planets_owned:
    #         if has_room_to_dock(MyMoves, planet_id):
    #             return planet_id
    #
    # return None ## NO MORE PLANETS


def get_num_ally_ships_nearby(MyMoves, planet_id):
    """
    GET NUMBER OF ALLY SHIPS IN THE AREA
    """
    planet_coord = MyMoves.EXP.planets[planet_id]['coords']
    planet_radius = MyMoves.EXP.planets[planet_id]['radius']

    value = MyMoves.myMatrix.ally_matrix
    total_radius = int(MyCommon.Constants.PLANET_AREA_RADIUS_CHECK * planet_radius)
    v_ally = MyCommon.get_section_with_padding(value, planet_coord, total_radius, pad_values=-1)

    num_ally_nearby = (v_ally>=0).sum()  ## ALLY MATRIX CONTAINS -1 OR SHIP IDS

    logging.debug("planet_id {} num_ally_nearby {}".format(planet_id, num_ally_nearby))

    return num_ally_nearby


def has_room_to_dock(MyMoves, planet_id):
    """
    RETURNS TRUE IF THERE IS STILL A DOCKING SPACE AVAILABLE
    """

    ## WHEN USING HEAPQ, OR MOVING CLOSER SHIPS FIRST
    len_miners_now = len(MyMoves.myMap.data_planets[planet_id]['my_miners'])
    max_docks = MyMoves.myMap.data_planets[planet_id]['num_docks']

    ## CURRENTLY ONLY, HAVE LESS MINERS THAN NUMBER OF DOCKS
    if planet_id not in MyMoves.myMap.planets_enemy and len_miners_now < max_docks:
        return True

    return False

