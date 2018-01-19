
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
        logging.debug("get next planet: ship_id: {} from_planet_id {} planet_id {}".format(ship_id, from_planet_id, planet_id))
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

    ## WHEN NOT USING HEAPQ
    # len_miners_prev = len(MyMoves.myMap.myMap_prev.data_planets[planet_id]['my_miners'])
    # len_miners_now = len(MyMoves.myMap.data_planets[planet_id]['my_miners'])
    # max_docks = MyMoves.myMap.data_planets[planet_id]['num_docks']
    #
    # ## PREVIOUSLY AND CURRENTLY, HAVE LESS MINERS THAN NUMBER OF DOCKS
    # if len_miners_prev < max_docks and len_miners_now < max_docks:
    #     return True
    #
    # return False

    ## WHEN USING HEAPQ, OR MOVING CLOSER SHIPS FIRST
    len_miners_now = len(MyMoves.myMap.data_planets[planet_id]['my_miners'])
    max_docks = MyMoves.myMap.data_planets[planet_id]['num_docks']

    ## CURRENTLY ONLY, HAVE LESS MINERS THAN NUMBER OF DOCKS
    if planet_id not in MyMoves.myMap.planets_enemy and len_miners_now < max_docks:
        return True

    return False


def get_mining_spot(MyMoves, ship_id, target_planet_id):
    """
    AT THE LAUNCH LAND ON COORD, FIND A MINING SAFE SPOT

                               (-4,0)

                        (-2,-1)      (2,1)
       (-1,-4)   (-1,-2)       (-1,0)     (-1,2)     (-1,4)

    NO LONGER USED??
    """
    # print(get_destination_coord(start, 58, 3))
    # print(get_destination_coord(start, 90, 3))
    # print(get_destination_coord(start, 60, 2))
    # print(get_destination_coord(start, 122, 3))
    # print(get_destination_coord(start, 120, 2))

    # print(get_destination_coord(start, 38, 5))
    # print(get_destination_coord(start, 148, 5))

    ## CHECK PREVIOUS Astar path_key

    if MyMoves.myMap.myMap_prev.data_ships[MyMoves.myMap.my_id][ship_id]['Astar_path_key'] is None:
            #or len(MyMoves.myMap.myMap_prev.data_ships[MyMoves.myMap.my_id][ship_id]['Astar_path_key']) == 3:
        ## FIRST 3 SHIPS OR READY TO MINE
        if MyMoves.myMap.can_dock(ship_id, target_planet_id):
            MyMoves.command_queue.append(MyCommon.convert_for_command_queue(ship_id, target_planet_id))
        else:
            ## CANT DOCK THIS PLANET ANYMORE/YET
            ## NEED TO GO TO ANOTHER PLANET!!!!!!111
            ## IMPLEMENT LATER!!!!!!!!!!!!!!!!!1
            ## !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!1
            #target_id = get_next_target_planet(MyMoves, ship_id)
            pass
    else:
        ## REACHED LAUNCH ON COORD
        MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['Astar_path_key'] = None  ## SO IT"LL DOCK NEXT TURN

        start = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
        target = MyMoves.myMap.data_planets[target_planet_id]['coords']
        angle = MyCommon.get_angle(start, target)

        values = [(angle, 3), \
                  (angle - 32, 3), \
                  (angle + 32, 3), \
                  (angle - 52, 5), \
                  (angle + 58, 5), \
                  (angle - 30, 2), \
                  (angle + 30, 2)]

        for new_angle, new_thrust in values:
            new_angle = new_angle % 360  ## KEEP IT FROM 0-360 RANGE
            new_destination_coord = MyCommon.get_destination_coord(start, new_angle, new_thrust)
            new_destination_point = MyCommon.get_rounded_point(new_destination_coord)

            if new_destination_point not in MyMoves.myMap.taken_coords:
                MyMoves.command_queue.append(MyCommon.convert_for_command_queue(ship_id, new_thrust, new_angle))
                break


def get_set_path_table_toward_launch(MyMoves, ship_id, ship_coord, from_planet_id, target_planet_id):
    """
    GET PATH FROM SPAWN TO FLY OFF COORD

    SET ASTAR PATH TABLE
    """
    launch_pad = MyMoves.EXP.planets[from_planet_id][target_planet_id]  ## GET LAUNCH PAD
    fly_off_point = (launch_pad.fly_off.y, launch_pad.fly_off.x)
    ship_point = (ship_coord.y, ship_coord.x)

    path_table_forward, simplified_paths = astar.get_Astar_table(MyMoves.EXP.all_planet_matrix, ship_point, fly_off_point)
    MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['Astar_path_table'] = path_table_forward

    return path_table_forward


def check_duplicate_target(MyMoves, ship_id, target_planet_id):
    """
    CHECKS IF TARGET IS ALREADY TAKEN BY ANOTHER SHIP

    IF IT IS, GET A NEW TARGET POINT

    NO LONGER USED!!!
    """
    try:
        old_target_point = MyMoves.myMap.myMap_prev.data_ships[MyMoves.myMap.my_id][ship_id]['target_point']
        old_angle = MyMoves.myMap.myMap_prev.data_ships[MyMoves.myMap.my_id][ship_id]['target_angle']
    except:
        old_target_point = None

    if old_target_point is None:
        return None
    elif old_target_point in MyMoves.myMap.all_target_coords:
        ## GET NEW TARGET POINT
        old_target_point = get_new_point_on_planet(MyMoves, old_target_point, old_angle, target_planet_id)

    ## RETURN OLD OR NEW TARGET POINT (COORD)
    return MyCommon.Coordinates(old_target_point[0], old_target_point[1])


def get_new_point_on_planet(MyMoves, old_target_point, old_angle, target_planet_id):
    """
    GET NEW TARGET POINT

    MOVE CLOCKWISE (TAKE CURVATURE OF THE PLANET INTO ACCOUNT)

    NO LONGER USED!!!
    """
    planet_center = MyMoves.myMap.data_planets[target_planet_id]['coords']
    planet_angle = MyCommon.get_reversed_angle(old_angle)
    opposite = 1.5

    while True:  ## MOVE 1.5 FROM OLD TARGET TO NEW TARGET
        target_coord = MyCommon.Coordinates(old_target_point[0], old_target_point[1])
        adjacent = MyCommon.calculate_distance(target_coord, planet_center)
        angle = math.degrees(math.atan(opposite / adjacent))
        hypotenuse = opposite / math.sin(math.radians(angle))
        new_angle = planet_angle + angle
        new_target_coord = MyCommon.get_destination_coord(planet_center, new_angle, hypotenuse)
        new_target_point = (new_target_coord.y, new_target_coord.x)

        if old_target_point not in MyMoves.myMap.all_target_coords:
            break
        else:
            ## UPDATE VALUES FOR NEXT ITERATION
            old_target_point = new_target_point
            planet_angle = new_angle

    return new_target_point


def get_thrust_to_planet(MyMoves, ship_coord, planet_coord, target_planet_id, angle, safe_coord=None):
    """
    GET THRUST VALUE TOWARDS A PLANET ID PROVIDED

    NEED TO TAKE INTO ACCOUNT THE PLANETS RADIUS + 3 (TO NOT CRASH AND TO MINE)

    NO LONGER USED!!!
    """
    if safe_coord:  ## SAFE COORD ALREADY IDENTIFIED
        target_coord = safe_coord
    else:
        target_coord = get_mining_coord(MyMoves, target_planet_id, planet_coord, angle)
    distance = MyCommon.calculate_distance(ship_coord, target_coord)

    if distance > 7:
        thrust = 7  ## STILL FAR, MAXIMIZE THRUST
    else:
        thrust = round(distance)

    return thrust, target_coord


def get_mining_coord(MyMoves, target_planet_id, planet_coord, angle):
    """
    GET SAFE COORD TO MINE
    GIVEN PLANET ID AND THE REVERSE ANGLE (ANGLE OUTWARD THE CENTER OF THE PLANET

    NO LONGER USED!!!
    """
    mining_distance = 3

    planet_radius = MyMoves.myMap.data_planets[target_planet_id]['radius']
    safe_distance = planet_radius + mining_distance
    reversed_angle = MyCommon.get_reversed_angle(angle)
    safe_coord = MyCommon.get_destination_coord(planet_coord, reversed_angle, safe_distance)

    return safe_coord



