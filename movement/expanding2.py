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

    ADDING TRY/EXCEPT TO HANDLE OUT OF BOUNDS
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
    try: position_matrix[ship_point[0] - 1][ship_point[1] - 1] = Matrix_val.ALLY_SHIP.value
    # logging.debug("Filled position_matrix point: {}, {}".format(ship_point[0] - 1, ship_point[1] - 1))
    except: pass

    try: position_matrix[ship_point[0] - 1][ship_point[1] + 1] = Matrix_val.ALLY_SHIP.value
    # logging.debug("Filled position_matrix point: {}, {}".format(ship_point[0] - 1, ship_point[1] + 1))
    except: pass

    try: position_matrix[ship_point[0] + 1][ship_point[1] + 1] = Matrix_val.ALLY_SHIP.value
    # logging.debug("Filled position_matrix point: {}, {}".format(ship_point[0] + 1, ship_point[1] + 1))
    except: pass

    try: position_matrix[ship_point[0] + 1][ship_point[1] - 1] = Matrix_val.ALLY_SHIP.value
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



def get_thrust_angle_from_Astar(MyMoves, ship_id, target_coord, target_distance, target_planet_id):
    """
    RETURN THRUST AND ANGLE BASED SHIP ID AND TARGET COORD ONLY

    WE"LL USE LOCAL/SECTIONED A*
    """
    square_radius = MyCommon.Constants.ASTAR_SQUARE_RADIUS
    circle_radius = MyCommon.Constants.ASTAR_CIRCLE_RADIUS
    max_travel_distance = MyCommon.Constants.MAX_TRAVEL_DISTANCE
    fake_target_thrust = MyCommon.Constants.ASTAR_SQUARE_RADIUS ## 10
    ship_coord = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
    ship_point = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['point']

    ## GET ANGLE TO TARGET
    angle_towards_target = MyCommon.get_angle(ship_coord, target_coord)

    ## GET SECTION (ONLY BASE ON LAST POSITION MATRIX)
    # position_matrix = MyMoves.position_matrix[7]
    # pad_values = -1
    # section_matrix = MyCommon.get_circle_in_square(position_matrix, ship_coord, circle_radius, square_radius, pad_values)

    ## GET SECTION (FOR A* 2nd Version)
    ## GETTING SECTIONS FROM 7 POSITION MATRIXES
    pad_values = -1
    section_matrixes = {}
    for step in range(1,8):
        section_matrixes[step] = MyCommon.get_circle_in_square(MyMoves.position_matrix[step],
                                                               ship_coord,
                                                               circle_radius,
                                                               square_radius,
                                                               pad_values)


    logging.debug("get_thrust_angle_from_Astar:: angle_towards_target {}".format(angle_towards_target))

    if  target_distance <= circle_radius:
        ## TARGET IS INSIDE CIRCLE RADIUS
        temp_target_coord = target_coord
        logging.debug("get_thrust_angle_from_Astar:: target_distance {}".format(target_distance))
        temp_thrust = target_distance
    else:
        ## TARGET IS OUTSIDE CIRCLE RADIUS
        temp_target_coord = MyCommon.get_destination_coord(ship_coord, angle_towards_target, fake_target_thrust)
        logging.debug("get_thrust_angle_from_Astar:: fake_target_thrust {}".format(fake_target_thrust))
        temp_thrust = 7 ## SET TO 7 BECAUSE THAT IS THE MAX, NEED TO COMPARE THIS LATER TO A* THRUST

    logging.debug("get_thrust_angle_from_Astar:: temp_target_coord {}".format(temp_target_coord))

    ## GET NEW ANGLE AND TARGET IF GOING OUTSIDE THE MAP
    logging.debug("temp_target_coord {} angle_towards_target {} ship_coord {} fake_target_thrust {}".format(temp_target_coord, angle_towards_target, ship_coord, fake_target_thrust))
    angle_towards_target, temp_target_coord = get_angle_target_if_outside_map(temp_target_coord, angle_towards_target, MyMoves, ship_coord, fake_target_thrust)


    temp_target_point = (int(round(temp_target_coord.y)) - int(round(ship_coord.y)), \
                         int(round(temp_target_coord.x)) - int(round(ship_coord.x)))
    section_target_point = (int(MyCommon.Constants.ASTAR_SQUARE_RADIUS + temp_target_point[0]), \
                            int(MyCommon.Constants.ASTAR_SQUARE_RADIUS + temp_target_point[1]))

    logging.debug("get_thrust_angle_from_Astar:: section_target_point {}".format(section_target_point))

    ## MID POINT OF THE SECTION MATRIX IS THE STARTING POINT (SHIP COORD IN SECTION MATRIX IS JUST THE MIDDLE)
    mid_point = (MyCommon.Constants.ASTAR_SQUARE_RADIUS, MyCommon.Constants.ASTAR_SQUARE_RADIUS) ## MIDDLE OF SECTION MATRIX
    mid_coord = MyCommon.Coordinates(mid_point[0], mid_point[1])

    ## PERFORM A* TOWARDS TARGET
    ## WE DONT REALLY NEED TABLE OR SIMPLIFIED PATHS HERE
    #path_table_forward, simplified_paths = astar.get_Astar_table(section_matrix, mid_point, section_target_point)

    ## RETURN ANGLE/THRUST
    ## JUST GETTING THE FIRST STRAIGHT (COULD COLLIDE WITH SOMETHING)
    #astar_destination_point = path_table_forward[mid_point]

    #logging.debug("At ship_id: {} section_target_point: {} temp_target_coord: {} target_coord: {} temp_target_point: {}".format(ship_id, section_target_point, temp_target_coord, target_coord, temp_target_point))

    if mid_point == section_target_point:
        ## REACHED ITS TARGET
        logging.debug("target reached!")

        ## CHECK IF STILL AVAILABLE IN POSITION MATRIX
        ## POSSIBLE THAT ANOTHER SHIP NOW WENT TO THIS POSITION THAT MOVED BEFORE THIS SHIP
        if not (isPositionMatrix_free(MyMoves.position_matrix[7], ship_coord)):
            logging.debug("CANNOT MOVE DUE TO ANOTHER SHIP GOING HERE FIRST??? ship_id: {}".format(ship_id))

            ## NEED TO UPDATE THIS LATER!!
            astar_destination_coord = mid_coord
            angle, thrust = 0, 0

        ## POSSIBLE THAT DUE TO ROUNDING, IT STIL CANNOT DOCK
        elif not(ship_can_dock(MyMoves, ship_coord, target_planet_id)):
            logging.debug("CANNOT DOCK DUE TO ROUNDING!!!!!! ship_id: {}".format(ship_id))

            ## FOR NOW JUST MOVE 1 TOWARDS TARGET
            angle, thrust = angle_towards_target, 1
            astar_destination_coord = MyCommon.get_destination_coord(mid_coord, angle, thrust, rounding=True)

        else:
            logging.debug("Staying!")

            astar_destination_coord = mid_coord
            angle, thrust = 0, 0

    else:
        ## GET FURTHEST POINT WITHIN THE CIRCLE

        ## UPDATE SECTION MATRIX TO CLEAR MID POINT (JUST IN CASE NEW SHIPS WENT IN THIS LOCATION)

        #path_points = astar.a_star(section_matrix, mid_point, section_target_point)
        path_points = astar.a_star2(section_matrixes, mid_point, section_target_point)

        # logging.debug("section_matrixes[0]: {}".format(section_matrixes[7]))
        # logging.debug("section_matrixes[1]: {}".format(section_matrixes[7]))
        # logging.debug("section_matrixes[2]: {}".format(section_matrixes[7]))
        # logging.debug("section_matrixes[3]: {}".format(section_matrixes[7]))
        # logging.debug("section_matrixes[4]: {}".format(section_matrixes[7]))
        # logging.debug("section_matrixes[5]: {}".format(section_matrixes[7]))
        # logging.debug("section_matrixes[6]: {}".format(section_matrixes[7]))
        # logging.debug("section_matrixes[7]: {}".format(section_matrixes[7]))

        logging.debug("A* path_points: {}".format(path_points))

        if path_points:
            ## GOING FROM START POINT TO END POINT
            # astar_destination_point = path_points[-2]
            # for current_point in reversed(path_points[:-1]):
            #     logging.debug("current_point: {} ".format(current_point))
            #
            #     current_coord = MyCommon.Coordinates(current_point[0], current_point[1])
            #
            #     ## NOT DOING INTERMEDIATE COLLISION
            #     # if MyCommon.within_circle(current_coord, mid_coord, max_travel_distance) \
            #     #         and theta_clear(mid_coord, current_coord, section_matrix):
            #
            #     ## DOING INTERMEDIATE COLLISION
            #     if MyCommon.within_circle(current_coord, mid_coord, max_travel_distance) \
            #             and theta_clear(MyMoves, ship_id, current_coord):
            #
            #         astar_destination_point = current_point
            #         logging.debug("astar_destination_point: {} is good (no collision)".format(astar_destination_point))
            #     else:
            #         ## OUTSIDE THE CIRCLE OR COLLISION DETECTED
            #         break


            ## GOING FROM END POINT TO START POINT
            ## MAKING FIRST STEP (-2) AS DEFAULT (PREVENT JUST SITTING)
            astar_destination_point = path_points[-2]
            for current_point in path_points[:-2]:
                logging.debug("current_point: {} ".format(current_point))

                current_coord = MyCommon.Coordinates(current_point[0], current_point[1])

                ## DOING INTERMEDIATE COLLISION
                if MyCommon.within_circle(current_coord, mid_coord, max_travel_distance) \
                        and theta_clear(MyMoves, ship_id, current_coord):

                    astar_destination_point = current_point
                    logging.debug("astar_destination_point: {} is good (no collision)".format(astar_destination_point))
                    break
            # if astar_destination_point is None:
            #     ## THIS SHIP HAS COLLISION EVERYWHERE FROM A*
            #     ## EVEN STAYING AT THIS LOCATION HAS COLLISION
            #     ## NEED TO UPDATE THIS LATER
            #     logging.warning("ship_id: {} will definitely collide, but staying here for now".format(ship_id))
            #     astar_destination_point = mid_point

            astar_destination_coord = MyCommon.Coordinates(astar_destination_point[0], astar_destination_point[1])
            angle, thrust = MyCommon.get_angle_thrust(mid_coord, astar_destination_coord)

            logging.debug("A* angle {}".format(angle))

            logging.debug("temp_thrust {} vs thrust {}".format(temp_thrust, thrust))

            ## UPDATE ANGLE TO USE angle_towards_target
            ## ANGLE TOWARDS TARGET IS MORE ACCURATE SINCE ITS WITHOUT ROUNDING
            ## ONLY IF ANGLE IS CLOSE ENOUGH
            if temp_thrust == thrust and (angle - 5 <= angle_towards_target <= angle + 5):
                angle = angle_towards_target

            logging.debug("angle {} thrust {}".format(angle, thrust))

        else:
            ## NO A* PATH FOUND
            ## TARGET POINT MAY NOT BE REACHABLE (DUE TO OTHER SHIPS IN ITS IN POSITION MATRIX)
            ## ACTUAL TARGET POINT IS AVAILABLE SINCE IT WAS DETERMINED BY get_target_coord_towards_planet ?
            ## WHICH LOOKS FOR OTHER TARGET COORDS IF ITS ALREADY TAKEN

            astar_destination_coord = mid_coord  ## NEED TO UPDATE THIS LATER, GET A NEW TARGET!!
            angle, thrust = 0, 0
            logging.debug("No A* PATH FOUND!!!!!!!! ship_id: {} ship_coord: {} target_coord: {} target_distance: {} target_planet_id: {}".format(ship_id, ship_coord, target_coord, target_distance, target_planet_id))

    ## UPDATE POSITION MATRIX FOR THIS POINT WILL NOW BE TAKEN
    slope_from_mid_point = (astar_destination_coord.y - MyCommon.Constants.ASTAR_SQUARE_RADIUS, \
                            astar_destination_coord.x - MyCommon.Constants.ASTAR_SQUARE_RADIUS)
    taken_point = (ship_point[0] + slope_from_mid_point[0] , ship_point[1] + slope_from_mid_point[1])
    fill_position_matrix(MyMoves.position_matrix[7], taken_point, mining=False)

    return thrust, angle


def get_angle_target_if_outside_map(temp_target_coord, angle_towards_target, MyMoves, ship_coord, fake_target_thrust):

    if not (MyCommon.isInside_map(temp_target_coord, MyMoves)):  ## TARGET IS OUTSIDE MAP
        logging.debug("temp_target_coord is outside map")
        logging.debug("angle_towards_target: {}".format(angle_towards_target))
        if angle_towards_target < 45:
            angle_towards_target = angle_towards_target + 90
        elif angle_towards_target < 90:
            angle_towards_target = 0
        elif angle_towards_target < 135:
            angle_towards_target = angle_towards_target + 90
        elif angle_towards_target < 180:
            angle_towards_target = angle_towards_target - 90
        elif angle_towards_target < 225:
            angle_towards_target = angle_towards_target + 90
        elif angle_towards_target < 270:
            angle_towards_target = angle_towards_target - 90
        elif angle_towards_target < 315:
            angle_towards_target = 0
        else:
            angle_towards_target = 270

        logging.debug("updated angle_towards_target: {}".format(angle_towards_target))
        temp_target_coord = MyCommon.get_destination_coord(ship_coord, angle_towards_target, fake_target_thrust)

        return angle_towards_target, temp_target_coord

    return angle_towards_target, temp_target_coord


def theta_clear(MyMoves, ship_id, current_coord):   ## DOING INTERMEDIATE COLLISION
#def theta_clear(start_coord, target_coord, section_matrix): ## NOT DOING INTERMEDIATE COLLISION
    """
    RETURNS TRUE IF NO COLLISION BETWEEN THE TWO COORDS
    """
    ## DOING INTERMEDIATE COLLISION
    mid_point = (MyCommon.Constants.ASTAR_SQUARE_RADIUS, MyCommon.Constants.ASTAR_SQUARE_RADIUS) ## MIDDLE OF SECTION MATRIX
    mid_coord = MyCommon.Coordinates(mid_point[0], mid_point[1])

    ship_coord = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
    target_coord = MyCommon.Coordinates(ship_coord.y + (current_coord.y - mid_coord.y), ship_coord.x + (current_coord.x - mid_coord.x))
    angle = MyCommon.get_angle(ship_coord, target_coord)
    thrust = MyCommon.calculate_distance(ship_coord, target_coord)

    #safe_thrust = MyMoves.check_intermediate_collisions(ship_id, angle, thrust)
    safe_thrust = MyMoves.check_intermediate_collisions2(ship_id, angle, thrust)

    return thrust == safe_thrust

    # ## NOT DOING INTERMEDIATE COLLISION
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
    # angle = MyCommon.get_angle(start_coord, target_coord)
    # distance = MyCommon.calculate_distance(start_coord, target_coord)
    # unit_vector = -np.cos(np.radians(-angle - 90)), -np.sin(np.radians(-angle - 90))
    # start_point = [start_coord.y, start_coord.x]
    #
    # for multiplier in range(1,int(round(distance)) + 1):
    #     new_coord = [start_point[0] + multiplier * unit_vector[0],
    #                  start_point[1] + multiplier * unit_vector[1]]
    #     round_new_coord = (int(round(new_coord[0])), int(round(new_coord[1])))
    #
    #     if section_matrix[round_new_coord[0]][round_new_coord[1]] != 0:
    #         return False
    #
    # return True

def get_docking_coord(MyMoves, target_planet_id, ship_id):
    """
    RETURN TARGET COORD TOWARDS A SPECIFIED PLANET
    AND THE DISTANCE
    """
    ship_coord = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
    target_planet_coord = MyMoves.myMap.data_planets[target_planet_id]['coords']

    angle = MyCommon.get_angle(ship_coord, target_planet_coord)

    ## WE CAN DOCK ALREADY, SO JUST RETURN DISTANCE 0 SO WE CAN JUST DOCK
    if ship_can_dock(MyMoves, ship_coord, target_planet_id):
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

        if isPositionMatrix_free(position_matrix, round_coord) and ship_can_dock(MyMoves, new_coord, target_planet_id):
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

        if isPositionMatrix_free(position_matrix, round_coord) and ship_can_dock(MyMoves, new_target_coord, target_planet_id):
        #if isPositionMatrix_free(position_matrix, round_coord):
            logging.debug("Good enough 2")
            #ship_can_dock(MyMoves, round_coord, target_planet_id)
            return round_coord

        ## GOING COUNTER CLOCKWISE
        new_angle_left = planet_angle_left - angle
        new_target_coord_left = MyCommon.get_destination_coord(planet_center, new_angle_left, hypotenuse)
        round_point = MyCommon.get_rounded_point(new_target_coord_left)
        round_coord = MyCommon.Coordinates(round_point[0], round_point[1])

        if isPositionMatrix_free(position_matrix, round_coord) and ship_can_dock(MyMoves, new_target_coord_left, target_planet_id):
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
    """
    logging.debug("At coord: {}.  Position_matrix value is: {}".format(coord, position_matrix[int(round(coord.y))][int(round(coord.x))]))

    point = MyCommon.get_rounded_point(coord)
    return position_matrix[point[0]][point[1]] == 0


def ship_can_dock(MyMoves, coord, target_planet_id):
    """
    CHECK IF A SHIP CAN DOCK ON ITS CURRENT COORDINATES
    FIRST USING DOCKABLE MATRIX
    THEN IF NOT, DOUBLE CHECK DISTANCE FROM PLANET
    """

    ## NO TARGET PLANET
    if target_planet_id is None:
        return False

    target_planet_coord = MyMoves.myMap.data_planets[target_planet_id]['coords']
    target_radius = MyMoves.myMap.data_planets[target_planet_id]['radius']
    d = MyCommon.calculate_distance(coord, target_planet_coord, rounding=False)
    dock_val = d - target_radius

    ## DOCKING RADIUS NOT REALLY 4??? SUTRACT XXX
    #if d <= target_radius + MyCommon.Constants.DOCK_RADIUS - 0.22:
    if dock_val < MyCommon.Constants.DOCK_RADIUS:
        return True

    ## TOO FAR
    return False





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
