
from heapq import *
import logging
import MyCommon
from models.data import Matrix_val


def heuristic(a, b):
    """
    IS THE DISTANCE, IF TAKEN THE SQRT
    """
    return (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2


def isBadNeighbor(array,neighbor):
    """
    CHECKS IF THE NEIGHBOR IS WITHIN THE ARRAY BOUNDARIES
    OR IF THE NEIGHBOR IS AN OBSTRUCTION
    """
    if 0 <= neighbor[0] < array.shape[0] and 0 <= neighbor[1] < array.shape[1] \
            and array[neighbor[0]][neighbor[1]] == MyCommon.Constants.NON_OBSTRUCTION:
        ## NEIGHBOR COORDINATE IS WITHIN THE ARRAY BOUNDARIES
        ## AND VALID NEIGHBOR
        return False
                
    ## OUTSIDE ARRAY Y OR X BOUNDARY
    ## OR ITS AN OBSTRUCTION (BAD/SKIP)
    return True
        

def a_star2(arrays, start_point, goal_point):
    """
    A* ALGO TO GET THE BEST PATH FROM start TO goal

    UPDATED A* ABOVE, THIS TIME IT WILL TAKE MULTIPLE ARRAYS (INCLUDING INTERMEDIATE STEPS)

    ARRAY WILL BE A DICTIONARY OF STEPS
    """
    
    ## MAKE SURE COORDS ARE ROUNDED AS INTS
    start = (int(round(start_point[0])),int(round(start_point[1])))
    goal = (int(round(goal_point[0])),int(round(goal_point[1])))

    ## HOW FAR AWAY IS THE GOAL DISTANCE
    goal_distance = MyCommon.calculate_distance(
                        MyCommon.Coordinates(start_point[0], start_point[1]),
                        MyCommon.Coordinates(goal_point[0], goal_point[1])
                        )

    ## SOMETIMES GOAL CAN BE VERY FAR, BUT LIMIT TO 7 ONLY
    goal_distance = min(7, goal_distance)

    ## THIS WILL BE THE INCREASE IN INDEX (POSITION MATRIX) PER STEP
    index_per_step = 7/goal_distance  

    logging.debug("a_star: start: {} goal: {}".format(start, goal))

    ## NEIGHBORS IN NORTH, EAST, SOUTH, WEST DIRECTIONS, PLUS DIAGONALS
    neighbors = [(-1,0),(0,1),(1,0),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]

    visited_pts = set()
    came_from = {}
    gscore = {start:0}                      ## ACTUAL DISTANCE FROM START
    fscore = {start:heuristic(start, goal)} ## GSCORE PLUS DISTANCE TO GOAL
    myheap = []

    ## HEAP CONSIST OF FSCORE, COORD
    heappush(myheap, (fscore[start], start))

    while myheap:
        curr_pt = heappop(myheap)[1]

        if curr_pt == goal: ## GOAL REACHED
            data_pts = []
            while curr_pt in came_from:
                data_pts.append(curr_pt)
                curr_pt = came_from[curr_pt]
            data_pts.append(start) ## APPEND STARTING LOCATION
            return data_pts ## FIRST COORD WILL BE AT THE END!

        visited_pts.add(curr_pt)
        for r, c in neighbors:
            neighbor_pt = (curr_pt[0] + r, curr_pt[1] + c)
            ## tentative_g_score IS BASICALLY THE DISTANCE/STEPS AWAY FROM START
            tentative_g_score = gscore[curr_pt] + heuristic(curr_pt, neighbor_pt)

            ## HIGHEST INDEX CAN ONLY BE 7 STEPS (WE ONLY HAVE 7 POSITION MATRIX)
            index_value = min(7, int(round(tentative_g_score * index_per_step)))

            ## BASE ON INDEX IN POSITION MATRIX
            ## THIS IS TO TAKE INTO ACCOUNT INTERMEDIATE STEPS
            if isBadNeighbor(arrays[index_value], neighbor_pt):
                if neighbor_pt == goal:
                    pass
                else:
                    continue

            if neighbor_pt in visited_pts and tentative_g_score >= gscore.get(neighbor_pt, 0): ## 0 DEFAULT VALUE
                continue

            ## IF A BETTER GSCORE IS FOUND FOR THAT NEIGHBOR COORD OR NEIGHBOR COORD NOT IN HEAP
            if  tentative_g_score < gscore.get(neighbor_pt, 0) or neighbor_pt not in (i[1] for i in myheap):
                came_from[neighbor_pt] = curr_pt   ## NEIGHBOR COORD CAME FROM CURRENT COORD
                gscore[neighbor_pt] = tentative_g_score  ## NEIGHBOR DISTANCE FROM START
                fscore[neighbor_pt] = tentative_g_score + heuristic(neighbor_pt, goal)  ## GSCORE PLUS DISTANCE TO GOAL
                heappush(myheap, (fscore[neighbor_pt], neighbor_pt))  ## PUSH NEIGHBOR TO HEAP

    return []


def get_thrust_angle_from_Astar(MyMoves, ship_id, target_coord, target_distance, target_planet_id, second_call=False):
    """
    RETURN THRUST AND ANGLE BASED SHIP ID AND TARGET COORD ONLY

    WE"LL USE LOCAL/SECTIONED A*
    """
    logging.debug("get_thrust_angle_from_Astar: ship_id {}, target_coord {}, target_distance {}, target_planet_id {}".format(
       ship_id, target_coord, target_distance, target_planet_id
    ))

    square_radius = MyCommon.Constants.ASTAR_SQUARE_RADIUS
    circle_radius = MyCommon.Constants.ASTAR_CIRCLE_RADIUS
    max_travel_distance = MyCommon.Constants.MAX_TRAVEL_DISTANCE
    fake_target_thrust = MyCommon.Constants.ASTAR_SQUARE_RADIUS ## 10
    ship_coord = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
    ship_point = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['point']

    ## GET ANGLE TO TARGET
    angle_towards_target = MyCommon.get_angle(ship_coord, target_coord)

    ## GET SECTION (FOR A* 2nd Version)
    ## GETTING SECTIONS FROM 7 POSITION MATRIXES
    pad_values = -1
    section_matrixes = {}
    for step in range(1,8):
        section_matrixes[step] = MyCommon.get_circle_in_square(
                                    MyMoves.position_matrix[step], ship_coord, circle_radius, square_radius, pad_values
                                   )

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
    angle_towards_target, temp_target_coord = get_angle_target_if_outside_map(
                                                     temp_target_coord, angle_towards_target,
                                                     MyMoves, ship_coord, fake_target_thrust
                                                     )


    temp_target_point = (int(round(temp_target_coord.y)) - int(round(ship_coord.y)), \
                         int(round(temp_target_coord.x)) - int(round(ship_coord.x)))
    section_target_point = (int(MyCommon.Constants.ASTAR_SQUARE_RADIUS + temp_target_point[0]), \
                            int(MyCommon.Constants.ASTAR_SQUARE_RADIUS + temp_target_point[1]))

    logging.debug("get_thrust_angle_from_Astar:: section_target_point {}".format(section_target_point))

    ## MID POINT OF THE SECTION MATRIX IS THE STARTING POINT (SHIP COORD IN SECTION MATRIX IS JUST THE MIDDLE)
    mid_point = (MyCommon.Constants.ASTAR_SQUARE_RADIUS, MyCommon.Constants.ASTAR_SQUARE_RADIUS) ## MIDDLE OF SECTION MATRIX
    mid_coord = MyCommon.Coordinates(mid_point[0], mid_point[1])

    if mid_point == section_target_point:

        ## REACHED ITS TARGET
        logging.debug("target reached!")

        ## POSSIBLE THAT DUE TO ROUNDING, IT STIL CANNOT DOCK
        if not(MyCommon.ship_can_dock(MyMoves, ship_coord, target_planet_id)) and not(MyMoves.retreating):
            logging.debug("Cannot dock due to rounding, move 1 forward still. ship_id: {}".format(ship_id))

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


        path_points = a_star2(section_matrixes, mid_point, section_target_point)


        # logging.debug("section_matrixes[1]: {}".format(section_matrixes[1]))
        # logging.debug("section_matrixes[2]: {}".format(section_matrixes[2]))
        # logging.debug("section_matrixes[3]: {}".format(section_matrixes[3]))
        # logging.debug("section_matrixes[4]: {}".format(section_matrixes[4]))
        # logging.debug("section_matrixes[5]: {}".format(section_matrixes[5]))
        # logging.debug("section_matrixes[6]: {}".format(section_matrixes[6]))
        logging.debug("section_matrixes[7]: {}".format(section_matrixes[7]))


        logging.debug("A* path_points: {}".format(path_points))
        logging.debug("A* path_points length: {}".format(len(path_points)))

        if path_points:
            ## MAKING LAST STEP (OR ORIGIN) AS DEFAULT
            ## PREVENTS KNOWN COLLISIONS TO HAPPEN (MIGHT KEEP UNITS NOT MOVING THOUGH)
            step1_point = path_points[-2]
            astar_destination_point = path_points[-1]
            for current_point in path_points[:-1]:
                logging.debug("current_point: {} ".format(current_point))

                current_coord = MyCommon.Coordinates(current_point[0], current_point[1])

                ## DOING INTERMEDIATE COLLISION
                isClear, collision_value = theta_clear(MyMoves, ship_id, current_coord)
                if MyCommon.within_circle(current_coord, mid_coord, max_travel_distance) and isClear:
                    astar_destination_point = current_point
                    logging.debug("astar_destination_point: {} is good (no collision)".format(astar_destination_point))
                    break

            logging.debug("astar_destination_point {} collision_value {}".format(astar_destination_point, collision_value))

            ## IF ITS THE SAME AS FIRST COORD, AND COLLISION VALUE IS NOT OUR SHIP (1), THEN GO TO STEP 1
            ## WILL SKIP, PLANETS OR CORNER IN FILL MATRIX
            if astar_destination_point == path_points[-1] and collision_value is not None \
                    and (int(collision_value) == Matrix_val.ALLY_SHIP.value or
                         int(collision_value) == Matrix_val.ALLY_SHIP_CORNER.value or
                         int(collision_value) == Matrix_val.PREDICTION_PLANET.value*2) :
                logging.debug("Everything is bad, but will go step 1")
                astar_destination_coord = MyCommon.Coordinates(step1_point[0], step1_point[1])
                angle, thrust = MyCommon.get_angle_thrust(mid_coord, astar_destination_coord)

                new_point = MyCommon.get_destination_coord(ship_coord,angle,thrust,rounding=True)

                ## BEFORE, BASICALLY GOES TO STEP 1 IF ITS A CORNER
                ## BUT GETS A NEW ANGLE IF ITS A SHIP/PLANET
                if MyMoves.position_matrix[7][new_point.y, new_point.x] == Matrix_val.ALLY_SHIP.value or \
                    MyMoves.position_matrix[7][new_point.y, new_point.x] == Matrix_val.PREDICTION_PLANET.value*2:
                    ## WILL DEFINITELY COLLIDE TO ONE OF OUR SHIPS
                    ## GET NEW ANGLE
                    logging.debug("Colliding to ally ship, do prevention")
                    angle, thrust = get_new_angle_step1(MyMoves, ship_coord, angle)

                ## NOW GET A NEW ANGLE IF ITS OUR SHIP OR CORNER OF OUR SHIP
                ## WILL DEFINITELY COLLIDE TO ONE OF OUR SHIPS
                ## GET NEW ANGLE
                # logging.debug("Colliding to ally ship, do prevention")
                # angle, thrust = get_new_angle_step1(MyMoves, ship_coord, angle)

            else:
                astar_destination_coord = MyCommon.Coordinates(astar_destination_point[0], astar_destination_point[1])
                angle, thrust = MyCommon.get_angle_thrust(mid_coord, astar_destination_coord)

            logging.debug("A* angle {}".format(angle))

            logging.debug("temp_thrust {} vs thrust {}".format(temp_thrust, thrust))

            ## UPDATE ANGLE TO USE angle_towards_target
            ## ANGLE TOWARDS TARGET IS MORE ACCURATE SINCE ITS WITHOUT ROUNDING
            ## ONLY IF ANGLE IS CLOSE ENOUGH
            ## THIS ACTUALLY CAUSES COLLISIONS!! CHANGED FROM 5 to 4 TO FIX A COLLISION
            ## BUT THEN A COLLISION WAS STILL HAPPENING AT 4 WITH ANOTHER GAME, SO COMMENTING OUT
            ## COMMENTING THIS OUT MADE BEST BOT SO FAR (BOT 68, GETTING AS LOW AS RANK 63)
            ## BUT CAUSES DOCKING ISSUE, LEAVING TO 2 CAN STILL CAUSE COLLISION THOUGH (STILL HAS DOCKING ISSUES)
            # if temp_thrust == thrust and (angle - 2 <= angle_towards_target <= angle + 2):
            #     angle = angle_towards_target

            logging.debug("angle {} thrust {}".format(angle, thrust))

        else:
            ## NO A* PATH FOUND
            ## TARGET POINT MAY NOT BE REACHABLE (DUE TO OTHER SHIPS IN ITS IN POSITION MATRIX)
            ## ACTUAL TARGET POINT IS AVAILABLE SINCE IT WAS DETERMINED BY get_target_coord_towards_planet ?
            ## WHICH LOOKS FOR OTHER TARGET COORDS IF ITS ALREADY TAKEN
            astar_destination_coord = mid_coord  ## NEED TO UPDATE THIS LATER, GET A NEW TARGET!!
            angle, thrust = 0, 0
            logging.debug("No A* PATH FOUND!!!!!!!! ship_id: {} ship_coord: {} target_coord: {} target_distance: {} target_planet_id: {}".format(ship_id, ship_coord, target_coord, target_distance, target_planet_id))

            ## GET CLOSER TO TARGET
            if not(second_call): ## PREVENT FOREVER RECURSION
                seek_value = Matrix_val.ALLY_SHIP_CORNER.value
                value_coord = MyCommon.get_coord_of_value_in_angle(MyMoves.position_matrix[7], ship_coord, seek_value, angle_towards_target, move_back=1)

                if not(value_coord):
                    seek_value = Matrix_val.ALLY_SHIP.value
                    value_coord = MyCommon.get_coord_of_value_in_angle(MyMoves.position_matrix[7], ship_coord, seek_value, angle_towards_target, move_back=1)

                if value_coord:
                    logging.debug("new target coord: {}".format(value_coord))
                    distance = MyCommon.calculate_distance(ship_coord, value_coord)
                    thrust, angle = get_thrust_angle_from_Astar(MyMoves, ship_id, value_coord, distance, target_planet_id=None, second_call=True)


    ## UPDATE POSITION MATRIX FOR THIS POINT WILL NOW BE TAKEN
    ## WAS FILLING POSITION TO EARLY?? COMMENTING THIS OUT MAKES IT BETTER!!
    # slope_from_mid_point = (astar_destination_coord.y - MyCommon.Constants.ASTAR_SQUARE_RADIUS, \
    #                         astar_destination_coord.x - MyCommon.Constants.ASTAR_SQUARE_RADIUS)
    # taken_point = (ship_point[0] + slope_from_mid_point[0] , ship_point[1] + slope_from_mid_point[1])
    # fill_position_matrix(MyMoves.position_matrix[7], taken_point, mining=False)

    return thrust, angle




def get_new_angle_step1(MyMoves, ship_coord, angle):
    """
    AT THIS POINT, IT HAS BEEN DETERMINED THAT THE PATH IDENTIFIED FROM A* IS NO GOOD (COLLISIONS EVERYWHERE)
    COLLIDING WITH ALLY SHIPS, GET NEW COORD THATS FREE (AROUND ITS CURRENT POSITION)
    THRUST IS ONLY SET TO 1
    """
    thrust = 1

    ##BEFORE BASE ON ANGLE PROVIDED
    for _ in range(7):
        new_angle = angle + 45
        new_angle = new_angle - 360 if new_angle > 360 else new_angle ## LIMIT TO 360
        new_point = MyCommon.get_destination_coord(ship_coord, new_angle, thrust, rounding=True)

        ## CHECK BOTH [7] AND [6] ARE FREE OF COLLISIONS
        if not(
               MyMoves.position_matrix[7][new_point.y, new_point.x] == Matrix_val.ALLY_SHIP.value \
               or MyMoves.position_matrix[7][new_point.y, new_point.x] == Matrix_val.ALLY_SHIP_CORNER.value
               ):
            return new_angle, thrust

        angle = new_angle

    logging.debug("THIS SHIP IS COMPLETELY SURROUNDED!! COLLIDING!!")
    return 0, 0 ## NO FREE ANGLE FOUND

    ## JUST GO UP, DOWN, LEFT, RIGHT, THEN DIAGONALS
    # for new_angle in [0, 90, 180, 270, 45, 135, 225, 315]:
    #     new_point = MyCommon.get_destination_coord(ship_coord, new_angle, thrust, rounding=True)
    #
    #     ## CHECK BOTH [7] AND [6] ARE FREE OF COLLISIONS
    #     if not(
    #          MyMoves.position_matrix[7][new_point.y, new_point.x] == Matrix_val.ALLY_SHIP.value \
    #             or MyMoves.position_matrix[7][new_point.y, new_point.x] == Matrix_val.ALLY_SHIP_CORNER.value
    #            ) \
    #        and not(
    #             MyMoves.position_matrix[6][new_point.y, new_point.x] == Matrix_val.ALLY_SHIP.value \
    #               or MyMoves.position_matrix[6][new_point.y, new_point.x] == Matrix_val.ALLY_SHIP_CORNER.value
    #             ):
    #         return new_angle, thrust
    #
    #     angle = new_angle
    #
    # logging.debug("THIS SHIP IS COMPLETELY SURROUNDED!! COLLIDING!!")
    # return 0, 0 ## NO FREE ANGLE FOUND


def get_angle_target_if_outside_map(temp_target_coord, angle_towards_target, MyMoves, ship_coord, fake_target_thrust):
    """
    IF CURRENT TARGET IS OUTSIDE THE MAP
    WE TRY TO DETERMINE A NEW TARGET INSIDE THE MAP
    """

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
    BASICALLY CHECKING IF THIS ANGLE IS CLEAR OF COLLISIONS
    """
    ## DOING INTERMEDIATE COLLISION
    mid_point = (MyCommon.Constants.ASTAR_SQUARE_RADIUS, MyCommon.Constants.ASTAR_SQUARE_RADIUS) ## MIDDLE OF SECTION MATRIX
    mid_coord = MyCommon.Coordinates(mid_point[0], mid_point[1])

    ship_coord = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
    target_coord = MyCommon.Coordinates(ship_coord.y + (current_coord.y - mid_coord.y), ship_coord.x + (current_coord.x - mid_coord.x))
    angle = MyCommon.get_angle(ship_coord, target_coord)
    thrust = MyCommon.calculate_distance(ship_coord, target_coord)

    #safe_thrust = MyMoves.check_intermediate_collisions(ship_id, angle, thrust)
    safe_thrust, collision_value = MyMoves.check_intermediate_collisions2(ship_id, angle, thrust)

    return thrust == safe_thrust, collision_value






