
import heapq
import MyCommon
import initialization.astar as astar
import math
import logging
import sys
import traceback
from models.data import Matrix_val

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

    ## A BIT FURTHER
    # position_matrix[ship_point[0] - 2][ship_point[1]] = Matrix_val.ALLY_SHIP.value
    # position_matrix[ship_point[0]][ship_point[1] + 2] = Matrix_val.ALLY_SHIP.value
    # position_matrix[ship_point[0] + 2][ship_point[1]] = Matrix_val.ALLY_SHIP.value
    # position_matrix[ship_point[0]][ship_point[1] - 2] = Matrix_val.ALLY_SHIP.value

    ## ALSO DIAGONALS?
    # position_matrix[ship_point[0] - 1][ship_point[1] - 1] = Matrix_val.ALLY_SHIP.value
    # position_matrix[ship_point[0] - 1][ship_point[1] + 1] = Matrix_val.ALLY_SHIP.value
    # position_matrix[ship_point[0] + 1][ship_point[1] + 1] = Matrix_val.ALLY_SHIP.value
    # position_matrix[ship_point[0] + 1][ship_point[1] - 1] = Matrix_val.ALLY_SHIP.value


def get_Astar_thrust_angle(MyMoves, position_matrix, ship_id, target_coord):
    """
    RETURN THRUST AND ANGLE BASED SHIP ID AND TARGET COORD ONLY

    WE"LL USE LOCAL/SECTIONED A*
    """
    square_radius = MyCommon.Constants.SECTION_RADIUS
    circle_radius = MyCommon.Constants.SECTION_CIRCLE_RADIUS
    fake_target_thrust = MyCommon.Constants.SECTION_RADIUS ## 10
    ship_coord = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
    ship_point = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['point']

    ## GET ANGLE TO TARGET
    angle_towards_target = MyCommon.get_angle(ship_coord, target_coord)

    ## GET SECTION
    section_matrix = MyCommon.get_circle_in_matrix(position_matrix, ship_coord, circle_radius, square_radius)

    ## CHECK IF THE TARGET IS WITHIN THE SHIPS REACH
    target_distance = MyCommon.calculate_distance(ship_coord, target_coord)
    if  target_distance <= 7:
        ## TARGET IS INSIDE CIRCLE RADIUS
        temp_target_coord = MyCommon.get_destination_coord(ship_coord, angle_towards_target, target_distance)
    else:
        ## TARGET IS OUTSIDE CIRCLE RADIUS
        temp_target_coord = MyCommon.get_destination_coord(ship_coord, angle_towards_target, fake_target_thrust)

    logging.debug("Ship_id: {} target_coord: {} angle_towards_target: {} target_distance: {}".format(ship_id, target_coord, angle_towards_target, target_distance))

    ## GET TARGET POINT ON THE SECTION MATRIX
    temp_target_point = (temp_target_coord.y - ship_coord.y, temp_target_coord.x - ship_coord.x)
    section_target_point = (int(MyCommon.Constants.SECTION_RADIUS + round(temp_target_point[0])), \
                            int(MyCommon.Constants.SECTION_RADIUS + round(temp_target_point[1])))

    logging.debug("temp_target_coord: {} temp_target_point: {} section_target_point: {} ".format(temp_target_coord,temp_target_point, section_target_point))

    ## MID POINT OF THE SECTION MATRIX IS THE STARTING POINT (SHIP COORD IN SECTION MATRIX IS JUST THE MIDDLE)
    mid_point = (MyCommon.Constants.SECTION_RADIUS, MyCommon.Constants.SECTION_RADIUS) ## MIDDLE OF SECTION MATRIX
    mid_coord = MyCommon.Coordinates(mid_point[0], mid_point[1])

    ## PERFORM A* TOWARDS TARGET
    ## WE DONT REALLY NEED TABLE OR SIMPLIFIED PATHS HERE
    #path_table_forward, simplified_paths = astar.get_Astar_table(section_matrix, mid_point, section_target_point)

    ## RETURN ANGLE/THRUST
    try:
        ## JUST GETTING THE FIRST STRAIGHT
        #astar_destination_point = path_table_forward[mid_point]

        ## GET FURTHEST POINT WITHIN THE CIRCLE
        path_points = astar.a_star(section_matrix, mid_point, section_target_point)
        logging.debug("path_points: {}".format(path_points))
        for current_point in path_points[::-1]:
            current_coord = MyCommon.Coordinates(current_point[0], current_point[1])
            if MyCommon.within_circle(current_coord, mid_coord, circle_radius) \
                    and no_collision(mid_coord, current_coord, section_matrix):
                astar_destination_point = current_point
                logging.debug("astar_destination_point: {}".format(astar_destination_point))
            else:
                logging.debug("Break")
                break

        astar_destination_coord = MyCommon.Coordinates(astar_destination_point[0], astar_destination_point[1])
        logging.debug("1")
        angle, thrust = MyCommon.get_angle_thrust(mid_coord, astar_destination_coord)
        logging.debug("2")
    except:
        ## NO PATH FORWARD TABLE
        ## POSSIBLY REACHED ITS TARGET
        astar_destination_coord = mid_coord
        angle, thrust = 0, 0
        logging.debug("Testing!!! Possibly reached target for ship_id: {} target_coord: {}".format(ship_id, target_coord))

    ## UPDATE POSITION MATRIX FOR THIS POINT WILL NOW BE TAKEN
    slope_from_mid_point = (astar_destination_coord.y - MyCommon.Constants.SECTION_RADIUS, \
                            astar_destination_coord.x - MyCommon.Constants.SECTION_RADIUS)
    taken_point = (ship_point[0] + slope_from_mid_point[0] , ship_point[1] + slope_from_mid_point[1])
    fill_position_matrix(position_matrix, taken_point)

    return thrust, angle

def no_collision(start_coord, target_coord, section_matrix):
    """
    RETURNS TRUE IF NO COLLISION BETWEEN THE TWO COORDS
    """
    angle = MyCommon.get_angle(start_coord, target_coord)
    distance = MyCommon.calculate_distance(start_coord, target_coord)

    for thrust in range(round(distance)):
        temp_coord = MyCommon.get_destination_coord(start_coord, angle, thrust)
        round_coord = MyCommon.Coordinates(int(round(temp_coord.y)), int(round(temp_coord.x)))
        if section_matrix[round_coord.y][round_coord.x] != 0:
            logging.info("section matrix value: {}".format(section_matrix[round_coord.y][round_coord.x]))
            return False

    return True

def get_target_coord_towards_planet(MyMoves, target_planet_id, ship_id):
    """
    RETURN TARGET COORD TOWARDS A SPECIFIED PLANET
    """

    ship_coord = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
    target_coord = MyMoves.myMap.data_planets[target_planet_id]['coords']

    angle = MyCommon.get_angle(ship_coord, target_coord)

    ## GET MATRIX OF JUST THE TARGET PLANET
    planet_matrix = MyMoves.EXP.planet_matrix[target_planet_id]

    looking_for_val = Matrix_val.PREDICTION_PLANET.value

    closest_coord = MyCommon.get_coord_closest_value(planet_matrix, ship_coord, looking_for_val, angle)

    if closest_coord:
        reverse_angle = MyCommon.get_reversed_angle(angle)  ## REVERSE DIRECTION/ANGLE
        new_target_coord = MyCommon.get_destination_coord(closest_coord, reverse_angle, 1)  ## MOVE BACK
    else:
        logging.error("Did not get closest target, given the angle.")

    if not(isPositionMatrix_free(MyMoves.position_matrix, new_target_coord)):
        new_target_coord = get_new_target_coord(MyMoves.position_matrix, new_target_coord, reverse_angle)

    return new_target_coord

def get_new_target_coord(position_matrix, coord, reverse_angle):
    """
    GIVEN A COORD, GET A NEW COORD CLOSE TO IT
    """
    positions = [(reverse_angle + 90, 2), \
                 (reverse_angle - 90, 2), \
                 (reverse_angle + 45, 2), \
                 (reverse_angle - 45, 2), \
                 (reverse_angle, 2), \
                 (reverse_angle + 45, 3), \
                 (reverse_angle - 45, 3), \
                 ]

    for angle, thrust in positions:
        new_coord = MyCommon.get_destination_coord(coord, angle, thrust)
        round_coord = MyCommon.Coordinates(int(round(new_coord.y)), int(round(new_coord.x)))

        if isPositionMatrix_free(position_matrix, round_coord):
            return new_coord

    return None ## NO NEW COORDS AVAILABLE

def isPositionMatrix_free(position_matrix, coord):
    """
    RETURNS TRUE IF POSITION MATRIX IS AVAILABLE
    """
    return position_matrix[int(round(coord.y))][int(round(coord.x))] == 0







