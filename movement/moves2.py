import logging
from testing.test_logs import log_players, log_planets, log_myShip, log_dimensions
import hlt
from enum import Enum
import math
from models.data import ShipTasks
import MyCommon
import heapq
import initialization.astar as astar
import movement.expanding as expanding
import movement.expanding2 as expanding2
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
            for ship_id in self.myMap.ships_new:
                ship_coord = self.myMap.data_ships[self.myMap.my_id][ship_id]['coords']
                value_coord = MyCommon.get_coord_of_value_in_angle(planet_matrix, ship_coord, seek_value, angle)

                if value_coord:
                    reverse_angle = MyCommon.get_reversed_angle(angle)  ## REVERSE DIRECTION/ANGLE
                    target_coord = MyCommon.get_destination_coord(value_coord, reverse_angle, MyCommon.Constants.MOVE_BACK)  ## MOVE BACK
                else:
                    ## DIDNT FIND. SHOULDNT HAPPEN FOR THE STARTING 3 SHIPS
                    logging.error("One of the starting ships didnt see the best planet, given the angle.")

                distance = MyCommon.calculate_distance(ship_coord, target_coord)

                ## GET THRUST AND ANGLE
                thrust, angle = expanding2.get_thrust_angle_from_Astar(self, ship_id, target_coord, distance, target_planet_id)

                ## ADD TO COMMAND QUEUE
                self.command_queue.append(MyCommon.convert_for_command_queue(ship_id, thrust, angle))

                ## SET SHIP STATUSES
                self.set_ship_statuses(ship_id, target_planet_id, ship_coord, angle, thrust, target_coord)

        else:
            s = datetime.datetime.now()

            ## MOVE ALREADY MINING SHIPS FIRST
            for ship_id in self.myMap.ships_mining_ally:
                self.set_ship_moved_and_fill_position(ship_id, angle=0, thrust=0)

            logging.info("Move mining ships time: {}".format(datetime.timedelta.total_seconds(datetime.datetime.now() - s)))




            time_astar = 0
            astar_number = 0


            ## MOVE OTHERS REMAINING
            ## NOT USING HEAP (USING HEAP CAUSES TO TIME OUT)
            for ship_id, ship in self.myMap.data_ships[self.myMap.my_id].items():
                if ship_id not in self.myMap.ships_moved_already:
                    ship_coord = self.myMap.data_ships[self.myMap.my_id][ship_id]['coords']

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
                        self.set_ship_moved_and_fill_position(ship_id, angle=0, thrust=0)
                        continue
                    else:
                        logging.debug("Getting docking coord for ship_id: {}".format(ship_id))
                        target_coord, distance = expanding2.get_docking_coord(self, target_planet_id, ship_id)
                        logging.debug("Got docking coord of: {}".format(target_coord))

                        if target_coord is None:
                            ## NO AVAILABLE SPOT NEAR THE TARGET
                            self.set_ship_moved_and_fill_position(ship_id, angle=0, thrust=0)
                            continue

                        ## GET THRUST AND ANGLE
                        s = datetime.datetime.now()

                        thrust, angle = expanding2.get_thrust_angle_from_Astar(self, ship_id, target_coord, distance, target_planet_id)

                        astar_number += 1

                        time_astar += datetime.timedelta.total_seconds(datetime.datetime.now() - s)

                        safe_thrust = self.check_collisions(ship_id, angle, thrust)

                        if thrust == 0:

                            self.command_queue.append(MyCommon.convert_for_command_queue(ship_id, target_planet_id))

                            # target_planet_coord = self.myMap.data_planets[target_planet_id]['coords']
                            # target_radius = self.myMap.data_planets[target_planet_id]['radius']
                            # d = MyCommon.calculate_distance(ship_coord, target_planet_coord)
                            # if d > round(target_radius + 4):
                            #     logging.debug("CAN NOT DOCK!!! MORE THAT DOCKABLE DISTANCE ship_id: {}".format(ship_id))

                        else:
                            ## ADD TO COMMAND QUEUE
                            self.command_queue.append(MyCommon.convert_for_command_queue(ship_id, safe_thrust, angle))

                        ## SET SHIP STATUSES
                        self.set_ship_statuses(ship_id, target_planet_id, ship_coord, angle, safe_thrust, target_coord)

            logging.info("Test! Turn")
            logging.info("Total astar number: {}".format(astar_number))
            logging.info("Total time astar: {}".format(time_astar))





            # ## USING HEAPQ
            # ## USING HEAP WAS VERY SLOW BEFORE (NOT SURE WHY BUT WHEN TESTING WITH RANDOM DATA, ITS VERY FAST)
            # ## ADDING UP ALL THE HEAPPOP IS SLOW (COULD TAKE 2 SECS TOTAL FOR ALL SHIPS COMBINED) WHY?? NOT TRUE!
            # ## HEAPPOP IS FAST, TAKING A LOT OF TIME AT ASTAR, BUT ALSO BECAUSE WE HAVE MUCH MORE SHIPS
            # ## WITHOUT USING HEAPPOP, ITS MUCH FASTER. BUT ABOVE WITHOUT CALCULATING TARGET/DISTANCE IS STILL FASTER
            # ## THIS GOES UP TO 0.5 SEC, WHILE ABOVE IS ABOUT 0.2-0.3 SEC ONLY (NOT USING HEAPPOP WILL NOT WORK!!)
            # ## STILL CANT DETERMINE WHY THIS IS MUCH SLOWER THAN ABOVE
            #
            # #s = datetime.datetime.now()
            #
            # ## GET TARGET AND DISTANCES
            # ## SET distance_shipID_target
            # heap = self.get_target_and_distances()
            #
            # #logging.info("target and distance time: {}".format(datetime.timedelta.total_seconds(datetime.datetime.now() - s)))
            #
            # time_pop = 0
            # time_astar = 0
            # time_statuses = 0
            # pop_number = 0
            #
            #
            # ## MOVE OTHERS REMAINING
            #
            # ## USING HEAPQ POP
            # while heap:
            #     ## GET VALUES FROM HEAPQ
            #     #s = datetime.datetime.now()
            #     distance, ship_id, target_planet_id, target_coord = copy.deepcopy(heapq.heappop(heap))
            #     #time_pop += datetime.timedelta.total_seconds(datetime.datetime.now() - s)
            #     #pop_number += 1
            #
            # ## INSTEAD OF POPPING, JUST LOOP THROUGH IT
            # ## NO NEED TO USE POP, SINCE WE ARE NO LONGER PLACING VALUES INTO THE HEAPQ
            # ## THIS DOES NOT WORK!!! THE HEAPQ WILL NOT BE IN THE RIGHT ORDER IF JUST LOOPING THROUGH
            # #for distance, ship_id, target_planet_id, target_coord in self.myMap.distance_shipID_target:
            #
            #
            #     ship_coord = self.myMap.data_ships[self.myMap.my_id][ship_id]['coords']
            #
            #     ## GET THRUST AND ANGLE
            #     #s = datetime.datetime.now()
            #
            #     thrust, angle = expanding2.get_thrust_angle_from_Astar(self, ship_id, target_coord, distance)
            #
            #     #time_astar += datetime.timedelta.total_seconds(datetime.datetime.now() - s)
            #
            #
            #
            #     if thrust == 0:
            #         self.command_queue.append(MyCommon.convert_for_command_queue(ship_id, target_planet_id))
            #     else:
            #         ## ADD TO COMMAND QUEUE
            #         self.command_queue.append(MyCommon.convert_for_command_queue(ship_id, thrust, angle))
            #
            #     s = datetime.datetime.now()
            #
            #     ## SET SHIP STATUSES
            #     self.set_ship_statuses(ship_id, target_planet_id, ship_coord, angle, thrust, target_coord)
            #
            #     time_statuses += datetime.timedelta.total_seconds(datetime.datetime.now() - s)
            #
            # logging.info("Test! Turn")
            # logging.info("Total pop number: {}".format(pop_number))
            # logging.info("Total time popping: {}".format(time_pop))
            # logging.info("Total time astar: {}".format(time_astar))
            # logging.info("Total time statuses: {}".format(time_statuses))

    def check_collisions(self, ship_id, angle, thrust):
        """
        CHECK IF AN INTERMEDIATE COLLISION EXISTS
        IF SO, RETURN THE THRUST THAT HAS NO COLLISION
        """

        ship_coord = self.myMap.data_ships[self.myMap.my_id][ship_id]['coords']
        dx = thrust / 7
        prev_thrust = 0

        for step_num in range(1, 7):
            curr_thrust = int(round(dx * step_num))

            intermediate_coord = MyCommon.get_destination_coord(ship_coord, angle, curr_thrust)
            intermediate_point = (int(round(intermediate_coord.y)), int(round(intermediate_coord.x)))

            no_collision = self.no_intermediate_collision(step_num, intermediate_point)
            if no_collision:
                prev_thrust = curr_thrust
            else:
                logging.debug("Collision detected! ship_id: {} intermediate_point: {} step_num: {} prev_thrust: {}".format(ship_id, intermediate_point, step_num, prev_thrust))
                return prev_thrust  ## CURRENT THRUST HAS COLLISION

        return thrust  ## RETURN ORIGINAL THRUST

    def no_intermediate_collision(self, step_num, point):
        """
        CHECK IF THERE IS A COLLISION
        PROVIDED THE STEP_NUM AND THE POINT (y,x)
        """
        #return self.position_matrix[step_num][point[0]][point[1]] != Matrix_val.ALLY_SHIP.value
        return self.position_matrix[step_num][point[0]][point[1]] == 0



    def get_target_and_distances(self):
        """
        GET SHIP'S TARGET AND DISTANCE TO THAT TARGET COORD

        IF SHIP HAS NO TARGET, SET SHIP TO MOVED

        USED WHEN USING HEAPQ, BUT KINDA SLOW
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
                    self.set_ship_moved_and_fill_position(ship_id, angle=0, thrust=0)
                    continue
                else:
                    target_coord, distance = expanding2.get_docking_coord(self, target_planet_id, ship_id)

                    if target_coord is None:
                        ## NO AVAILABLE SPOT NEAR THE TARGET
                        self.set_ship_moved_and_fill_position(ship_id, angle=0, thrust=0)
                        continue

                    ## ADD TO DISTANCE HEAP
                    heapq.heappush(heap, (distance, ship_id, target_planet_id, target_coord))

        return heap

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

    def set_ship_moved_and_fill_position(self, ship_id, angle, thrust):
        """
        ADD SHIP TO MOVED ALREADY

        FILL POSITION MATRIX OF THIS SHIPS POSITION
        """
        logging.debug('Moved! ship_id: {}'.format(ship_id))

        self.myMap.ships_moved_already.add(ship_id)
        ship_point = self.myMap.data_ships[self.myMap.my_id][ship_id]['point']

        ## ADD TO POSITION MATRIX
        expanding2.fill_position_matrix(self.position_matrix[7], ship_point)

        ## FILL IN INTERMEDIATE POSITION MATRIX
        expanding2.fill_position_matrix2(self, ship_id, angle, thrust)

    def set_ship_destination(self, ship_id, coords, angle, thrust, target_coord):
        """
        SET SHIP DESTINATION IN MYMAP DATA SHIPS
        BOTH TENTATIVE DESTINATION AND FINAL DESTINATION
        WITH SHIP ID, ANGLE AND THRUST PROVIDED
        """
        tentative_coord = MyCommon.get_destination_coord(coords, angle, thrust)
        self.myMap.data_ships[self.myMap.my_id][ship_id]['tentative_coord'] = tentative_coord

        tentative_point = (int(round(tentative_coord.y)), int(round(tentative_coord.x)))
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


