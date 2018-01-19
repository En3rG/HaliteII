from enum import Enum
import numpy as np
import copy
import logging
import MyCommon
from movement import grouping
import traceback
import sys
import heapq


class Matrix_val(Enum):
    """
    VALUES PLACED ON THE MATRIX
    REPRESENTING ITS STATUS
    """
    ALLY_SHIP = 1
    ALLY_SHIP_DOCKED = 0.75
    ALLY_PLANET = 0.50
    UNOWNED_PLANET = 0.25
    DEFAULT = 0
    ENEMY_PLANET = -0.5
    ENEMY_SHIP_DOCKED = -0.75
    ENEMY_SHIP = -1
    MAX_SHIP_HP = 255

    ALLY_SHIP_CORNER = -8

    ## FOR MATRIX PREDICTIONS
    PREDICTION_PLANET = 100
    PREDICTION_ENEMY_SHIP_DOCKED = 0.5

    DOCKABLE_AREA = 777


class MyMap():
    """
    CONVERT GAME_MAP TO DICTIONARY
    ACCESS WITH PLAYER IDs AND SHIP IDs
    """
    MAX_NODES = 2  ## USED FOR LIMITING NUMBER OF NODES IN MEMORY
    NUM_NODES = 0

    def __init__(self,game_map, myMap_prev):
        self.game_map = game_map
        self.my_id = game_map.my_id
        self.height = game_map.height + 1
        self.width = game_map.width + 1
        self.myMap_prev = myMap_prev

        self.planets_owned = set()          ## PLANETS I OWN
        self.planets_unowned = set()        ## PLANETS UNOWNED
        self.planets_enemy = set()          ## PLANETS OWNED BY ENEMY
        self.planets_existing = set()       ## ALL PLANETS EXISTING IN THE MAP CURRENTLY

        self.ships_enemy = set()
        self.ships_owned = set()            ## SHIPS I OWN
        self.ships_new = set()              ## SHIPS THAT DIDNT EXIST PREVIOUSLY
        self.ships_died = set()             ## SHIPS THAT DIED
        self.ships_mining_ally = set()      ## SHIPS THAT ARE DOCKED (MINE)
        self.ships_mining_enemy = set()     ## SHIPS THAT ARE DOCKED (ENEMY)
        self.ships_attacking_frontline = set()
        self.ships_attacking = set()
        self.ships_supporting = set()
        self.ships_evading = set()
        self.ships_defending = set()
        self.ships_expanding = set()
        self.ships_running = set()
        self.ships_sniping = set()
        self.ships_battling = {1:set(),\
                               2:set(),\
                               3:set(),\
                               4:set(),\
                               5:set()}

        self.section_in_battle = set()          ## WILL CONTAIN SECTIONS IN WAR
        self.sections_with_enemy = set()        ## WILL CONTAIN SECTIONS WITH ENEMY
        self.sections_with_enemy_docked = set() ## WILL CONTAIN SECTIONS WITH ENEMY DOCKED
        self.ships_moved_already = set()        ## WILL CONTAIN SHIP IDS THAT ALREADY MOVED

        self.section_enemy_summary = np.zeros(((self.height // MyCommon.Constants.NUM_SECTIONS) + 1,
                                               (self.width // MyCommon.Constants.NUM_SECTIONS) + 1),
                                               dtype=np.float16)
        self.section_ally_summary = np.zeros(((self.height // MyCommon.Constants.NUM_SECTIONS) + 1,
                                              (self.width // MyCommon.Constants.NUM_SECTIONS) + 1),
                                              dtype=np.float16)

        self.data_ships = self.get_ship_data()

        self.data_planets = {}
        self.set_planet_status()
        self.set_ships_status()
        self.set_from_planet()                  ## ASSOCIATE NEW SHIPS TO A PLANET

        self.check_limit()                      ## KEEP A LIMIT OF NODES IN MEMORY

        # self.taken_coords = set()          ## NO LONGER USED

        # self.all_target_coords = set()     ## WILL CONTAIN ALL TARGET COORDS (TO PREVENT COLLISION OR SAME DESTINATION)
                                             ## NO LONGER USED

        #self.groups = grouping.Groups(self) ## NO LONGER USED


    def check_limit(self):
        """
        DELETE NODES THAT ARE OVER THE MAX LIMIT

        MINIMIZE/LIMIT NUMBER OF NODES IN MEMORY
        """
        MyMap.NUM_NODES += 1
        if MyMap.NUM_NODES > MyMap.MAX_NODES:
            ## DELETE OLD NODES
            self.myMap_prev.myMap_prev.myMap_prev = None
            MyMap.NUM_NODES -= 1


    def get_ship_data(self):
        """
        RETURN DATA IN DICTIONARY FORM
        DOCKING STATUS:
        0 = UNDOCKED
        1 = DOCKING
        2 = DOCKED
        3 = UNDOCKING

        enemy_in_turn WILL BE POPULATED BY PROJECTIONS
        """
        data = {}
        for player in self.game_map.all_players():

            player_id = player.id
            mine = player_id == self.game_map.my_id

            data[player_id] = {}
            for ship in player.all_ships():
                ship_id = ship.id
                ## CHANGE THIS LATER TO A CLASS, INSTEAD OF JUST A DICTIONARY
                data[player_id][ship_id] = {'x': ship.x, \
                                            'y': ship.y, \
                                            'coords': MyCommon.Coordinates(ship.y, ship.x), \
                                            'point': (int(round(ship.y)), int(round(ship.x))), \
                                            'health': ship.health, \
                                            'dock_status': ship.docking_status.value, \
                                            'enemy_in_turn':[], \
                                            'enemy_coords':{},\
                                            ## ONLY POPULATED THE FIRST TURN THE SHIP CAME OUT
                                            'from_planet':None, \
                                            ## TARGET IS THE FINAL DESTINATION
                                            'target_id':None, \
                                            'target_angle':None, \
                                            'target_coord':None, \
                                            ## ITS IMMEDIATE TARGET/DESTINATION
                                            'tentative_coord':None, \
                                            'tentative_point':None, \
                                            ## KEY IS USED TO GET THE ACTUAL A* PATH (PREDEFINED EARLIER)
                                            'Astar_path_key': None, \
                                            ## A* TABLE GENERATED TO REACH ITS TARGET
                                            'Astar_path_table': None, \
                                            ## WHERE IMMEDIATE DESTINATION IS
                                            ## SINCE SOMETIMES WITH THE ROUNDING, IT MAY NOT HIT EXACTLY AT THAT POINT
                                            'Astar_dest_point': None, \
                                            'task':MyCommon.ShipTasks.NONE}
                                             ## from_planet IS ONLY SET ON NEW SHIPS

                docked = not(ship.docking_status.value == 0)
                coord = data[player_id][ship_id]['coords']

                ## GATHER SHIPS I OWN
                if mine:
                    self.ships_owned.add(ship_id)
                    ## GATHER DOCKED SHIPS
                    if docked:
                        self.ships_mining_ally.add(ship_id)
                        data[player_id][ship_id]['target_id'] = (MyCommon.Target.PLANET, ship.planet.id)

                    self.set_section_summary(coord, enemy=False)  ## SET SECTION FOR ALLY
                else:
                    self.ships_enemy.add(ship_id)

                    ## GATHER ENEMY DOCKED SHIPS
                    if docked:
                        self.ships_mining_enemy.add(ship_id)

                        ## ADD THIS SECTION TO SECTION WITH ENEMY DOCKED
                        section_point = MyCommon.get_section_num(coord)
                        self.sections_with_enemy_docked.add(section_point)

                    self.set_section_summary(coord, enemy=True)  ## SET SECTION FOR ENEMY

        return data


    def set_section_summary(self, coord, enemy):
        """
        SET SHIP INTO SECTION SUMMARY
        """
        if enemy:
            section_point = MyCommon.get_section_num(coord)
            self.section_enemy_summary[section_point[0]][section_point[1]] += 1

            ## ADD THIS SECTION TO SECTION WITH ENEMY
            self.sections_with_enemy.add(section_point)
        else:
            section_point = MyCommon.get_section_num(coord)
            self.section_ally_summary[section_point[0]][section_point[1]] += 1


    def set_planet_status(self):
        """
        GATHER PLANETS WITH KEY AS PLANET ID

        SET STATUS OF PLANETS
        """
        for planet in self.game_map.all_planets():
            ## FILL IN PLANETS DATA
            self.set_planet_data(planet)

            ## ADD TO PLANET EXISTING CURRENTLY
            self.planets_existing.add(planet.id)

            if not planet.is_owned():
                ## PLANET NOT OWNED
                self.planets_unowned.add(planet.id)
            elif planet.owner is not None and planet.owner.id == self.game_map.my_id:
                ## PLANET I OWN
                self.planets_owned.add(planet.id)
                self.data_planets[planet.id]['docked_ships'].update(planet._docked_ship_ids)
                self.data_planets[planet.id]['my_miners'].update(planet._docked_ship_ids)
                #self.update_ship_task_mining(planet._docked_ship_ids)
            else:
                ## PLANET ENEMY OWNED
                self.planets_enemy.add(planet.id)


    def update_ship_task_mining(self,ships):
        """
        UPDATE TASKS OF SHIPS PROVIDED

        SHIPS ARE MINE ONLY

        NO LONGER USED
        """
        for ship_id in ships:
            self.data_ships[self.game_map.my_id][ship_id]['task'] = MyCommon.ShipTasks.MINING


    def set_planet_data(self, planet):
        """
        FILL PLANET DATA
        """
        ## my_miners ARE MY SHIPS MINING OR GOING TO MINE THIS PLANET
        ## NEED TO ADD SHIPS TASKED TO EXPANDING
        self.data_planets[planet.id] = {'y': planet.y, \
                                       'x': planet.x, \
                                        'coords': MyCommon.Coordinates(planet.y, planet.x), \
                                        'point': (int(round(planet.y)), int(round(planet.x))), \
                                       'radius': planet.radius, \
                                       'num_docks': planet.num_docking_spots, \
                                        'docked_ships': set(), \
                                       'my_miners': set(), \
                                       'health': planet.health, \
                                       'owner': None if planet.owner is None else planet.owner.id}


    def set_ships_status(self):
        """
        SET STATUS OF SHIPS
        """
        # for ship_id in self.ships_owned:
        #     ## CHECK IF SHIP IS NEW
        #     if self.myMap_prev is not None and ship_id not in self.myMap_prev.ships_owned:
        #         self.ships_new.add(ship_id)

        if self.myMap_prev is not None:
            ## CHECK FOR SHIPS THAT ARE NEW
            self.ships_new = self.ships_owned - self.myMap_prev.ships_owned

            ## CHECK FOR MY SHIPS THAT DIED FROM LAST TURN
            ## CHECK FOR SHIPS ONLY IN PREVIOUS, BUT NOT IN CURRENT (SET DIFFERENCE)
            self.ships_died = self.myMap_prev.ships_owned - self.ships_owned
        else:
            ## FIRST TURN
            self.ships_new = self.ships_owned


    def set_from_planet(self):
        """
        ASSOCIATE NEW SHIPS WITH A PLANET ORIGIN
        """

        ## PLUS 2 SINCE SPAWN CAN BE AROUND THERE, MADE IT 3 TO BE SURE
        spawn_radius = 3

        for ship_id in self.ships_new:
            for planet_id in self.planets_owned:
                planet_coord = self.data_planets[planet_id]['coords']
                ship_coord = self.data_ships[self.game_map.my_id][ship_id]['coords']

                if MyCommon.within_circle(ship_coord,planet_coord,self.data_planets[planet_id]['radius']+spawn_radius):
                    self.data_ships[self.game_map.my_id][ship_id]['from_planet'] = planet_id
                    break

    def can_dock(self, ship_id, planet_id):
        """
        RETURNS TRUE IF CAN DOCK PLANET ID

        NOT USED?
        """
        ship_coord = self.data_ships[self.my_id][ship_id]['coords']
        planet_coord = self.data_planets[planet_id]['coords']
        radius = self.data_planets[planet_id]['radius']

        distance = MyCommon.calculate_distance(ship_coord, planet_coord)

        return distance <= radius + MyCommon.Constants.DOCK_RADIUS

class MyMatrix():
    MAX_NODES = 2
    NUM_NODES = 0

    def __init__(self, myMap,myMatrix_prev,EXP,input_matrix_y,input_matrix_x):
        self.myMap = myMap
        self.matrix_prev = myMatrix_prev
        self.input_matrix_y = input_matrix_y
        self.input_matrix_x = input_matrix_x
        self.EXP = EXP
        self.prediction_matrix = None
        self.ally_matrix = np.zeros((self.myMap.height, self.myMap.width), dtype=np.int16)
        self.ally_matrix.fill(-1)
        self.matrix = self.get_matrix()  ## A DICTIONARY CONTAINING (MATRIX, MATRIX HP) (PER PLAYER ID)

        ## WILL CONTAIN LOCATION OF BACKUPS NEEDED
        self.backup_matrix = np.zeros((self.myMap.height, self.myMap.width), dtype=np.float16)

        ## KEEP A LIMIT OF NODES IN MEMORY
        self.check_limit()


    def check_limit(self):
        """
        DELETE NODES THAT ARE OVER THE MAX LIMIT
        """
        MyMatrix.NUM_NODES += 1
        if MyMatrix.NUM_NODES > MyMatrix.MAX_NODES:
            ## DELETE OLD NODES
            self.matrix_prev.matrix_prev.matrix_prev = None
            MyMatrix.NUM_NODES -= 1


    def get_matrix(self):
        """
        GET BASE MATRIX (WITH PLANETS INFO)
        GET MAP MATRIX PER PLAYER ID
        """
        final_matrix = {}
        # matrix = np.zeros((self.myMap.height, self.myMap.width), dtype=np.float16)
        # matrix_hp = np.zeros((self.myMap.height, self.myMap.width), dtype=np.float16)

        #for player in self.game_map.all_players():
        for player_id, ships in self.myMap.data_ships.items():
            if player_id == self.myMap.my_id:
                ## SET PLANET TO PREDICTION MATRIX
                #self.prediction_matrix = copy.deepcopy(EXP.all_planet_matrix)
                #curr_matrix = np.zeros((self.myMap.height, self.myMap.width), dtype=np.float16)
                #self.prediction_matrix = self.fill_planets_predictions(curr_matrix) ## NO LONGER USED

                self.ally_matrix, _ = self.fill_ships_ally(self.ally_matrix, np.copy(self.EXP.all_planet_matrix), ships)

            ## FILLING PLANET MATRIX PER TURN
            # matrix_current = copy.deepcopy(matrix)
            # matrix_hp_current = copy.deepcopy(matrix_hp)
            # matrix_current, matrix_hp_current = self.fill_planets(matrix_current, matrix_hp_current, player_id)

            ## JUST TAKING MATRIX FROM EXPLORATION
            matrix_current, matrix_hp_current = np.copy(self.EXP.all_planet_matrix), np.copy(self.EXP.all_planet_hp_matrix)

            if player_id != self.myMap.my_id:
                ## NOT FILLING OUR SHIPS SINCE IT"LL BE ADDED ONCE ME MOVE EACH SHIPS
                ## FILL CURRENT PLAYER'S SHIPS
                matrix_current, matrix_hp_current = self.fill_ships_ally(matrix_current,matrix_hp_current,ships)

            #for player_enemy in self.game_map.all_players():
            for player_enemy_id, enemy_ships in self.myMap.data_ships.items():
                if player_enemy_id == player_id:
                    pass
                else:
                    ## FILL CURRENT PLAYER'S ENEMY SHIPS
                    matrix_current, matrix_hp_current = self.fill_ships_enemy(matrix_current, matrix_hp_current, enemy_ships)

            final_matrix[player_id] = (matrix_current,matrix_hp_current) ## TUPLE OF 2 MATRIXES

        return final_matrix


    def fill_planets_predictions(self,matrix):
        """
        FILL PLANETS FOR PREDICTION MATRIX

        NO LONGER USED, SINCE WE ARE NO LONGER PREDICTING (NO NEURAL NET)
        """
        for planet_id, planet in self.myMap.data_planets.items():
            value = Matrix_val.PREDICTION_PLANET.value
            matrix = MyCommon.fill_circle(matrix, \
                                          planet['coords'], \
                                          planet['radius'], \
                                          value, \
                                          cummulative=False)

        return matrix

    def fill_planets(self,matrix,matrix_hp, player_id):
        """
        FILL MATRIX WITH
        ENTIRE BOX OF PLANET, CAN CHANGE TO CIRCLE LATER

        FILL IN MATRIX_HP OF PLANETS HP
        HP IS A PERCENTAGE OF MAX_SHIP_HP
        """
        ## JUST USING myMap, NOT game_map
        for planet_id, planet in self.myMap.data_planets.items():
            if planet['owner'] is None:
                value = Matrix_val.UNOWNED_PLANET.value
            elif planet['owner'] == player_id:
                value = Matrix_val.ALLY_PLANET.value
            else:
                value = Matrix_val.ENEMY_PLANET.value

            #matrix[round(planet.y)][round(planet.x)] = value
            ## INSTEAD OF FILLING JUST THE CENTER, FILL IN A BOX
            #matrix[round(planet.y)-round(planet.radius):round(planet.y)+round(planet.radius)+1, \
            #       round(planet.x)-round(planet.radius):round(planet.x)+round(planet.radius)+1] = value
            ## FILLING A CIRCLE (BETTER)
            #matrix = self.fill_circle(matrix, planet.y, planet.x, planet.radius, value)
            ## JUST USING myMap, NOT game_map
            matrix = MyCommon.fill_circle(matrix, \
                                          planet['coords'], \
                                          planet['radius']+MyCommon.Constants.FILL_PLANET_PAD, \
                                          value)

            ## FILL IN MATRIX_HP WITH HP OF PLANET (BOX)
            #matrix_hp[round(planet.y) - round(planet.radius):round(planet.y) + round(planet.radius)+1, \
            #          round(planet.x) - round(planet.radius):round(planet.x) + round(planet.radius)+1] = planet.health/Matrix_val.MAX_SHIP_HP.value
            ## FILLING A CIRCLE (BETTER)
            #matrix_hp = self.fill_circle(matrix_hp, planet.y, planet.x, planet.radius, planet.health/Matrix_val.MAX_SHIP_HP.value)
            ## JUST USING myMap, NOT game_map
            matrix_hp = MyCommon.fill_circle(matrix_hp, \
                                             planet['coords'], \
                                             planet['radius']+MyCommon.Constants.FILL_PLANET_PAD, \
                                             planet['health'] / Matrix_val.MAX_SHIP_HP.value)

        return matrix, matrix_hp


    def fill_ships_ally(self,matrix,matrix_hp,player_ships):
        """
        FILL MATRIX WHERE SHIP IS AT AND ITS HP
        HP IS A PERCENTAGE OF MAX_SHIP_HP
        """
        for ship_id, ship in player_ships.items():
            if ship['dock_status'] == 0:  ## UNDOCKED
                value = Matrix_val.ALLY_SHIP.value
            else:
                value = Matrix_val.ALLY_SHIP_DOCKED.value

            #matrix[ship['point'][0]][ship['point'][1]] = value

            matrix[ship['point'][0]][ship['point'][1]] = ship_id
            matrix_hp[ship['point'][0]][ship['point'][1]] = ship['health'] / Matrix_val.MAX_SHIP_HP.value

        return matrix, matrix_hp

    def fill_ships_enemy(self, matrix, matrix_hp, enemy_ships):
        """
        FILL MATRIX WHERE SHIP IS AT AND ITS HP
        HP IS A PERCENTAGE OF MAX_SHIP_HP

        value WILL DEPEND ON ENEMY, IF DOCKED OR NOT
        """
        for ship_id, ship in enemy_ships.items():
            if ship['dock_status'] == 0:  ## UNDOCKED
                value = Matrix_val.ENEMY_SHIP.value
            else:
                value = Matrix_val.ENEMY_SHIP_DOCKED.value

            #matrix[round(ship['y'])][round(ship['x'])] = value
            #matrix_hp[round(ship['y'])][round(ship['x'])] = ship['health'] / Matrix_val.MAX_SHIP_HP.value
            matrix[ship['point'][0]][ship['point'][1]] = value
            matrix_hp[ship['point'][0]][ship['point'][1]] = ship['health'] / Matrix_val.MAX_SHIP_HP.value

        return matrix, matrix_hp

    def fill_prediction_matrix(self, predicted_coords):
        """
        FILL MATRIX WITH PREDICTED ENEMY SHIPS COORDS
        ITS ACCUMULATIVE ATTACK POWER WILL

        MATRIX SHOULD BE FILLED WITH PLANETS INFO ALREADY

        NO LONGER USED, SINCE NO LONGER PREDICTING (NO NEURAL NET)
        """

        for player_id, ships in predicted_coords.items():
            for ship_id, coord in ships.items():
                ## FILLS ATTACK AREA OF ENEMY SHIPS
                ## 5 FOR SHIP RANGE, -1 FOR EACH ENEMY ATTACK RANGE
                try:
                    ## GET SHIPS ACTUAL COORDS
                    ship_y = self.myMap.data_ships[player_id][ship_id]['y']
                    ship_x = self.myMap.data_ships[player_id][ship_id]['x']
                    pred_y = ship_y + coord.y
                    pred_x = ship_x + coord.x

                    if self.myMap.data_ships[player_id][ship_id]['dock_status'] == 0: ## UNDOCKED
                        value = Matrix_val.ENEMY_SHIP.value
                    else:
                        value = Matrix_val.PREDICTION_ENEMY_SHIP_DOCKED.value
                    logging.debug("Predicted ship id: {} new coord: {} {}".format(ship_id, pred_y, pred_x))
                    self.prediction_matrix = MyCommon.fill_circle(self.prediction_matrix, \
                                                                  MyCommon.Coordinates(pred_y,pred_x), \
                                                                  MyCommon.Constants.ATTACK_RADIUS, \
                                                                  value, \
                                                                  cummulative=True)
                except Exception as e:
                    logging.error("Error found: ==> {}".format(e))

                    for index, frame in enumerate(traceback.extract_tb(sys.exc_info()[2])):
                        fname, lineno, fn, text = frame
                        logging.error("Error in {} on line {}".format(fname, lineno))

        ## TEST PRINT OUT
        ## ALSO UPDATING NUMPY PRINT OPTIONS
        #np.set_printoptions(threshold=np.inf,linewidth=np.inf)  ## SET PRINT THRESHOLD TO INFINITY
        #logging.debug("prediction_matrix: {}".format(self.prediction_matrix))
        #np.set_printoptions(threshold=10)     ## SET PRINT THRESHOLD TO 10





