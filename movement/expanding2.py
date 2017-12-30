import heapq
import MyCommon
import initialization.astar as astar
import math
import logging
import sys
import traceback
from models.data import Matrix_val
import numpy as np
import copy

def fill_position_matrix(position_matrix, ship_point):
    """
    FILL POSITION MATRIX WITH 1 TO REPRESENT MY SHIP
    ALSO NEED TO TAKE INTO ACCOUNT ITS NEIGHBORING COORDS
    """
    position_matrix[ship_point[0]][ship_point[1]] = Matrix_val.ALLY_SHIP.value

    ## ALSO ITS NORTH, EAST, SOUTH AND WEST
    position_matrix[ship_point[0] - 1][ship_point[1]] = Matrix_val.ALLY_SHIP.value
    position_matrix[ship_point[0]][ship_point[1] + 1] = Matrix_val.ALLY_SHIP.value
    position_matrix[ship_point[0] + 1][ship_point[1]] = Matrix_val.ALLY_SHIP.value
    position_matrix[ship_point[0]][ship_point[1] - 1] = Matrix_val.ALLY_SHIP.value

    ## A BIT FURTHER NORTH, EAST, SOUTH AND WEST
    # position_matrix[ship_point[0] - 2][ship_point[1]] = Matrix_val.ALLY_SHIP.value
    # position_matrix[ship_point[0]][ship_point[1] + 2] = Matrix_val.ALLY_SHIP.value
    # position_matrix[ship_point[0] + 2][ship_point[1]] = Matrix_val.ALLY_SHIP.value
    # position_matrix[ship_point[0]][ship_point[1] - 2] = Matrix_val.ALLY_SHIP.value

    ## ALSO DIAGONALS?
    position_matrix[ship_point[0] - 1][ship_point[1] - 1] = Matrix_val.ALLY_SHIP.value
    position_matrix[ship_point[0] - 1][ship_point[1] + 1] = Matrix_val.ALLY_SHIP.value
    position_matrix[ship_point[0] + 1][ship_point[1] + 1] = Matrix_val.ALLY_SHIP.value
    position_matrix[ship_point[0] + 1][ship_point[1] - 1] = Matrix_val.ALLY_SHIP.value


def fill_position_matrix2(MyMoves, ship_id, angle, thrust):
    """
    FILL IN INTERMEDIATE POSITION MATRIXES
    """
    ship_coord = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
    dx = thrust/7

    for x in range(1, 7):  ## 7 WILL BE FILLED BY ANOTHER FUNCTION
        intermediate_coord = MyCommon.get_destination_coord(ship_coord, angle, int(round(dx*x)))
        intermediate_point = (int(round(intermediate_coord.y)), int(round(intermediate_coord.x)))
        fill_position_matrix(MyMoves.position_matrix[x], intermediate_point)


def get_thrust_angle_from_Astar(MyMoves, ship_id, target_coord, target_distance):
    """
    RETURN THRUST AND ANGLE BASED SHIP ID AND TARGET COORD ONLY

    WE"LL USE LOCAL/SECTIONED A*
    """
    position_matrix = MyMoves.position_matrix[7]

    square_radius = MyCommon.Constants.SECTION_SQUARE_RADIUS
    circle_radius = MyCommon.Constants.SECTION_CIRCLE_RADIUS
    fake_target_thrust = MyCommon.Constants.SECTION_SQUARE_RADIUS ## 10
    ship_coord = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
    ship_point = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['point']

    ## GET ANGLE TO TARGET
    angle_towards_target = MyCommon.get_angle(ship_coord, target_coord)

    ## GET SECTION
    section_matrix = MyCommon.get_circle_in_square(position_matrix, ship_coord, circle_radius, square_radius)

    ## CHECK IF THE TARGET IS WITHIN THE SHIPS IMMEDIATE REACH
    if  target_distance <= 7:
        ## TARGET IS INSIDE CIRCLE RADIUS
        temp_target_coord = target_coord
    else:
        ## TARGET IS OUTSIDE CIRCLE RADIUS
        temp_target_coord = MyCommon.get_destination_coord(ship_coord, angle_towards_target, fake_target_thrust)


    ## GET TARGET POINT ON THE SECTION MATRIX
    ## ROUNDING temp_target_point CAUSES COLLISIONS OR NOT DOCKING SHIPS
    # temp_target_point = (temp_target_coord.y - ship_coord.y, temp_target_coord.x - ship_coord.x)  ## THIS IS BETTER, DOCKS BETTER
    # section_target_point = (int(MyCommon.Constants.SECTION_SQUARE_RADIUS + round(temp_target_point[0])), \
    #                         int(MyCommon.Constants.SECTION_SQUARE_RADIUS + round(temp_target_point[1])))

    temp_target_point = (int(round(temp_target_coord.y)) - int(round(ship_coord.y)), \
                         int(round(temp_target_coord.x)) - int(round(ship_coord.x)))
    section_target_point = (int(MyCommon.Constants.SECTION_SQUARE_RADIUS + temp_target_point[0]), \
                            int(MyCommon.Constants.SECTION_SQUARE_RADIUS + temp_target_point[1]))


    ## MID POINT OF THE SECTION MATRIX IS THE STARTING POINT (SHIP COORD IN SECTION MATRIX IS JUST THE MIDDLE)
    mid_point = (MyCommon.Constants.SECTION_SQUARE_RADIUS, MyCommon.Constants.SECTION_SQUARE_RADIUS) ## MIDDLE OF SECTION MATRIX
    mid_coord = MyCommon.Coordinates(mid_point[0], mid_point[1])

    ## PERFORM A* TOWARDS TARGET
    ## WE DONT REALLY NEED TABLE OR SIMPLIFIED PATHS HERE
    #path_table_forward, simplified_paths = astar.get_Astar_table(section_matrix, mid_point, section_target_point)

    ## RETURN ANGLE/THRUST
    try:
        ## JUST GETTING THE FIRST STRAIGHT (COULD COLLIDE WITH SOMETHING)
        #astar_destination_point = path_table_forward[mid_point]

        #logging.debug("At ship_id: {} section_target_point: {} temp_target_coord: {} target_coord: {} temp_target_point: {}".format(ship_id, section_target_point, temp_target_coord, target_coord, temp_target_point))

        if mid_point == section_target_point:
            ## REACHED ITS TARGET
            logging.debug("target reached!")

            ## CHECK IF STILL AVAILABLE IN POSITION MATRIX
            ## POSIBLE THAT ANOTHER SHIP NOW WENT TO THIS POSITION THAT MOVED BEFORE THIS SHIP

            if not (isPositionMatrix_free(MyMoves.position_matrix[7], ship_coord)):
                logging.debug("Need to Move! (no longer available) NEED UPDATE!!!!")
            else:
                logging.debug("Staying!")

            astar_destination_coord = mid_coord
            angle, thrust = 0, 0

        else:
            ## GET FURTHEST POINT WITHIN THE CIRCLE
            path_points = astar.a_star(section_matrix, mid_point, section_target_point)
            #logging.debug("path_points: {}".format(path_points))
            for current_point in path_points[::-1]:
                current_coord = MyCommon.Coordinates(current_point[0], current_point[1])
                if MyCommon.within_circle(current_coord, mid_coord, circle_radius) \
                        and no_collision(mid_coord, current_coord, section_matrix):
                    astar_destination_point = current_point
                    #logging.debug("astar_destination_point: {}".format(astar_destination_point))
                else:
                    break

            astar_destination_coord = MyCommon.Coordinates(astar_destination_point[0], astar_destination_point[1])
            angle, thrust = MyCommon.get_angle_thrust(mid_coord, astar_destination_coord)
    except:
        ## NO A* PATH FOUND
        ## TARGET POINT MAY NOT BE REACHABLE (DUE TO OTHER SHIPS IN ITS IN POSITION MATRIX)
        ## ACTUAL TARGET POINT IS AVAILABLE SINCE IT WAS DETERMINED BY get_target_coord_towards_planet ?
        ## WHICH LOOKS FOR OTHER TARGET COORDS IF ITS ALREADY TAKEN

        astar_destination_coord = mid_coord ## NEED TO UPDATE THIS LATER, GET A NEW TARGET!!
        angle, thrust = 0, 0
        logging.debug("ship_coord: {}".format(ship_coord))
        logging.debug("No A* PATH FOUND!!!!!!!!!!!!!!!!!!!!!!!")
        logging.debug("except!")


    ## UPDATE POSITION MATRIX FOR THIS POINT WILL NOW BE TAKEN
    slope_from_mid_point = (astar_destination_coord.y - MyCommon.Constants.SECTION_SQUARE_RADIUS, \
                            astar_destination_coord.x - MyCommon.Constants.SECTION_SQUARE_RADIUS)
    taken_point = (ship_point[0] + slope_from_mid_point[0] , ship_point[1] + slope_from_mid_point[1])
    fill_position_matrix(MyMoves.position_matrix[7], taken_point)

    return thrust, angle

def no_collision(start_coord, target_coord, section_matrix):
    """
    RETURNS TRUE IF NO COLLISION BETWEEN THE TWO COORDS
    """

    # angle = MyCommon.get_angle(start_coord, target_coord)
    # distance = MyCommon.calculate_distance(start_coord, target_coord)
    #
    # for thrust in range(int(round(distance))):
    #     temp_coord = MyCommon.get_destination_coord(start_coord, angle, thrust)
    #     round_coord = MyCommon.Coordinates(int(round(temp_coord.y)), int(round(temp_coord.x)))
    #     if section_matrix[round_coord.y][round_coord.x] != 0:
    #         return False
    #
    # return True

    ## NOT USING GET DESTINATION COORDS
    ## SHOULD BE MORE OPTIMAL
    angle = MyCommon.get_angle(start_coord, target_coord)
    distance = MyCommon.calculate_distance(start_coord, target_coord)
    unit_vector = -np.cos(np.radians(-angle - 90)), -np.sin(np.radians(-angle - 90))
    start_point = [start_coord.y, start_coord.x]

    for multiplier in range(1,int(round(distance)) + 1):
        new_coord = [start_point[0] + multiplier * unit_vector[0],
                     start_point[1] + multiplier * unit_vector[1]]
        round_new_coord = (int(round(new_coord[0])), int(round(new_coord[1])))

        if section_matrix[round_new_coord[0]][round_new_coord[1]] != 0:
            return False

    return True

def get_docking_coord(MyMoves, target_planet_id, ship_id):
    """
    RETURN TARGET COORD TOWARDS A SPECIFIED PLANET
    """

    ship_coord = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
    target_planet_coord = MyMoves.myMap.data_planets[target_planet_id]['coords']

    angle = MyCommon.get_angle(ship_coord, target_planet_coord)

    ## GET MATRIX OF JUST THE TARGET PLANET
    target_planet_matrix = MyMoves.EXP.planet_matrix[target_planet_id]

    seek_value = Matrix_val.PREDICTION_PLANET.value

    value_coord = MyCommon.get_coord_of_value_in_angle(target_planet_matrix, ship_coord, seek_value, angle)

    if value_coord:
        reverse_angle = MyCommon.get_reversed_angle(angle)  ## REVERSE DIRECTION/ANGLE
        docking_coord = MyCommon.get_destination_coord(value_coord, reverse_angle, MyCommon.Constants.MOVE_BACK)  ## MOVE BACK
    else:
        logging.error("Did not get closest target, given the angle.")

    if not(isPositionMatrix_free(MyMoves.position_matrix[7], docking_coord)):
        #new_target_coord = get_new_target_coord(MyMoves.position_matrix, new_target_coord, reverse_angle)

        new_docking_coord = get_new_docking_coord(MyMoves.position_matrix[7], docking_coord, reverse_angle)
        if new_docking_coord is None:  ## TRY GOING CLOCKWISE/COUNTERCLOCKWISE
            docking_coord = get_new_docking_coord2(MyMoves, docking_coord, reverse_angle, target_planet_id)
        else:
            docking_coord = new_docking_coord

    if docking_coord is None:
        distance = None
    else:
        distance = MyCommon.calculate_distance(ship_coord ,docking_coord)

    return docking_coord, distance

def get_new_docking_coord(position_matrix, coord, reverse_angle):
    """
    GIVEN A COORD, GET A NEW COORD CLOSE TO IT
    """

    ## ONLY IF FILLED POSITION IS NORTH, EAST, SOUTH, WEST
    positions = [(reverse_angle + 90, 2), \
                 (reverse_angle - 90, 2), \
                 # (reverse_angle + 45, 2), \
                 # (reverse_angle - 45, 2), \
                 (reverse_angle, 2), \
                 (reverse_angle + 45, 3), \
                 (reverse_angle - 45, 3), \
                 ]

    ## NEED DIFFERENT POSITIONS WHEN TAKING BIGGER RADIUS
    ## TAKING BIGGEST RADIUS 2x ON NORTH, EAST, SOUTH, WEST
    ## ONE IN DIAGONALS
    # positions = [(reverse_angle, 3), \
    #              (reverse_angle + 20, 2), \
    #              (reverse_angle - 20, 2), \
    #              (reverse_angle + 90, 4), \
    #              (reverse_angle - 90, 4), \
    #              (reverse_angle - 65, 4), \
    #              (reverse_angle - 65, 4), \
    #              ]

    for angle, thrust in positions:
        new_coord = MyCommon.get_destination_coord(coord, angle, thrust)
        round_coord = MyCommon.Coordinates(int(round(new_coord.y)), int(round(new_coord.x)))

        if isPositionMatrix_free(position_matrix, round_coord):
            #return new_coord
            return round_coord ## THIS IS BETTER? LESS COLLISION?

    logging.debug("No new position found for coord: {}".format(coord))
    return None ## NO NEW COORDS AVAILABLE


def get_new_docking_coord2(MyMoves, old_target_coord, reverse_angle, target_planet_id):
    """
    USING CURVATURE OF PLANET

    CLOCKWISE AND COUNTER CLOCKWISE DIRECTIONS
    """
    position_matrix = MyMoves.position_matrix[7]
    planet_center = MyMoves.myMap.data_planets[target_planet_id]['coords']
    planet_angle = reverse_angle
    planet_angle_left = reverse_angle
    opposite = 1.5
    spots = 0

    while spots < 3:  ## MOVE 1.5 FROM OLD TARGET TO NEW TARGET
        adjacent = MyCommon.calculate_distance(old_target_coord, planet_center)
        angle = math.degrees(math.atan(opposite / adjacent))
        hypotenuse = opposite / math.sin(math.radians(angle))
        new_angle = planet_angle + angle
        new_target_coord = MyCommon.get_destination_coord(planet_center, new_angle, hypotenuse)
        round_coord = MyCommon.Coordinates(int(round(new_target_coord.y)), int(round(new_target_coord.x)))

        if isPositionMatrix_free(position_matrix, round_coord):
            return round_coord

        ## GOING COUNTER CLOCKWISE
        new_angle_left = planet_angle_left - angle
        new_target_coord_left = MyCommon.get_destination_coord(planet_center, new_angle_left, hypotenuse)
        round_coord = MyCommon.Coordinates(int(round(new_target_coord_left.y)), int(round(new_target_coord_left.x)))

        if isPositionMatrix_free(position_matrix, round_coord):
            return round_coord

        ## UPDATE VALUES FOR NEXT ITERATION
        old_target_coord = new_target_coord
        planet_angle = new_angle
        planet_angle_left = new_angle_left

        spots += 1

    logging.debug("No new position2 found for coord: {}".format(old_target_coord))
    return None

def isPositionMatrix_free(position_matrix, coord):
    """
    RETURNS TRUE IF POSITION MATRIX IS AVAILABLE
    """
    return position_matrix[int(round(coord.y))][int(round(coord.x))] == 0




# import random
# import heapq
# import datetime
#
# def someFunction(sum, val):
#     sum += val
#     return sum
#
# data_heap = []
# data_list = []
#
# for x in range(1000):
#     val1 = random.randint(1,10)
#     val2 = random.randint(1, 10)
#     heapq.heappush(data_heap, (val1,val2))
#     data_list.append(val2)
#
#
# ## METHOD 1
# start = datetime.datetime.now()
#
# total = 0
# total_somefunction = 0
# for x in data_list:
#     s = datetime.datetime.now()
#     total = someFunction(total, x)
#     total_somefunction += datetime.timedelta.total_seconds(datetime.datetime.now() - s)
#
# print("all someFunction time in method #1", total_somefunction)
# print("Total Method #1: ", datetime.timedelta.total_seconds(datetime.datetime.now() - start))
#
#
#
# ## METHOD 2
# start = datetime.datetime.now()
#
# total = 0
# total_somefunction = 0
# while data_heap:
#     _, x = heapq.heappop(data_heap)
#     s = datetime.datetime.now()
#     total = someFunction(total, x)
#     total_somefunction += datetime.timedelta.total_seconds(datetime.datetime.now() - s)
#
# print("all someFunction time in method #2", total_somefunction)
# print("Total Method #2: ",datetime.timedelta.total_seconds(datetime.datetime.now() - start))

