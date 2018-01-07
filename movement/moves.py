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
import movement.expanding as expanding2




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

        self.get_my_moves()


    def get_my_moves(self):
        if self.myMap.myMap_prev is None:
            # # FIRST TURN
            #
            # ## GET BEST PLANET
            # target_planet_id = self.EXP.best_planet_id
            #
            # planet_y = self.myMap.data_planets[target_planet_id]['y']
            # planet_x = self.myMap.data_planets[target_planet_id]['x']
            # planet_coord = MyCommon.Coordinates(planet_y, planet_x)
            #
            # for ship_id in self.myMap.ships_new:
            #     ship_y = self.myMap.data_ships[self.myMap.my_id][ship_id]['y']
            #     ship_x = self.myMap.data_ships[self.myMap.my_id][ship_id]['x']
            #     ship_coord = MyCommon.Coordinates(ship_y,ship_x)
            #
            #     ## ADD MOVE TO COMMAND QUEUE AND SET STATUSES
            #     #self.set_moves(ship_coord, ship_id, planet_coord, target_planet_id)
            #
            #     ## USE A* PATH FOUND EARLIER
            #     path_key = (-1, ship_id, target_planet_id)
            #     self.myMap.data_ships[self.myMap.my_id][ship_id]['Astar_path_key'] = path_key
            #     path_table = self.EXP.A_paths[path_key]
            #
            #     tentative_destination = path_table.get((int(round(self.EXP.myStartCoords.y)), int(round(self.EXP.myStartCoords.x))), None)
            #
            #     angle, thrust = MyCommon.get_angle_thrust(ship_coord, MyCommon.Coordinates(tentative_destination[0],tentative_destination[1]))
            #
            #     self.command_queue.append(MyCommon.convert_for_command_queue(ship_id, thrust, angle))
            #
            #     new_target_coord = None
            #     self.set_ship_statuses(ship_id, target_planet_id, ship_coord, angle, thrust, new_target_coord)



            # ## FIRST TURN
            # ## GET ALL SHIPS (USING CENTROID)
            # members_id = [ ship_id for ship_id in self.myMap.ships_new ]
            #
            # ## GET BEST PLANET
            # target_planet_id = self.EXP.best_planet_id
            #
            # ## USE A* PATH FOUND EARLIER DURING EXPLORATION/INITIALIZATION
            # path_key = (-1, target_planet_id)
            #
            # ## ADD/CREATE GROUP
            # self.myMap.groups.add_group(members_id, keep_location=True)
            #
            # ## ADD ASTAR PATH KEY TO THE GROUP
            # self.myMap.groups.add_value_to_group(-1, 'Astar_path_key', path_key)
            # self.myMap.groups.add_value_to_group(-1, 'target_id', target_planet_id)
            #
            # ## ADD ASTAR PATH KEY TO EACH SHIP OF THE GROUP
            # self.myMap.groups.add_value_to_group_members(-1, 'Astar_path_key', path_key)
            # self.myMap.groups.add_value_to_group_members(-1, 'target_id', target_planet_id)
            #
            # ## GET ANGLE AND THRUST FROM PATH KEY
            # angle, thrust = self.get_angle_thrust_from_path_key(path_key, self.EXP.myStartCoords)
            #
            # ## ADD TO COMMAND QUEUE
            # self.command_queue.extend(self.myMap.groups.get_move_group(-1, thrust, angle))
            #
            # ## SET SHIP STATUSES
            # for ship_id in self.myMap.groups.groups_dict[-1].members_id:
            #     ship_y = self.myMap.data_ships[self.myMap.my_id][ship_id]['y']
            #     ship_x = self.myMap.data_ships[self.myMap.my_id][ship_id]['x']
            #     ship_coord = MyCommon.Coordinates(ship_y,ship_x)
            #     self.set_ship_statuses(ship_id, target_planet_id, ship_coord, angle, thrust, new_target_coord=None)


            # FIRST TURN
            ## GET BEST PLANET
            target_planet_id = self.EXP.best_planet_id

            for ship_id in self.myMap.ships_new:
                ship_coord = self.myMap.data_ships[self.myMap.my_id][ship_id]['coords']

                # ## USE A* PATH FOUND EARLIER DURING EXPLORATION/INITIALIZATION
                path_key = (-1, ship_id, target_planet_id)

                ## ADD/CREATE GROUP (NO LONGER CREATING GROUP?)

                ## SET TARGET
                self.myMap.data_ships[self.myMap.my_id][ship_id]['target_id'] = target_planet_id

                ## SET A* PATH KEY
                self.myMap.data_ships[self.myMap.my_id][ship_id]['Astar_path_key'] = path_key

                ## GET ANGLE AND THRUST FROM PATH KEY
                angle, thrust = self.get_angle_thrust_from_path_key(ship_id, path_key, ship_coord)

                ## ADD TO COMMAND QUEUE
                self.command_queue.append(MyCommon.convert_for_command_queue(ship_id, thrust, angle))

                ## SET SHIP STATUSES
                ship_coord = self.myMap.data_ships[self.myMap.my_id][ship_id]['coords']
                self.set_ship_statuses(ship_id, target_planet_id, ship_coord, angle, thrust, new_target_coord=None)

        else:
            ## NOT FIRST TURN

            ## NO LONGER USING GROUPS???
            # ## UPDATE GROUPS FROM PREV TURN
            # self.myMap.groups.get_and_update_prev_group()
            #
            # ## MOVE GROUPS
            # for group_id, group in self.myMap.groups.groups_dict.items():
            #     path_key = self.myMap.myMap_prev.groups.groups_dict[group_id].Astar_path_key
            #     target_planet_id = self.myMap.myMap_prev.groups.groups_dict[group_id].target_id
            #
            #     ## GET ANGLE AND THRUST FROM PATH KEY
            #     angle, thrust = self.get_angle_thrust_from_path_key(path_key, group.centroid_coord)
            #
            #     self.myMap.groups.add_value_to_group(group_id, 'Astar_path_key', path_key)
            #     self.myMap.groups.add_value_to_group(group_id, 'target_id', target_planet_id)
            #
            #     ## ADD TO COMMAND QUEUE
            #     self.command_queue.extend(self.myMap.groups.get_move_group(-1, thrust, angle))
            #
            #     ## SET SHIP STATUSES
            #     for ship_id in self.myMap.groups.groups_dict[group_id].members_id:
            #         ship_y = self.myMap.data_ships[self.myMap.my_id][ship_id]['y']
            #         ship_x = self.myMap.data_ships[self.myMap.my_id][ship_id]['x']
            #         ship_coord = MyCommon.Coordinates(ship_y, ship_x)
            #         self.set_ship_statuses(ship_id, target_planet_id, ship_coord, angle, thrust, new_target_coord=None)


            ## MOVE ALREADY MINING SHIPS FIRST
            for ship_id in self.myMap.ships_mining_ally:
                point = self.myMap.data_ships[self.myMap.my_id][ship_id]['point']

                self.myMap.taken_coords.add(point)
                self.myMap.ships_moved_already.add(ship_id)

            ## MOVE OTHERS
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
                        break
                    else:
                        planet_coord = self.myMap.data_planets[target_planet_id]['coords']

                        ## ADD MOVE TO COMMAND QUEUE AND SET STATUSES
                        self.set_moves(ship_coord, ship_id, planet_coord, target_planet_id)



    def get_angle_thrust_from_path_key(self, ship_id, path_key, coord):
        """
        GET ANGLE AND THRUST FROM PATH KEY PROVIDED

        ONLY USED IN FIRST TURN? SINCE COULD BE A LITTLE OFF DUE TO ROUNDING SOMETIMES
        """
        if path_key is None:
            return None, None

        path_table = self.EXP.A_paths[path_key]
        point = MyCommon.get_rounded_point(coord)
        tentative_destination = path_table.get(point, None)
        self.myMap.data_ships[self.myMap.my_id][ship_id]['Astar_dest_point'] = tentative_destination
        angle, thrust = MyCommon.get_angle_thrust(coord, MyCommon.Coordinates(tentative_destination[0],
                                                                              tentative_destination[1]))

        return angle, thrust


    def set_moves(self,ship_coord, ship_id, planet_coord, target_planet_id):
        """
        ADD COMMAND TO COMMAND QUEUE

        SET ALL STATUS
        """
        old_target_coord = None
        #old_target_coord = expanding.check_duplicate_target(self, ship_id,target_planet_id)



        ## JUST GOING STRAIGHT TO TARGET
        # if old_target_coord:  ## USING OLD TARGET INFORMATION
        #     angle = MyCommon.get_angle(ship_coord, old_target_coord)
        #     ## PASS SAFE_COORD
        #     thrust, new_target_coord = expanding.get_thrust_to_planet(self, ship_coord, planet_coord, target_planet_id, angle, old_target_coord)
        # else:
        #     ## NO OLD TARGET FOUND (NEW SHIP) OR NO TARGET SET
        #     angle = MyCommon.get_angle(ship_coord, planet_coord)
        #     thrust, new_target_coord = expanding.get_thrust_to_planet(self, ship_coord, planet_coord, target_planet_id, angle)


        ## USING A* PATH
        if old_target_coord:  ## USING OLD TARGET INFORMATION
            angle = MyCommon.get_angle(ship_coord, old_target_coord)

            ## PASS SAFE_COORD
            thrust, new_target_coord = expanding.get_thrust_to_planet(self, ship_coord, planet_coord, target_planet_id, angle,
                                                                 old_target_coord)
        else:
            ## INSTEAD OF GOING DIRECTLY TO TARGET, USE A* PATH GENERATED EARLIER
            from_planet_id = self.myMap.data_ships[self.myMap.my_id][ship_id]['from_planet']


            if from_planet_id is not None: ## NEW SHIP
                path_key = (from_planet_id, target_planet_id)
                self.myMap.data_ships[self.myMap.my_id][ship_id]['Astar_path_key'] = path_key

                ## USE A* TO GET TO LAUNCHPAD FLY OFF COORD
                path_table = expanding.get_set_path_table_toward_launch(self, ship_id, ship_coord, from_planet_id, target_planet_id)

                tentative_destination = path_table[self.myMap.data_ships[self.myMap.my_id][ship_id]['point']]
                self.myMap.data_ships[self.myMap.my_id][ship_id]['Astar_dest_point'] = tentative_destination
                angle, thrust = MyCommon.get_angle_thrust(ship_coord, MyCommon.Coordinates(tentative_destination[0], tentative_destination[1]))

                ## NEW SHIP APPEARED ON LAUNCH OFF
                ## FOLLOW ITS PATH KEY
                if thrust == 0:
                    tentative_destination = self.EXP.A_paths[path_key].get(tentative_destination, None)
                    self.myMap.data_ships[self.myMap.my_id][ship_id]['Astar_dest_point'] = tentative_destination
                    angle, thrust = MyCommon.get_angle_thrust(ship_coord, MyCommon.Coordinates(tentative_destination[0],
                                                                                               tentative_destination[1]))

            else: ## USE EXISTING Astar path table, IF ONE EXISTS
                path_key = self.myMap.myMap_prev.data_ships[self.myMap.my_id][ship_id].get('Astar_path_key', None)
                path_table = self.myMap.myMap_prev.data_ships[self.myMap.my_id][ship_id].get('Astar_path_table', None)
                tentative_destination = None

                if path_table:
                    # tentative_destination = path_table.get((int(round(ship_coord.y)), int(round(ship_coord.x))), None)
                    # if not(tentative_destination): ## POSSIBLY OFF BY A LITTLE, USE PREV A* DEST POINT
                    prev_dest_point = self.myMap.myMap_prev.data_ships[self.myMap.my_id][ship_id]['Astar_dest_point']
                    tentative_destination = path_table.get(prev_dest_point, None)

                if path_table is None or tentative_destination is None:
                    ## CHECK A* PATH KEY IF IT EXISTS
                    if path_key:
                        # tentative_destination = self.EXP.A_paths[path_key].get((int(round(ship_coord.y)), int(round(ship_coord.x))), None)
                        # if not(tentative_destination): ## POSSIBLY OFF BY A LITTLE, USE PREV A* DEST POINT
                        prev_dest_point = self.myMap.myMap_prev.data_ships[self.myMap.my_id][ship_id]['Astar_dest_point']
                        tentative_destination = self.EXP.A_paths[path_key].get(prev_dest_point, None)
                        path_table = None

                    else: ## PATH KEY DOESNT EXIST OR NONE
                        tentative_destination = None

                if tentative_destination: ## DIDNT GET TO DESTINATION YET
                    self.myMap.data_ships[self.myMap.my_id][ship_id]['Astar_dest_point'] = tentative_destination
                    self.myMap.data_ships[self.myMap.my_id][ship_id]['Astar_path_table'] = path_table
                    self.myMap.data_ships[self.myMap.my_id][ship_id]['Astar_path_key'] = path_key
                    angle, thrust = MyCommon.get_angle_thrust(ship_coord, MyCommon.Coordinates(tentative_destination[0], tentative_destination[1]))

                    ## !!!!!!!!!!!!!!!!111
                    ## IF MOVING BY 1 THRUST, IT IS POSSIBLE THAT THE ROUNDED COORDINATE DOESNT MOVE AT ALL
                    ## THIS THINKS THRUST IS 0, AND WILL TRY TO DOCK!!!!!

                else: ## GOT TO FINAL DESTINATION
                    thrust = 0
                    angle = 0

            #new_target_coord = None

        if thrust == 0:
            ## START MINING
            expanding.get_mining_spot(self, ship_id, target_planet_id)
        else:
            ## MOVE
            self.command_queue.append(MyCommon.convert_for_command_queue(ship_id, thrust, angle))

        ## ADD TO SHIPS MOVED
        self.myMap.ships_moved_already.add(ship_id)

        self.set_ship_statuses(ship_id, target_planet_id, ship_coord, angle, thrust, new_target_coord=None)


    def set_ship_statuses(self,ship_id, target_planet_id, ship_coord, angle, thrust, new_target_coord):
        ## SET SHIP'S TARGET
        self.set_ship_target_id(ship_id, Target.PLANET, target_planet_id)

        ## SET SHIP'S TASK
        self.set_ship_task(ship_id, ShipTasks.EXPANDING)

        ## SET PLANET'S MY MINER
        self.set_planet_myminer(target_planet_id, ship_id)

        ## GET DESTINATION COORDS (y,x)
        self.set_ship_destination(ship_id, ship_coord, angle, thrust, new_target_coord)

    def set_ship_destination(self, ship_id, coords, angle, thrust, new_target_coord):
        """
        SET SHIP DESTINATION IN MYMAP DATA SHIPS
        BOTH TENTATIVE DESTINATION AND FINAL DESTINATION
        WITH SHIP ID, ANGLE AND THRUST PROVIDED
        """
        tentative_coord = MyCommon.get_destination_coord(coords, angle, thrust)
        self.myMap.data_ships[self.myMap.my_id][ship_id]['tentative_coord'] = tentative_coord

        tentative_point = MyCommon.get_rounded_point(tentative_coord)
        self.myMap.data_ships[self.myMap.my_id][ship_id]['tentative_point'] = tentative_point

        if new_target_coord:
            target_point = (round(new_target_coord.y), round(new_target_coord.x))
            self.myMap.data_ships[self.myMap.my_id][ship_id]['target_point'] = target_point

        ## ADD THIS DESTINATION TO ALL TARGET COORDS
        self.myMap.taken_coords.add(tentative_point)

        ## SET ANGLE TO TARGET (TENTATIVE ANGLE IS CURRENTLY THE SAME)
        self.myMap.data_ships[self.myMap.my_id][ship_id]['target_angle'] = angle

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


def starter_bot_moves(game_map,command_queue):
    """
    MOVES FROM STARTER BOT AS IS
    """
    ## FOR EVERY SHIP I CONTROL
    for ship in game_map.get_me().all_ships():

        #log_myShip(ship)

        ## IF SHIP IS DOCKED
        if ship.docking_status != ship.DockingStatus.UNDOCKED:
            ## SKIP THIS SHIP
            continue

        ## FOR EACH PLANET IN THE GAME (ONLY NON-DESTROYED PLANETS ARE INCLUDED)
        for planet in game_map.all_planets():
            ## IF THE PLANET IS OWNED
            if planet.is_owned():
                ## SKIP THIS PLANET
                continue

            ## If we can dock, let's (try to) dock. If two ships try to dock at once, neither will be able to.
            if ship.can_dock(planet):
                ## We add the command by appending it to the command_queue
                command_queue.append(ship.dock(planet))
            else:
                ## If we can't dock, we move towards the closest empty point near this planet (by using closest_point_to)
                ## with constant speed. Don't worry about pathfinding for now, as the command will do it for you.
                ## We run this navigate command each turn until we arrive to get the latest move.
                ## Here we move at half our maximum speed to better control the ships
                ## In order to execute faster we also choose to ignore ship collision calculations during navigation.
                ## This will mean that you have a higher probability of crashing into ships, but it also means you will
                ## make move decisions much quicker. As your skill progresses and your moves turn more optimal you may
                ## wish to turn that option off.
                navigate_command = ship.navigate(ship.closest_point_to(planet), game_map,
                                                 speed=hlt.constants.MAX_SPEED / 2, ignore_ships=True)
                ## If the move is possible, add it to the command_queue (if there are too many obstacles on the way
                ## or we are trapped (or we reached our destination!), navigate_command will return null;
                ## don't fret though, we can run the command again the next turn)
                if navigate_command:
                    command_queue.append(navigate_command)
            break



