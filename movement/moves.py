import logging
from testing.test_logs import log_players, log_planets, log_myShip, log_dimensions
import hlt
from enum import Enum
import math
from models.data import ShipTasks
import MyCommon









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
    def __init__(self,myMap, EXP):
        self.command_queue = []
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


    def get_my_moves(self):
        if self.myMap.myMap_prev is None:
            ## FIRST TURN
            for ship_id in self.myMap.ships_new:
                ## GET BEST PLANET AND SET COMMAND QUEUE
                target_planet_id = self.EXP.best_planet_id

                planet_y = self.myMap.data_planets[target_planet_id]['y']
                planet_x = self.myMap.data_planets[target_planet_id]['x']
                planet_coord = MyCommon.Coordinates(planet_y,planet_x)

                ship_y = self.myMap.data_ships[self.myMap.my_id][ship_id]['y']
                ship_x = self.myMap.data_ships[self.myMap.my_id][ship_id]['x']
                ship_coord = MyCommon.Coordinates(ship_y,ship_x)

                ## ADD MOVE TO COMMAND QUEUE AND SET STATUSES
                self.set_moves(ship_coord, ship_id, planet_coord, target_planet_id)

        else:
            ## NOT FIRST TURN
            for ship_id, ship in self.myMap.data_ships[self.myMap.my_id].items():

                target_planet_id = self.myMap.myMap_prev.data_ships[self.myMap.my_id][ship_id]['target_id'][1]
                planet_y = self.myMap.data_planets[target_planet_id]['y']
                planet_x = self.myMap.data_planets[target_planet_id]['x']
                planet_coord = MyCommon.Coordinates(planet_y, planet_x)

                ship_coord = MyCommon.Coordinates(ship['y'], ship['x'])

                ## ADD MOVE TO COMMAND QUEUE AND SET STATUSES
                self.set_moves(ship_coord, ship_id, planet_coord, target_planet_id)


    def set_moves(self,ship_coord, ship_id, planet_coord, target_planet_id):
        """
        ADD COMMAND TO COMMAND QUEUE
        SET ALL STATUS
        """

        old_target_coord = self.check_duplicate_target(ship_id,target_planet_id)

        if old_target_coord:  ## USING OLD TARGET INFORMATION
            angle = MyCommon.get_angle(ship_coord, old_target_coord)
            ## PASS SAFE_COORD
            thrust, new_target_coord = self.get_thrust_to_planet(ship_coord, planet_coord, target_planet_id, angle, old_target_coord)
        else: ## NO OLD TARGET FOUND
            angle = MyCommon.get_angle(ship_coord, planet_coord)
            thrust, new_target_coord = self.get_thrust_to_planet(ship_coord, planet_coord, target_planet_id, angle)

        if thrust == 0:
            ## START MINING
            self.command_queue.append(self.convert_to_command_queue(ship_id, target_planet_id))
        else:
            ## MOVE
            self.command_queue.append(self.convert_to_command_queue(ship_id, thrust, angle))

        self.set_ship_statuses(ship_id, target_planet_id, ship_coord, angle, thrust, new_target_coord)

    def set_ship_statuses(self,ship_id, target_planet_id, ship_coord, angle, thrust, new_target_coord):
        ## SET SHIP'S TARGET
        self.set_ship_target_id(ship_id, Target.PLANET, target_planet_id)

        ## SET SHIP'S TASK
        self.set_ship_task(ship_id, ShipTasks.EXPANDING)

        ## SET PLANET'S MY MINER
        self.set_planet_myminer(target_planet_id, ship_id)

        ## GET DESTINATION COORDS (y,x)
        self.set_ship_destination(ship_id, ship_coord, angle, thrust, new_target_coord)

    def check_duplicate_target(self,ship_id,target_planet_id):
        """
        CHECKS IF TARGET IS ALREADY TAKEN BY ANOTHER SHIP

        IF IT IS, GET A NEW TARGET POINT
        """
        try:
            old_target_point = self.myMap.myMap_prev.data_ships[self.myMap.my_id][ship_id]['target_point']
            old_angle = self.myMap.myMap_prev.data_ships[self.myMap.my_id][ship_id]['target_angle']
        except:
            return None

        if old_target_point in self.myMap.all_target_coords:
            ## GET NEW TARGET POINT
            old_target_point = self.get_new_target_point(old_target_point, old_angle,target_planet_id)

        ## RETURN OLD OR NEW TARGET POINT (COORD)
        return MyCommon.Coordinates(old_target_point[0],old_target_point[1])


    def get_new_target_point(self,old_target_point, old_angle, target_planet_id):
        """
        GET NEW TARGET POINT

        MOVE CLOCKWISE (TAKE CURVATURE OF THE PLANET INTO ACCOUNT)
        """
        planet_center = MyCommon.Coordinates(self.myMap.data_planets[target_planet_id]['y'], \
                                             self.myMap.data_planets[target_planet_id]['x'])
        planet_angle = MyCommon.get_reversed_angle(old_angle)
        opposite = 1.5

        while True: ## MOVE 1.5 FROM OLD TARGET TO NEW TARGET
            logging.info("Tetsing old_target_point: {}".format(old_target_point))
            target_coord = MyCommon.Coordinates(old_target_point[0],old_target_point[1])
            adjacent = MyCommon.calculate_distance(target_coord, planet_center)
            angle = math.degrees(math.atan(opposite/adjacent))
            hypotenuse = opposite / math.sin(math.radians(angle))
            new_angle = planet_angle + angle
            new_target_coord = MyCommon.get_destination_coord(planet_center, new_angle, hypotenuse)
            new_target_point = (new_target_coord.y, new_target_coord.x)

            if old_target_point not in self.myMap.all_target_coords:
                break
            else:
                ## UPDATE VALUES FOR NEXT ITERATION
                old_target_point = new_target_point
                planet_angle = new_angle

        return new_target_point


    def get_thrust_to_planet(self,ship_coord, planet_coord, target_planet_id, angle, safe_coord=None):
        """
        GET THRUST VALUE TOWARDS A PLANET ID PROVIDED

        NEED TO TAKE INTO ACCOUNT THE PLANETS RADIUS + 3 (TO NOT CRASH AND TO MINE)
        """
        if safe_coord: ## SAFE COORD ALREADY IDENTIFIED
            target_coord = safe_coord
        else:
            target_coord = self.get_mining_coord(target_planet_id, planet_coord, angle)
        distance = MyCommon.calculate_distance(ship_coord, target_coord)

        if distance > 7:
            thrust =  7  ## STILL FAR, MAXIMIZE THRUST
        else:
            thrust = round(distance)

        return thrust, target_coord

    def get_mining_coord(self, target_planet_id, planet_coord, angle):
        """
        GET SAFE COORD TO MINE
        GIVEN PLANET ID AND THE REVERSE ANGLE (ANGLE OUTWARD THE CENTER OF THE PLANET
        """
        mining_distance = 3

        planet_radius = self.myMap.data_planets[target_planet_id]['radius']
        safe_distance = planet_radius + mining_distance
        reversed_angle = MyCommon.get_reversed_angle(angle)
        safe_coord = MyCommon.get_destination_coord(planet_coord, reversed_angle, safe_distance)

        return safe_coord


    def set_ship_destination(self,ship_id, coords, angle, thrust, new_target_coord):
        """
        SET SHIP DESTINATION IN MYMAP DATA SHIPS
        BOTH TENTATIVE DESTINATION AND FINAL DESTINATION
        WITH SHIP ID, ANGLE AND THRUST PROVIDED
        """
        tentative_coord = MyCommon.get_destination_coord(coords, angle, thrust)
        self.myMap.data_ships[self.myMap.my_id][ship_id]['tentative_coord'] = tentative_coord

        tentative_point = (round(tentative_coord.y), round(tentative_coord.x))
        self.myMap.data_ships[self.myMap.my_id][ship_id]['tentative_point'] = tentative_point

        target_point = (round(new_target_coord.y), round(new_target_coord.x))
        self.myMap.data_ships[self.myMap.my_id][ship_id]['target_point'] = target_point
        logging.info("testing target_point set: {}".format(target_point))

        ## SET ANGLE TO TARGET (TENTATIVE ANGLE IS CURRENTLY THE SAME)
        self.myMap.data_ships[self.myMap.my_id][ship_id]['target_angle'] = angle

        ## ADD THIS DESTINATION TO ALL TARGET COORDS
        self.myMap.all_target_coords.add(target_point)


    def set_ship_target_id(self,ship_id,target_type, target_id):
        """
        SET SHIP TARGET IN MYMAP DATA SHIPS
        WITH SHIP ID, TARGET TYPE, AND TARGET ID PROVIDED
        """
        self.myMap.data_ships[self.myMap.my_id][ship_id]['target_id'] = (target_type, target_id)

    def set_ship_task(self,ship_id, ship_task):
        """
        SET SHIP TASK IN MYMAP DATA SHIPS
        WITH SHIP ID AND TASK PROVIDED
        """
        self.myMap.data_ships[self.myMap.my_id][ship_id]['task'] = ship_task

    def set_planet_myminer(self,planet_id,ship_id):
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


## y 40, x 60, angle 149, thrust 7
## should give y 43.60 x 53.99
# a = MyMoves.get_destination((40,60),149,7)
# print(a)
