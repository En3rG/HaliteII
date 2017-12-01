import logging
from testing.test_logs import log_players, log_planets, log_myShip, log_dimensions
import hlt
from enum import Enum
import math
from models.data import ShipTasks

class Target():
    NOTHING = -1
    PLANET = 0
    SHIP = 1

class MyMoves():
    """
    EX COMMAND QUEUE TO BE SENT:
    'd 0 2'      ## DOCKING SHIP ID 0 TO PLANET 2
    't 1 3 353'  ## MOVE SHIP ID 1 WITH SPEED 3 AND ANGLE 353
    """
    def __init__(self,myMap, EXP, game_map):
        self.command_queue = []
        self.game_map = game_map
        self.EXP = EXP
        self.myMap = myMap

        self.get_my_moves()

    def convert_to_command_queue(self, *args):
        if len(args) == 2:
            return "d {} {}".format(args[0], args[1])
        elif len(args) == 3:
            return "t {} {} {}".format(args[0], args[1], args[2])
        else:
            logging.ERROR("Command Error Length")


    def get_angle(self,coords, target_coords):
        """
        RETURNS ANGLE BETWEEN COORDS AND TARGET COORDS
        BOTH ARE IN (y,x) FORMAT
        """
        angle = math.degrees(math.atan2(target_coords[0] - coords[0], target_coords[1] - coords[1])) % 360
        return round(angle)

    def get_my_moves(self):
        if self.myMap.myMap_prev is None:
            ## FIRST TURN
            for ship_id in self.myMap.ships_new:
                ## GET BEST PLANET AND SET COMMAND QUEUE
                target_planet_id = self.EXP.best_planet
                planet_y = self.myMap.data_planets[target_planet_id]['y']
                planet_x = self.myMap.data_planets[target_planet_id]['y']

                ship_y = self.myMap.data_ships[self.game_map.my_id][ship_id]['y']
                ship_x = self.myMap.data_ships[self.game_map.my_id][ship_id]['x']

                angle = self.get_angle((ship_y,ship_x), (planet_y,planet_x))
                thrust = 7
                self.command_queue.append(self.convert_to_command_queue(ship_id, thrust, angle))

                ## SET SHIP TARGET TO
                self.set_ship_target(ship_id,Target.PLANET, target_planet_id)

                ## SET SHIP TASK TO
                self.set_ship_task(ship_id,ShipTasks.EXPANDING)

                ## SET PLANET MY MINER
                self.set_planet_myminer(target_planet_id,ship_id)


        else:
            ## NOT FIRST TURN
            test = None

    def set_ship_target(self,ship_id,target_type, target_id):
        """
        SET SHIP TARGET
        """
        self.myMap.data_ships[self.game_map.my_id][ship_id]['target'] = (target_type, target_id)

    def set_ship_task(self,ship_id, ship_task):
        """
        SET SHIP TASK
        """
        self.myMap.data_ships[self.game_map.my_id][ship_id]['task'] = ship_task

    def set_planet_myminer(self,planet_id,ship_id):
        """
        SET PLANET MY MINER
        REGARDING SHIP GOING TO MINE THIS PLANET
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







































# import math
#
# v1 = (1,0) ## y,x
# v2 = (-1,0)
#
# v1_t = math.atan2(v1[0],v1[1])
# v2_t = math.atan2(v2[0],v2[1])
#
# r = (v2_t - v1_t) * (180.0 / math.pi)
#
# print(r)
#
# if r < 0:
#     r += 360.0
#
# print(r)
#
# print(math.degrees(math.atan2(v1[0] - v2[0], v1[1] - v2[1])) % 360)
