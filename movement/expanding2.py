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

def fill_position_matrix(position_matrix, ship_point, mining, intermediate=False):
    """
    FILL POSITION MATRIX WITH 1 TO REPRESENT MY SHIP
    ALSO NEED TO TAKE INTO ACCOUNT ITS NEIGHBORING COORDS

    ADDING TRY/EXCEPT TO HANDLE OUT OF BOUNDS FROM MAP
    """

    position_matrix[ship_point[0]][ship_point[1]] = Matrix_val.ALLY_SHIP.value

    ## ALSO ITS NORTH, EAST, SOUTH AND WEST
    try: position_matrix[ship_point[0] - 1][ship_point[1]] = Matrix_val.ALLY_SHIP.value
        # logging.debug("Filled position_matrix point: {}, {}".format(ship_point[0] - 1,ship_point[1]))
    except: pass
    try: position_matrix[ship_point[0]][ship_point[1] + 1] = Matrix_val.ALLY_SHIP.value
        # logging.debug("Filled position_matrix point: {}, {}".format(ship_point[0], ship_point[1] + 1))
    except: pass
    try: position_matrix[ship_point[0] + 1][ship_point[1]] = Matrix_val.ALLY_SHIP.value
        # logging.debug("Filled position_matrix point: {}, {}".format(ship_point[0] + 1, ship_point[1]))

    except: pass
    try: position_matrix[ship_point[0]][ship_point[1] - 1] = Matrix_val.ALLY_SHIP.value
        # logging.debug("Filled position_matrix point: {}, {}".format(ship_point[0], ship_point[1] - 1))
    except: pass


    ## A BIT FURTHER NORTH, EAST, SOUTH AND WEST
    # position_matrix[ship_point[0] - 2][ship_point[1]] = Matrix_val.ALLY_SHIP.value
    # position_matrix[ship_point[0]][ship_point[1] + 2] = Matrix_val.ALLY_SHIP.value
    # position_matrix[ship_point[0] + 2][ship_point[1]] = Matrix_val.ALLY_SHIP.value
    # position_matrix[ship_point[0]][ship_point[1] - 2] = Matrix_val.ALLY_SHIP.value



    # if not(intermediate) or mining:
    #     ## DO NOT FILL DIAGONALS DURING AN INTERMEDIATE STEP POSITION MATRIX FILL
    #     ## UNLESS ITS DOCKING, INTERMEDIATE STEP IS SAME AS FINAL STEP
    #     ## ALSO DIAGONALS?
    #     try: position_matrix[ship_point[0] - 1][ship_point[1] - 1] = Matrix_val.ALLY_SHIP.value
    #         # logging.debug("Filled position_matrix point: {}, {}".format(ship_point[0] - 1, ship_point[1] - 1))
    #     except: pass
    #     try: position_matrix[ship_point[0] - 1][ship_point[1] + 1] = Matrix_val.ALLY_SHIP.value
    #         # logging.debug("Filled position_matrix point: {}, {}".format(ship_point[0] - 1, ship_point[1] + 1))
    #     except: pass
    #     try: position_matrix[ship_point[0] + 1][ship_point[1] + 1] = Matrix_val.ALLY_SHIP.value
    #         # logging.debug("Filled position_matrix point: {}, {}".format(ship_point[0] + 1, ship_point[1] + 1))
    #     except: pass
    #     try: position_matrix[ship_point[0] + 1][ship_point[1] - 1] = Matrix_val.ALLY_SHIP.value
    #         # logging.debug("Filled position_matrix point: {}, {}".format(ship_point[0] + 1, ship_point[1] - 1))
    #     except: pass


    # HERE ALWAYS FILLING DIAGONALS (EVEN ON INTERMEDIATE STEPS)
    try: position_matrix[ship_point[0] - 1][ship_point[1] - 1] = Matrix_val.ALLY_SHIP_CORNER.value
    # logging.debug("Filled position_matrix point: {}, {}".format(ship_point[0] - 1, ship_point[1] - 1))
    except: pass

    try: position_matrix[ship_point[0] - 1][ship_point[1] + 1] = Matrix_val.ALLY_SHIP_CORNER.value
    # logging.debug("Filled position_matrix point: {}, {}".format(ship_point[0] - 1, ship_point[1] + 1))
    except: pass

    try: position_matrix[ship_point[0] + 1][ship_point[1] + 1] = Matrix_val.ALLY_SHIP_CORNER.value
    # logging.debug("Filled position_matrix point: {}, {}".format(ship_point[0] + 1, ship_point[1] + 1))
    except: pass

    try: position_matrix[ship_point[0] + 1][ship_point[1] - 1] = Matrix_val.ALLY_SHIP_CORNER.value
    # logging.debug("Filled position_matrix point: {}, {}".format(ship_point[0] + 1, ship_point[1] - 1))
    except: pass



def fill_position_matrix_intermediate_steps(MyMoves, ship_id, angle, thrust, mining):
    """
    FILL IN INTERMEDIATE POSITION MATRIXES
    """
    ship_coord = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
    dx = thrust/7

    for x in range(1, 7):  ## 7 WILL BE FILLED BY ANOTHER FUNCTION
        intermediate_coord = MyCommon.get_destination_coord(ship_coord, angle, int(round(dx*x)))
        intermediate_point = MyCommon.get_rounded_point(intermediate_coord)

        # logging.debug("About to fill intermediate step: {}".format(x))
        fill_position_matrix(MyMoves.position_matrix[x], intermediate_point, mining, intermediate=True)
        # if thrust == 0:
        #     ## IF THRUST IS 0, DOCKING
        #     ## NEED TO FILL DIAGONALS
        #     fill_position_matrix(MyMoves.position_matrix[x], intermediate_point, intermediate=False)
        # else:
        #     fill_position_matrix(MyMoves.position_matrix[x], intermediate_point, intermediate=True)

    ## LAST TURN
    x = 7
    intermediate_coord = MyCommon.get_destination_coord(ship_coord, angle, int(round(dx * x)))
    intermediate_point = MyCommon.get_rounded_point(intermediate_coord)

    fill_position_matrix(MyMoves.position_matrix[x], intermediate_point, mining, intermediate=False)











def get_closest_docking_coord(MyMoves, target_planet_id, ship_id):
    """
    GET CLOSEST DOCKING COORD FROM DOCKABLE MATRIX

    NOT USED.  NOT COMPLETELY WORKING YET (NUMPY NO POP)
    """
    def get_coord_closest_dock_value(values, distances):
        """
        GET COORDS OF CLOSEST DOCK VALUES (BASED ON CLOSEST DISTANCE FIRST)
        """
        v_indx = np.where(values == Matrix_val.DOCKABLE_AREA.value)
        return values[v_indx][np.argsort(distances[v_indx])]


    ship_coord = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
    ship_point = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['point']
    circle_radius = 7
    square_radius = 8

    dockable_matrix = MyCommon.get_circle_in_square(MyMoves.EXP.dockable_matrix,
                                                           ship_coord,
                                                    circle_radius,
                                                    square_radius,
                                                           pad_values = -1)

    position_matrix = MyCommon.get_circle_in_square(MyMoves.position_matrix[7],
                                                    ship_coord,
                                                    circle_radius,
                                                    square_radius,
                                                    pad_values=-1)

    section_matrix = np.add(dockable_matrix,position_matrix)


    distances = MyMoves.EXP.distance_matrix_DxD

    closest_points = get_coord_closest_dock_value(section_matrix, distances)

    logging.debug(closest_points)

    while len(closest_points) > 0:
        closest_point = closest_points.pop()
        slope = (closest_point[0] - square_radius, closest_point[1] - square_radius)
        target_coord = MyCommon.Coordinates(ship_point[0] + slope[0], ship_point[1] + slope[1])

        if target_coord:
            thrust, angle = astar.get_thrust_angle_from_Astar(MyMoves, ship_id, target_coord, distance, target_planet_id)
            if thrust != 0:
                return thrust, angle

    return None, None


def get_docking_coord(MyMoves, target_planet_id, ship_id):
    """
    RETURN TARGET COORD TOWARDS A SPECIFIED PLANET
    AND THE DISTANCE
    """
    ship_coord = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
    target_planet_coord = MyMoves.myMap.data_planets[target_planet_id]['coords']

    angle = MyCommon.get_angle(ship_coord, target_planet_coord)

    ## WE CAN DOCK ALREADY, SO JUST RETURN DISTANCE 0 SO WE CAN JUST DOCK
    if MyCommon.ship_can_dock(MyMoves, ship_coord, target_planet_id):
        docking_coord = ship_coord
        distance = 0
        return docking_coord, distance

    ## GET MATRIX OF JUST THE TARGET PLANET
    target_planet_matrix = MyMoves.EXP.planet_matrix[target_planet_id]
    seek_value = Matrix_val.PREDICTION_PLANET.value
    value_coord = MyCommon.get_coord_of_value_in_angle(target_planet_matrix, ship_coord, seek_value, angle)

    if value_coord:
        reverse_angle = MyCommon.get_reversed_angle(angle)  ## REVERSE DIRECTION/ANGLE
        docking_coord = MyCommon.get_destination_coord(value_coord, reverse_angle, MyCommon.Constants.MOVE_BACK)
    else:
        logging.error("Did not get closest target, given the angle.")

    ## CHECK IF DOCKING COORD FOUND IS FREE/AVAILABLE
    ## IF NOT, TRY TO GET NEW COORDS
    if not(isPositionMatrix_free(MyMoves.position_matrix[7], docking_coord)):
        #new_target_coord = get_new_target_coord(MyMoves.position_matrix, new_target_coord, reverse_angle)

        new_docking_coord = get_new_docking_coord(MyMoves, ship_id, target_planet_id, MyMoves.position_matrix[7], docking_coord, reverse_angle)
        if new_docking_coord is None:  ## TRY GOING CLOCKWISE/COUNTERCLOCKWISE
            docking_coord = get_new_docking_coord2(MyMoves, ship_id, target_planet_id, docking_coord, reverse_angle)
        else:
            docking_coord = new_docking_coord

    if docking_coord is None:
        distance = None
    else:
        distance = MyCommon.calculate_distance(ship_coord ,docking_coord)

    ## DISTANCE IS NONE, MEANS NO DOCKING COORD FOUND
    return docking_coord, distance


def get_new_docking_coord(MyMoves, ship_id, target_planet_id, position_matrix, coord, reverse_angle):
    """
    GIVEN A COORD, GET A NEW COORD CLOSE TO IT
    SINCE THE PREVIOUS ONE IS ALREADY TAKEN
    """

    ## ONLY IF FILLED POSITION IS NORTH, EAST, SOUTH, WEST
    positions = [(reverse_angle, 2), \
                 (reverse_angle + 90, 2), \
                 (reverse_angle - 90, 2), \
                 (reverse_angle + 45, 2), \
                 (reverse_angle - 45, 2), \
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
        round_point = MyCommon.get_rounded_point(new_coord)
        round_coord = MyCommon.Coordinates(round_point[0], round_point[1])

        if isPositionMatrix_free(position_matrix, round_coord) and MyCommon.ship_can_dock(MyMoves, new_coord, target_planet_id):
        #if isPositionMatrix_free(position_matrix, round_coord):
            logging.debug("New docking coord found is good (Free and dockable: new_coord: {}".format(new_coord))
            #ship_can_dock(MyMoves, round_coord, target_planet_id)
            #return new_coord
            return round_coord ## THIS IS BETTER? LESS COLLISION?

    logging.debug("No new position found for ship_id: {} target_planet_id: {} coord: {}".format(ship_id, target_planet_id,coord))
    return None ## NO NEW COORDS AVAILABLE


def get_new_docking_coord2(MyMoves, ship_id, target_planet_id, old_target_coord, reverse_angle, ):
    """
    USING CURVATURE OF PLANET
    CLOCKWISE AND COUNTER CLOCKWISE DIRECTIONS
    SINCE PREVIOUS COORDINATES ARE ALSO TAKEN
    """
    position_matrix = MyMoves.position_matrix[7]
    planet_center = MyMoves.myMap.data_planets[target_planet_id]['coords']
    planet_angle = reverse_angle
    planet_angle_left = reverse_angle
    opposite = 1.5
    spots = 0

    while spots < 4:  ## MOVE 1.5 FROM OLD TARGET TO NEW TARGET
        adjacent = MyCommon.calculate_distance(old_target_coord, planet_center)
        angle = math.degrees(math.atan(opposite / adjacent))
        hypotenuse = opposite / math.sin(math.radians(angle))
        new_angle = planet_angle + angle
        new_target_coord = MyCommon.get_destination_coord(planet_center, new_angle, hypotenuse)
        round_point = MyCommon.get_rounded_point(new_target_coord)
        round_coord = MyCommon.Coordinates(round_point[0], round_point[1])

        if isPositionMatrix_free(position_matrix, round_coord) and MyCommon.ship_can_dock(MyMoves, new_target_coord, target_planet_id):
        #if isPositionMatrix_free(position_matrix, round_coord):
            logging.debug("Good enough 2")
            #ship_can_dock(MyMoves, round_coord, target_planet_id)
            return round_coord

        ## GOING COUNTER CLOCKWISE
        new_angle_left = planet_angle_left - angle
        new_target_coord_left = MyCommon.get_destination_coord(planet_center, new_angle_left, hypotenuse)
        round_point = MyCommon.get_rounded_point(new_target_coord_left)
        round_coord = MyCommon.Coordinates(round_point[0], round_point[1])

        if isPositionMatrix_free(position_matrix, round_coord) and MyCommon.ship_can_dock(MyMoves, new_target_coord_left, target_planet_id):
        #if isPositionMatrix_free(position_matrix, round_coord):
            logging.debug("Good enough 3")
            #ship_can_dock(MyMoves, round_coord, target_planet_id)
            return round_coord

        ## UPDATE VALUES FOR NEXT ITERATION
        old_target_coord = new_target_coord
        planet_angle = new_angle
        planet_angle_left = new_angle_left

        spots += 1

    logging.debug("No new position2 found for ship_id: {} target_planet_id: {} coord: {}".format(ship_id, target_planet_id, old_target_coord))
    return None


def isPositionMatrix_free(position_matrix, coord):
    """
    RETURNS TRUE IF POSITION MATRIX IS AVAILABLE
    GIVEN CURRENT POSITION MATRIX AND COORD
    BASED ON POSITION MATRIX [7]
    """
    logging.debug("At coord: {}.  Position_matrix value is: {}".format(coord, position_matrix[int(round(coord.y))][int(round(coord.x))]))

    point = MyCommon.get_rounded_point(coord)
    return position_matrix[point[0]][point[1]] == 0








# ship_coord = MyCommon.Coordinates(34.2850, 57.5704)
# angle_towards_target = 277
# fake_target_thrust = 10
# temp_target_coord = MyCommon.get_destination_coord(ship_coord, angle_towards_target, fake_target_thrust)
# print(temp_target_coord)



# coord = MyCommon.Coordinates(115.9589 , 171.9589)
# target = MyCommon.Coordinates(24.5, 45.5)
# d = MyCommon.calculate_distance(coord, target, rounding=False)
# print(d)


## GET DISTANCES BETWEEN point and a set of points
# to_points = np.array([(0,1),(1,0),(-1,0),(0,-1),(2,2)])
# start = np.array([0,0])
# distances = np.linalg.norm(to_points - start, ord=2, axis=1.)  # distances is a list
#
# print(type(distances))


# coord = MyCommon.Coordinates(125.9814,189.031)
# print(MyCommon.get_destination_coord(coord, 162, 3, rounding=True))
#
# coord = MyCommon.Coordinates(130.9572,189.0428)
# print(MyCommon.get_destination_coord(coord, 236, 4, rounding=True))
