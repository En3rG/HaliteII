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
        self.position_matrix = copy.deepcopy(myMatrix.matrix[myMap.my_id][0])  ## SECOND ONE IS HP MATRIX

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
            target_coord = self.myMap.data_planets[target_planet_id]['coords']
            angle = MyCommon.get_angle(self.EXP.myStartCoords, target_coord)

            ## GET MATRIX OF JUST THE TARGET PLANET
            planet_matrix = self.EXP.planet_matrix[target_planet_id]

            looking_for_val = Matrix_val.PREDICTION_PLANET.value
            for ship_id in self.myMap.ships_new:
                ship_coord = self.myMap.data_ships[self.myMap.my_id][ship_id]['coords']
                closest_coord = MyCommon.get_coord_closest_value(planet_matrix, ship_coord, looking_for_val, angle)

                if closest_coord:
                    reverse_angle = MyCommon.get_reversed_angle(angle)  ## REVERSE DIRECTION/ANGLE
                    target_coord = MyCommon.get_destination_coord(closest_coord, reverse_angle, MyCommon.Constants.MOVE_BACK)  ## MOVE BACK
                else:
                    ## DIDNT FIND. SHOULDNT HAPPEN FOR THE STARTING 3 SHIPS
                    logging.error("One of the starting ships didnt see the best planet, given the angle.")

                ## GET THRUST AND ANGLE
                thrust, angle = expanding2.get_thrust_angle_from_Astar(self, self.position_matrix, ship_id, target_coord)

                ## ADD TO COMMAND QUEUE
                self.command_queue.append(MyCommon.convert_for_command_queue(ship_id, thrust, angle))

                ## SET SHIP STATUSES
                self.set_ship_statuses(ship_id, target_planet_id, ship_coord, angle, thrust, target_coord)

        else:
            ## MOVE ALREADY MINING SHIPS FIRST
            for ship_id in self.myMap.ships_mining_ally:
                self.set_ship_moved_and_fill_position(ship_id)


            ## MOVE OTHERS REMAINING
            ## NOT USING HEAP (USING HEAP CAUSES TO TIME OUT)
            for ship_id, ship in self.myMap.data_ships[self.myMap.my_id].items():
                if ship_id not in self.myMap.ships_moved_already:
                    ship_coord = self.myMap.data_ships[self.myMap.my_id][ship_id]['coords']

                    try:
                        target_planet_id = self.myMap.myMap_prev.data_ships[self.myMap.my_id][ship_id]['target_id'][1]
                    except:
                        ## SHIP DIDNT EXIST BEFORE (NEW SHIP)
                        ## OR
                        ## SHIP HAS NO TARGET SET
                        target_planet_id = expanding.get_next_target_planet(self, ship_id)

                    if target_planet_id is None:
                        ## NO MORE PLANETS TO CONQUER AT THIS TIME
                        self.set_ship_moved_and_fill_position(ship_id)
                        break
                    else:
                        target_coord = expanding2.get_target_coord_towards_planet(self, target_planet_id, ship_id)

                        if target_coord is None:
                            ## NO AVAILABLE SPOT NEAR THE TARGET
                            self.set_ship_moved_and_fill_position(ship_id)
                            break

                        ## GET THRUST AND ANGLE
                        thrust, angle = expanding2.get_thrust_angle_from_Astar(self, self.position_matrix, ship_id, target_coord)

                        if thrust == 0:
                            self.command_queue.append(MyCommon.convert_for_command_queue(ship_id, target_planet_id))
                        else:
                            ## ADD TO COMMAND QUEUE
                            self.command_queue.append(MyCommon.convert_for_command_queue(ship_id, thrust, angle))

                        ## SET SHIP STATUSES
                        self.set_ship_statuses(ship_id, target_planet_id, ship_coord, angle, thrust, target_coord)


            ## USING HEAPQ
            ## USING HEAP IS VERY SLOW (TIMES OUT!!)
            ## GET TARGET AND DISTANCES
            ## SET distance_shipID_target
            # self.get_target_and_distances()
            #
            # ## MOVE OTHERS REMAINING
            # while self.myMap.distance_shipID_target:
            #     ## GET VALUES FROM HEAPQ
            #     distance, ship_id, target_planet_id, target_coord = heapq.heappop(self.myMap.distance_shipID_target)
            #
            #     ship_coord = self.myMap.data_ships[self.myMap.my_id][ship_id]['coords']
            #
            #     ## GET THRUST AND ANGLE
            #     thrust, angle = expanding2.get_thrust_angle_from_Astar(self, self.position_matrix, ship_id, target_coord)
            #
            #     logging.debug("Test! ship_id: {} target_coord: {} thrust: {}".format(ship_id, target_coord, thrust))
            #
            #     if thrust == 0:
            #         self.command_queue.append(MyCommon.convert_for_command_queue(ship_id, target_planet_id))
            #     else:
            #         ## ADD TO COMMAND QUEUE
            #         self.command_queue.append(MyCommon.convert_for_command_queue(ship_id, thrust, angle))
            #
            #     ## SET SHIP STATUSES
            #     self.set_ship_statuses(ship_id, target_planet_id, ship_coord, angle, thrust, target_coord)

    def get_target_and_distances(self):
        """
        GET SHIP'S TARGET AND DISTANCE TO THAT TARGET COORD

        IF SHIP HAS NO TARGET, SET SHIP TO MOVED

        USED WHEN USING HEAPQ, BUT KINDA SLOW
        """
        for ship_id, ship in self.myMap.data_ships[self.myMap.my_id].items():
            if ship_id not in self.myMap.ships_moved_already:
                ship_coord = self.myMap.data_ships[self.myMap.my_id][ship_id]['coords']

                try:
                    target_planet_id = self.myMap.myMap_prev.data_ships[self.myMap.my_id][ship_id]['target_id'][1]
                except:
                    ## SHIP DIDNT EXIST BEFORE (NEW SHIP)
                    ## OR
                    ## SHIP HAS NO TARGET SET
                    target_planet_id = expanding.get_next_target_planet(self, ship_id)

                if target_planet_id is None:
                    ## NO MORE PLANETS TO CONQUER AT THIS TIME
                    self.set_ship_moved_and_fill_position(ship_id)
                    break
                else:
                    target_coord = expanding2.get_target_coord_towards_planet(self, target_planet_id, ship_id)

                    ## ADD TO DISTANCE HEAP
                    distance = MyCommon.calculate_distance(ship_coord, target_coord)
                    heapq.heappush(self.myMap.distance_shipID_target, (distance, ship_id, target_planet_id, target_coord))

                    if target_coord is None:
                        ## NO AVAILABLE SPOT NEAR THE TARGET
                        self.set_ship_moved_and_fill_position(ship_id)
                        break

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
        self.set_ship_moved_and_fill_position(ship_id)

    def set_ship_moved_and_fill_position(self, ship_id):
        """
        ADD SHIP TO MOVED ALREADY

        FILL POSITION MATRIX OF THIS SHIPS POSITION
        """
        logging.debug('Moved! ship_id: {}'.format(ship_id))

        self.myMap.ships_moved_already.add(ship_id)
        ship_point = self.myMap.data_ships[self.myMap.my_id][ship_id]['point']

        ## ADD TO POSITION MATRIX
        expanding2.fill_position_matrix(self.position_matrix, ship_point)

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


