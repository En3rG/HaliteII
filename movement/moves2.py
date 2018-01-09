import logging
from testing.test_logs import log_players, log_planets, log_myShip, log_dimensions
import hlt
from enum import Enum
import math
from models.data import ShipTasks
import MyCommon
import heapq
import initialization.astar as astar
import movement.attacking as attacking
import movement.expanding as expanding
import movement.expanding2 as expanding2
import movement.attacking as attacking
import copy
from models.data import Matrix_val
import numpy as np
import datetime


"""
NOTE!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!1

when deciding where to go, should we place -1 on all enemy ranges, and if 2 enemy can attack that area,
it will then have -2.  This can help us decide whether to move there or not. Or whether we can win or not

"""

class Target():
    NOTHING = -1
    PLANET = 0
    SHIP = 1

class MyMoves():
    """
    EXAMPLE COMMAND QUEUE TO BE SENT TO HALITE ENGINE:
    'd 0 2'      ## DOCKING SHIP ID 0 TO PLANET 2
    't 1 3 353'  ## MOVE SHIP ID 1 WITH SPEED 3 AND ANGLE 353
    """
    def __init__(self, myMap, myMatrix, EXP):
        self.command_queue = []
        self.EXP = EXP
        self.myMap = myMap
        self.myMatrix = myMatrix
        self.position_matrix = {1: copy.deepcopy(myMatrix.matrix[myMap.my_id][0]),
                                2: copy.deepcopy(myMatrix.matrix[myMap.my_id][0]),
                                3: copy.deepcopy(myMatrix.matrix[myMap.my_id][0]),
                                4: copy.deepcopy(myMatrix.matrix[myMap.my_id][0]),
                                5: copy.deepcopy(myMatrix.matrix[myMap.my_id][0]),
                                6: copy.deepcopy(myMatrix.matrix[myMap.my_id][0]),
                                7: copy.deepcopy(myMatrix.matrix[myMap.my_id][0]),}  ## SECOND ONE IS HP MATRIX

        self.get_my_moves()


    def get_my_moves(self):
        """
        GET THE MOVES PER SHIP ID
        """
        if self.myMap.myMap_prev is None:
            # FIRST TURN

            ## GET BEST PLANET
            target_planet_id = self.EXP.best_planet_id

            ## GET ANGLE OF CENTROID TO BEST PLANET
            target_planet_coord = self.myMap.data_planets[target_planet_id]['coords']
            angle = MyCommon.get_angle(self.EXP.myStartCoords, target_planet_coord)

            ## GET MATRIX OF JUST THE TARGET PLANET
            planet_matrix = self.EXP.planet_matrix[target_planet_id]

            seek_value = Matrix_val.PREDICTION_PLANET.value

            first_heap = [] ## DIFFERENT THAN HEAP TO BE USED LATER

            ## PLACE SHIPS IN HEAP BASE ON DISTANCE
            for ship_id in self.myMap.ships_new:
                ship_coord = self.myMap.data_ships[self.myMap.my_id][ship_id]['coords']
                value_coord = MyCommon.get_coord_of_value_in_angle(planet_matrix, ship_coord, seek_value, angle)

                if value_coord:
                    reverse_angle = MyCommon.get_reversed_angle(angle)  ## REVERSE DIRECTION/ANGLE
                    target_coord = MyCommon.get_destination_coord(value_coord, reverse_angle, MyCommon.Constants.MOVE_BACK)  ## MOVE BACK
                else:
                    ## DIDNT FIND. SHOULDNT HAPPEN FOR THE STARTING 3 SHIPS
                    logging.error("One of the starting ships didnt see the best planet, given the angle.")

                distance = MyCommon.calculate_distance(ship_coord, target_coord, rounding=False)

                heapq.heappush(first_heap, (distance, ship_id, target_planet_id, ship_coord, target_coord))

            while first_heap:
                distance, ship_id, target_planet_id, ship_coord, target_coord = heapq.heappop(first_heap)

                ## DOUBLE CHECK IF PLANET IS STILL AVAILABLE
                if not (expanding.has_room_to_dock(self, target_planet_id)):
                    ## NO MORE ROOM, GET A NEW PLANET ID
                    target_planet_id = expanding.get_next_target_planet(self, ship_id)
                    target_coord = self.myMap.data_planets[target_planet_id]['coords']
                    distance = MyCommon.calculate_distance(ship_coord, target_coord, rounding=False)

                ## GET THRUST AND ANGLE
                thrust, angle = expanding2.get_thrust_angle_from_Astar(self, ship_id, target_coord, distance, target_planet_id)

                ## ADD TO COMMAND QUEUE
                self.command_queue.append(MyCommon.convert_for_command_queue(ship_id, thrust, angle))

                ## SET SHIP STATUSES
                self.set_ship_statuses(ship_id, target_planet_id, ship_coord, angle, thrust, target_coord)

        else:
            ## MOVE ALREADY MINING SHIPS FIRST
            for ship_id in self.myMap.ships_mining_ally:
                self.set_ship_moved_and_fill_position(ship_id, angle=0, thrust=0, mining=True)

            ## LOOK FOR SHIPS ABOUT TO BATTLE
            ## MOVE THOSE SHIPS
            attacking.get_battling_ships(self)

            ## USING HEAPQ
            ## INITIALLY THOUGHT USING HEAP WAS SLOW
            ## TURNS OUT A* IS RUNNING LONGER SINCE PATH IS UNREACHABLE, DUE TO ANOTHER SHIP BLOCKING ITS DESTINATION

            ## GET TARGET AND DISTANCES
            heap = self.get_target_and_distances()

            ## MOVE OTHERS REMAINING
            # USING HEAPQ POP
            while heap:
                planet_distance, enemy_distance, ship_id, target_planet_id, enemy_target_coord = heapq.heappop(heap)

                ship_coord = self.myMap.data_ships[self.myMap.my_id][ship_id]['coords']

                logging.debug("at heap ship_id: {} ship_coord: {} planet_distance: {} target_planet_id: {} enemy_distance: {} enemy_target_coord: {}".format(ship_id, ship_coord,planet_distance, target_planet_id, enemy_distance, enemy_target_coord))

                ## HAS ENEMY TARGET COORD
                ## DISTANCE TO ENEMY SHOULD BE GOOD, MOVE THIS SHIP NOW
                if enemy_target_coord is not None:
                    thrust, angle = expanding2.get_thrust_angle_from_Astar(self, ship_id, enemy_target_coord, enemy_distance, target_planet_id=None)
                    attacking.set_commands_status(self, ship_id, thrust=thrust, angle=angle)
                    continue

                else:
                    ## DOUBLE CHECK IF PLANET IS STILL AVAILABLE
                    if not(expanding.has_room_to_dock(self, target_planet_id)):
                        ## NO MORE ROOM, GET A NEW PLANET ID
                        new_target_planet_id = expanding.get_next_target_planet(self, ship_id)

                        logging.debug("new_target_planet_id: {} target_planet_id: {}".format(new_target_planet_id, target_planet_id))

                        if new_target_planet_id is None:
                            ## NO MORE PLANETS TO CONQUER AT THIS TIME
                            ## ADD BACK TO HEAP
                            planet_distance = MyCommon.Constants.BIG_DISTANCE
                            enemy_distance, enemy_target_coord = attacking.closest_section_with_enemy(self, ship_id, move_now=False)
                            heapq.heappush(heap, (planet_distance, enemy_distance, ship_id, target_planet_id, enemy_target_coord))
                            continue

                        if new_target_planet_id != target_planet_id:
                            ## TARGET PLANET CHANGED.  RECALCULATE DISTANCE, AND PUT BACK TO HEAP
                            planet_coord = self.myMap.data_planets[new_target_planet_id]['coords']
                            planet_radius = self.myMap.data_planets[new_target_planet_id]['radius']
                            planet_distance = MyCommon.calculate_distance(ship_coord, planet_coord, rounding=False) - planet_radius
                            enemy_distance = 0
                            enemy_target_coord = None

                            ## ADD TO BACK DISTANCE HEAP
                            heapq.heappush(heap, (planet_distance, enemy_distance, ship_id, new_target_planet_id, enemy_target_coord))

                            continue

                    if target_planet_id is None:
                        ## NO MORE PLANETS TO CONQUER AT THIS TIME
                        #attacking.closest_section_in_war(self, ship_id)
                        # attacking.closest_section_with_enemy(self, ship_id, move_now=True)
                        # continue

                        ## NO MORE PLANETS TO CONQUER AT THIS TIME
                        ## ADD BACK TO HEAP
                        planet_distance = MyCommon.Constants.BIG_DISTANCE
                        enemy_distance, enemy_target_coord = attacking.closest_section_with_enemy(self, ship_id, move_now=False)
                        heapq.heappush(heap, (planet_distance, enemy_distance, ship_id, target_planet_id, enemy_target_coord))

                        continue

                    ## ADDING THIS TO GET A NEW COORD, SINCE PATH/DESTINATION MIGHT NOT BE REACHABLE DUE TO OTHER SHIPS
                    target_coord, distance = expanding2.get_docking_coord(self, target_planet_id, ship_id)

                    if distance == 0:
                        ## WE CAN DOCK ALREADY
                        safe_thrust = 0
                        angle = 0
                        logging.debug("get_docking_coord distance 0 docking!!")
                        self.command_queue.append(MyCommon.convert_for_command_queue(ship_id, target_planet_id))

                    elif target_coord is None:
                        ## DOCKING COORD NOT FOUND?
                        logging.warning("Why is there no docking coord for ship_id: {} target_planet_id: {}".format(ship_id,target_planet_id ))
                        angle = 0
                        safe_thrust = 0

                    else:
                        ## GET THRUST AND ANGLE
                        thrust, angle = expanding2.get_thrust_angle_from_Astar(self, ship_id, target_coord, distance, target_planet_id)
                        logging.debug("get_thrust_angle_from_Astar thrust: {} angle: {}".format(thrust, angle))

                        #safe_thrust = self.check_intermediate_collisions(ship_id, angle, thrust)
                        safe_thrust = thrust  ## NOT LOOKING FOR INTERMEDIATE COLLLISIONS

                        if thrust == 0:
                            self.command_queue.append(MyCommon.convert_for_command_queue(ship_id, target_planet_id))

                        else:
                            ## ADD TO COMMAND QUEUE
                            self.command_queue.append(MyCommon.convert_for_command_queue(ship_id, safe_thrust, angle))

                    ## SET SHIP STATUSES
                    self.set_ship_statuses(ship_id, target_planet_id, ship_coord, angle, safe_thrust, target_coord)



    def get_target_and_distances(self):
        """
        GET SHIP'S TARGET AND DISTANCE TO THAT TARGET COORD

        IF NO MORE PLANETS AVAILABLE, GET COORD OF CLOSEST SECTION WITH ENEMY
        """
        heap = []

        for ship_id, ship in self.myMap.data_ships[self.myMap.my_id].items():
            if ship_id not in self.myMap.ships_moved_already:
                try:
                    target_planet_id = self.myMap.myMap_prev.data_ships[self.myMap.my_id][ship_id]['target_id'][1]

                    ## IF PLANET NO LONGER EXISTS, GET A NEW PLANET
                    if target_planet_id not in self.myMap.planets_existing:
                        target_planet_id = expanding.get_next_target_planet(self, ship_id)
                except:
                    ## SHIP DIDNT EXIST BEFORE (NEW SHIP)
                    ## OR
                    ## SHIP HAS NO TARGET SET
                    target_planet_id = expanding.get_next_target_planet(self, ship_id)

                if target_planet_id is None:
                    ## NO MORE PLANETS TO CONQUER AT THIS TIME
                    #self.set_ship_moved_and_fill_position(ship_id, angle=0, thrust=0, mining=True)
                    #attacking.closest_section_in_war(self, ship_id)
                    planet_distance = MyCommon.Constants.BIG_DISTANCE
                    enemy_distance, enemy_target_coord = attacking.closest_section_with_enemy(self, ship_id, move_now=False)
                    heapq.heappush(heap, (planet_distance, enemy_distance, ship_id, target_planet_id, enemy_target_coord))

                else:
                    ## NO NEED TO DETERMINE DOCKING COORD
                    ## SINCE COORDINATE DETERMINED HERE MAY NO LONGER EXISTS DUE TO OTHER SHIPS GETTING HERE FIRST
                    #target_coord, distance = expanding2.get_docking_coord(self, target_planet_id, ship_id)

                    # if target_coord is None:
                    #     ## NO AVAILABLE SPOT NEAR THE TARGET
                    #     self.set_ship_moved_and_fill_position(ship_id, angle=0, thrust=0)
                    #     continue

                    ## CALCULATE PLANET DISTANCE
                    ship_coord = self.myMap.data_ships[self.myMap.my_id][ship_id]['coords']
                    planet_coord = self.myMap.data_planets[target_planet_id]['coords']
                    planet_radius = self.myMap.data_planets[target_planet_id]['radius']
                    planet_distance = MyCommon.calculate_distance(ship_coord, planet_coord, rounding=False) - planet_radius
                    enemy_distance = 0
                    enemy_target_coord = None

                    ## ADD TO DISTANCE HEAP
                    heapq.heappush(heap, (planet_distance, enemy_distance, ship_id, target_planet_id, enemy_target_coord))

        return heap

    def check_intermediate_collisions(self, ship_id, angle, thrust):
        """
        CHECK IF AN INTERMEDIATE COLLISION EXISTS
        IF SO, RETURN THE THRUST THAT HAS NO COLLISION
        """

        ship_coord = self.myMap.data_ships[self.myMap.my_id][ship_id]['coords']
        dx = thrust / 7
        prev_thrust = 0

        logging.debug("check_intermediate_collisions thrust: {}".format(thrust))

        for step_num in range(1, 7):
            curr_thrust = int(round(dx * step_num))

            logging.debug("curr_thrust {}".format(curr_thrust))

            intermediate_coord = MyCommon.get_destination_coord(ship_coord, angle, curr_thrust)
            intermediate_point = MyCommon.get_rounded_point(intermediate_coord)

            no_collision = self.no_intermediate_collision(step_num, intermediate_point)
            if no_collision:
                prev_thrust = curr_thrust
            else:
                logging.debug(
                    "Collision detected! ship_id: {} intermediate_point: {} step_num: {} . Will return prev_thrust: {}".format(
                        ship_id, intermediate_point, step_num, prev_thrust))
                return prev_thrust  ## CURRENT THRUST HAS COLLISION

        return thrust  ## RETURN ORIGINAL THRUST

    def check_intermediate_collisions2(self, ship_id, angle, thrust):
        """
        CHECK IF AN INTERMEDIATE COLLISION EXISTS
        IF SO, RETURN THE THRUST THAT HAS NO COLLISION
        """

        ship_coord = self.myMap.data_ships[self.myMap.my_id][ship_id]['coords']
        ship_point = MyCommon.get_rounded_point(ship_coord)

        if thrust == 0: ## SHIP STAYING ITS IN CURRENT LOCATION
            ##
            if all([self.no_intermediate_collision(1, ship_point),
                    self.no_intermediate_collision(2, ship_point),
                    self.no_intermediate_collision(3, ship_point),
                    self.no_intermediate_collision(4, ship_point),
                    self.no_intermediate_collision(5, ship_point),
                    self.no_intermediate_collision(6, ship_point),
                    self.no_intermediate_collision(7, ship_point)]):
                logging.debug("Thurst is 0 with no collision")
                return thrust ## NO COLLISION
            else:
                logging.debug("Thurst is 0 BUT has collision")
                return -1


        dx = thrust / 7
        prev_thrust = 0

        logging.debug("check_intermediate_collisions thrust: {}".format(thrust))

        for step_num in range(1, 8):
            curr_thrust = int(round(dx * step_num))

            logging.debug("curr_thrust {}".format(curr_thrust))

            intermediate_coord = MyCommon.get_destination_coord(ship_coord, angle, curr_thrust)
            intermediate_point = MyCommon.get_rounded_point(intermediate_coord)

            no_collision = self.no_intermediate_collision(curr_thrust, intermediate_point)
            if no_collision:
                prev_thrust = curr_thrust
            else:
                logging.debug(
                    "Collision detected! ship_id: {} intermediate_point: {} step_num: {} . Will return prev_thrust: {}".format(
                        ship_id, intermediate_point, step_num, prev_thrust))
                return prev_thrust  ## CURRENT THRUST HAS COLLISION

        return thrust  ## RETURN ORIGINAL THRUST


    def no_intermediate_collision(self, step_num, point):
        """
        CHECK IF THERE IS A COLLISION
        PROVIDED THE STEP_NUM AND THE POINT (y,x)
        """
        # return self.position_matrix[step_num][point[0]][point[1]] != Matrix_val.ALLY_SHIP.value

        if step_num == 0:
            return True
        else:
            return self.position_matrix[step_num][point[0]][point[1]] == 0


    def set_ship_statuses(self,ship_id, target_planet_id, ship_coord, angle, thrust, target_coord):
        """
        SET STATUSES OF THE SPECIFIC SHIP
        """

        ## SET SHIP'S TARGET
        self.set_ship_target_id(ship_id, Target.PLANET, target_planet_id)

        ## SET SHIP'S TASK
        self.set_ship_task(ship_id, ShipTasks.EXPANDING)

        ## SET PLANET'S MY MINER
        self.set_planet_myminer(target_planet_id, ship_id)

        ## GET DESTINATION COORDS (y,x)
        self.set_ship_destination(ship_id, ship_coord, angle, thrust, target_coord)

        ## SET SHIP HAS MOVED AND FILL POSITION MATRIX
        self.set_ship_moved_and_fill_position(ship_id, angle, thrust)

    def set_ship_moved_and_fill_position(self, ship_id, angle, thrust, mining=False):
        """
        ADD SHIP TO MOVED ALREADY

        FILL POSITION MATRIX OF THIS SHIPS POSITION
        """
        logging.debug('Moved! ship_id: {}'.format(ship_id))

        self.myMap.ships_moved_already.add(ship_id)
        ship_point = self.myMap.data_ships[self.myMap.my_id][ship_id]['point']

        ## ADD TO POSITION MATRIX
        expanding2.fill_position_matrix(self.position_matrix[7], ship_point, mining)

        ## FILL IN INTERMEDIATE POSITION MATRIX
        expanding2.fill_position_matrix_intermediate_steps(self, ship_id, angle, thrust, mining)

    def set_ship_destination(self, ship_id, coords, angle, thrust, target_coord):
        """
        SET SHIP DESTINATION IN MYMAP DATA SHIPS
        BOTH TENTATIVE DESTINATION AND FINAL DESTINATION
        WITH SHIP ID, ANGLE AND THRUST PROVIDED
        """
        tentative_coord = MyCommon.get_destination_coord(coords, angle, thrust)
        self.myMap.data_ships[self.myMap.my_id][ship_id]['tentative_coord'] = tentative_coord

        tentative_point = MyCommon.get_rounded_point(tentative_coord)
        self.myMap.data_ships[self.myMap.my_id][ship_id]['tentative_point'] = tentative_point

        ## FINAL TARGET
        self.myMap.data_ships[self.myMap.my_id][ship_id]['target_coord'] = target_coord

        ## SET ANGLE TO TARGET (TENTATIVE ANGLE IS CURRENTLY THE SAME)
        self.myMap.data_ships[self.myMap.my_id][ship_id]['target_angle'] = angle

        ##

    def set_ship_target_id(self, ship_id, target_type, target_id):
        """
        SET SHIP TARGET IN MYMAP DATA SHIPS
        WITH SHIP ID, TARGET TYPE, AND TARGET ID PROVIDED
        """
        self.myMap.data_ships[self.myMap.my_id][ship_id]['target_id'] = (target_type, target_id)

    def set_ship_task(self, ship_id, ship_task):
        """
        SET SHIP TASK IN MYMAP DATA SHIPS
        WITH SHIP ID AND TASK PROVIDED
        """
        self.myMap.data_ships[self.myMap.my_id][ship_id]['task'] = ship_task

        ## ADD TO SHIP SETS
        if ship_task == ShipTasks.EXPANDING:
            self.myMap.ships_expanding.add(ship_id)

    def set_planet_myminer(self, planet_id, ship_id):
        """
        SET PLANET MY MINER IN MYMAP DATA PLANETS
        REGARDING MY SHIPS THAT ARE GOING TO MINE THIS PLANET
        """
        self.myMap.data_planets[planet_id]['my_miners'].add(ship_id)


