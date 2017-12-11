from enum import Enum
from initialization.explore import Exploration
import numpy as np
import copy
import logging



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

    ## FOR MATRIX PREDICTIONS
    PREDICTION_PLANET = -10000
    PREDICTION_ENEMY_SHIP_DOCKED = 0.5

class ShipTasks(Enum):
    """
    VALUES FOR SHIPS TASKS
    """
    NONE = -1   ## DEFAULT
    MINING = 0
    EXPANDING = 1
    DEFENDING = 2
    ATTACKING = 3
    RUNNING = 4


class MyMap():
    """
    CONVERT GAME_MAP TO DICTIONARY
    ACCESS WITH PLAYER IDs AND SHIP IDs
    """
    MAX_NODES = 3
    NUM_NODES = 0

    def __init__(self,game_map, myMap_prev):
        self.planets_owned = set()  ## PLANETS I OWN
        self.planets_unowned = set()  ## PLANETS UNOWNED
        self.planets_enemy = set()  ## PLANETS OWNED BY ENEMY

        self.ships_enemy = set()
        self.ships_owned = set()  ## SHIPS I OWN
        self.ships_new = set()  ## SHIPS THAT DIDNT EXIST PREVIOUSLY
        self.ships_died = set()  ## SHIPS THAT DIED
        self.ships_mining_ally = set()  ## SHIPS THAT ARE DOCKED (MINE)
        self.ships_mining_enemy = set()  ## SHIPS THAT ARE DOCKED (ENEMY)
        self.ships_attacking = set()  ## THESE ARE CURRENTLY NOT USED
        self.ships_defending = set()  ## THESE ARE CURRENTLY NOT USED
        self.ships_expanding = set()  ## THESE ARE CURRENTLY NOT USED
        self.ships_running = set()  ## THESE ARE CURRENTLY NOT USED

        self.game_map = game_map
        self.myMap_prev = myMap_prev
        self.data_ships = self.get_ship_data()
        self.data_planets = {}
        self.set_planet_status()
        self.set_ships_status()
        self.set_from_planet()  ## ASSOCIATE NEW SHIPS TO A PLANET

        ## KEEP A LIMIT OF NODES IN MEMORY
        self.check_limit()


    def check_limit(self):
        """
        DELETE NODES THAT ARE OVER THE MAX LIMIT
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
                data[player_id][ship_id] = {'x': ship.x, \
                                            'y': ship.y, \
                                            'health': ship.health, \
                                            'dock_status': ship.docking_status.value, \
                                            'enemy_in_turn':[], \
                                            'enemy_coord':[],\
                                            'from_planet':None, \
                                            'target':None, \
                                            'destination':None, \
                                            'task':ShipTasks.NONE}
                                             ## from_planet IS ONLY SET ON NEW SHIPS

                docked = not(ship.docking_status.value == 0)

                ## GATHER SHIPS I OWN
                if mine:
                    self.ships_owned.add(ship_id)
                    ## GATHER DOCKED SHIPS
                    if docked:
                        self.ships_mining_ally.add(ship_id)
                else:
                    self.ships_enemy.add(ship_id)
                    ## GATHER ENEMY DOCKED SHIPS
                    if docked:
                        self.ships_mining_enemy.add(ship_id)


        return data

    def set_planet_status(self):
        """
        GATHER PLANETS WITH KEY AS PLANET ID

        SET STATUS OF PLANETS
        """
        for planet in self.game_map.all_planets():
            ## FILL IN PLANETS DATA
            self.set_planet_data(planet)

            if not planet.is_owned():
                ## PLANET NOT OWNED
                self.planets_unowned.add(planet.id)
            elif planet.owner is not None and planet.owner.id == self.game_map.my_id:
                ## PLANET I OWN
                self.planets_owned.add(planet.id)
                self.data_planets[planet.id]['my_miners'].update(planet._docked_ship_ids)
                self.update_ship_task_mining(planet._docked_ship_ids)
            else:
                ## PLANET ENEMY OWNED
                self.planets_enemy.add(planet.id)

    def update_ship_task_mining(self,ships):
        """
        UPDATE TASKS OF SHIPS PROVIDED

        SHIPS ARE MINE ONLY
        """
        for ship_id in ships:
            self.data_ships[self.game_map.my_id][ship_id]['task'] = ShipTasks.MINING


    def set_planet_data(self, planet):
        """
        FILL PLANET DATA
        """
        ## my_miners ARE MY SHIPS MINING OR GOING TO MINE THIS PLANET
        ## NEED TO ADD SHIPS TASKED TO EXPANDING
        self.data_planets[planet.id] = {'y': planet.y, \
                                       'x': planet.x, \
                                       'radius': planet.radius, \
                                       'num_docks': planet.num_docking_spots, \
                                       'my_miners': set(), \
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
        for ship_id in self.ships_new:
            for planet_id in self.planets_owned:
                planet_coord = (self.data_planets[planet_id]['y'],self.data_planets[planet_id]['x'])
                ship_coord = (self.data_ships[self.game_map.my_id][ship_id]['y'],self.data_ships[self.game_map.my_id][ship_id]['x'])

                ## PLUS 2 SINCE SPAWN CAN BE AROUND THERE, MADE IT 3 TO BE SURE
                if Exploration.within_circle(ship_coord,planet_coord,self.data_planets[planet_id]['radius']+3):
                    self.data_ships[self.game_map.my_id][ship_id]['from_planet'] = planet_id
                    break


class MyMatrix():
    MAX_NODES = 3
    NUM_NODES =0

    def __init__(self, game_map, myMap,myMatrix_prev,input_matrix_y,input_matrix_x):
        self.game_map = game_map
        self.myMap = myMap
        self.matrix_prev = myMatrix_prev
        self.input_matrix_y = input_matrix_y
        self.input_matrix_x = input_matrix_x
        self.prediction_matrix = None
        self.matrix = self.get_matrix()  ## A DICTIONARY CONTAINING (MATRIX, MATRIX HP) (PER PLAYER ID)

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
        matrix = np.zeros((self.game_map.height, self.game_map.width), dtype=np.float)
        matrix_hp = np.zeros((self.game_map.height, self.game_map.width), dtype=np.float)

        for player in self.game_map.all_players():
            if player.id == self.game_map.my_id:
                ## ONLY FILL PLANETS IF ITS MY ID
                matrix_current = copy.deepcopy(matrix)
                ## SET PLANET TO PREDICTION MATRIX
                self.prediction_matrix = self.fill_planets_predictions(matrix_current)
                continue

            matrix_current = copy.deepcopy(matrix)
            matrix_hp_current = copy.deepcopy(matrix_hp)
            matrix_current, matrix_hp_current = self.fill_planets(matrix_current, matrix_hp_current, player.id)


            ## FILL CURRENT PLAYER'S SHIPS
            matrix_current, matrix_hp_current = self.fill_ships_ally(matrix_current,matrix_hp_current,player)

            for player_enemy in self.game_map.all_players():
                if player_enemy.id == player.id:
                    pass
                else:
                    ## FILL CURRENT PLAYER'S ENEMY SHIPS
                    matrix_current, matrix_hp_current = self.fill_ships_enemy(matrix_current, matrix_hp_current, player_enemy)

            final_matrix[player.id] = (matrix_current,matrix_hp_current)

        return final_matrix


    def fill_planets_predictions(self,matrix):
        """
        FILL PLANETS FOR PREDICTION MATRIX
        """
        for planet in self.game_map.all_planets():
            value = Matrix_val.PREDICTION_PLANET.value
            matrix = self.fill_circle(matrix, planet.y, planet.x, planet.radius, value)

        return matrix

    def fill_planets(self,matrix,matrix_hp, player_id):
        """
        FILL MATRIX WITH
        ENTIRE BOX OF PLANET, CAN CHANGE TO CIRCLE LATER

        FILL IN MATRIX_HP OF PLANETS HP
        HP IS A PERCENTAGE OF MAX_SHIP_HP
        """
        for planet in self.game_map.all_planets():
            if not planet.is_owned():
                value = Matrix_val.UNOWNED_PLANET.value
            elif planet.owner is not None and planet.owner.id == player_id:
                value = Matrix_val.ALLY_PLANET.value
            else:
                value = Matrix_val.ENEMY_PLANET.value


            #matrix[round(planet.y)][round(planet.x)] = value
            ## INSTEAD OF FILLING JUST THE CENTER, FILL IN A BOX
            #matrix[round(planet.y)-round(planet.radius):round(planet.y)+round(planet.radius)+1, \
            #       round(planet.x)-round(planet.radius):round(planet.x)+round(planet.radius)+1] = value
            ## FILLING A CIRCLE (BETTER)
            matrix = self.fill_circle(matrix, planet.y, planet.x, planet.radius, value)

            ## FILL IN MATRIX_HP WITH HP OF PLANET (BOX)
            #matrix_hp[round(planet.y) - round(planet.radius):round(planet.y) + round(planet.radius)+1, \
            #          round(planet.x) - round(planet.radius):round(planet.x) + round(planet.radius)+1] = planet.health/Matrix_val.MAX_SHIP_HP.value
            ## FILLING A CIRCLE (BETTER)
            matrix_hp = self.fill_circle(matrix_hp, planet.y, planet.x, planet.radius, planet.health/Matrix_val.MAX_SHIP_HP.value)

        return matrix, matrix_hp

    def fill_circle(self,array, center_y, center_x, radius, value, cummulative=False):
        """
        MASK A CIRCLE ON THE ARRAY WITH VALUE PROVIDED
        """
        height = self.game_map.height
        width = self.game_map.width

        ## y IS JUST AN ARRAY OF 1xY (ROWS)
        ## x IS JUST AN ARRAY OF 1xX (COLS)
        y, x = np.ogrid[-center_y:height-center_y, -center_x:width-center_x]
        ## MASKS IS A HEIGHTxWIDTH ARRAY WITH TRUE INSIDE THE CIRCLE SPECIFIED
        mask = x*x + y*y <= radius*radius


        if cummulative:  ## VALUE KEEPS GETTING ADDED
            array[mask] += value
        else:
            array[mask] = value

        return array


    def fill_ships_ally(self,matrix,matrix_hp,player):
        """
        FILL MATRIX WHERE SHIP IS AT AND ITS HP
        HP IS A PERCENTAGE OF MAX_SHIP_HP
        """
        for ship in player.all_ships():
            if ship.docking_status.value == 0:  ## UNDOCKED
                value = Matrix_val.ALLY_SHIP.value
            else:
                value = Matrix_val.ALLY_SHIP_DOCKED.value

            matrix[round(ship.y)][round(ship.x)] = value
            matrix_hp[round(ship.y)][round(ship.x)] = ship.health/Matrix_val.MAX_SHIP_HP.value

        return matrix, matrix_hp

    def fill_ships_enemy(self, matrix, matrix_hp, player):
        """
        FILL MATRIX WHERE SHIP IS AT AND ITS HP
        HP IS A PERCENTAGE OF MAX_SHIP_HP

        value WILL DEPEND ON ENEMY, IF DOCKED OR NOT
        """
        for ship in player.all_ships():
            if ship.docking_status.value == 0:  ## UNDOCKED
                value = Matrix_val.ENEMY_SHIP.value
            else:
                value = Matrix_val.ENEMY_SHIP_DOCKED.value

            matrix[round(ship.y)][round(ship.x)] = value
            matrix_hp[round(ship.y)][round(ship.x)] = ship.health/Matrix_val.MAX_SHIP_HP.value

        return matrix, matrix_hp

    def fill_prediction_matrix(self, predicted_coords):
        """
        FILL MATRIX WITH PREDICTED ENEMY SHIPS
        ITS ACCUMULATIVE ATTACK POWER WILL

        MATRIX SHOULD BE FILLED WITH PLANETS INFO ALREADY
        """
        for player_id, ships in predicted_coords.items():
            for ship_id, coord in ships.items():
                ## FILLS ATTACK AREA OF ENEMY SHIPS
                ## 5 FOR SHIP RANGE, -1 FOR EACH ENEMY ATTACK RANGE
                try:
                    ## GET SHIPS ACTUAL COORDS
                    ship_y = self.myMap.data_ships[player_id][ship_id]['y']
                    ship_x = self.myMap.data_ships[player_id][ship_id]['x']
                    pred_y = ship_y + coord[0]
                    pred_x = ship_x + coord[1]

                    if self.myMap.data_ships[player_id][ship_id]['dock_status'] == 0: ## UNDOCKED
                        value = Matrix_val.ENEMY_SHIP.value
                    else:
                        value = Matrix_val.PREDICTION_ENEMY_SHIP_DOCKED.value
                    logging.debug("Predicted ship id: {} new coord: {} {}".format(ship_id, pred_y, pred_x))
                    self.prediction_matrix = self.fill_circle(self.prediction_matrix, pred_y, pred_x, 5, value, cummulative=True)
                except Exception as e:
                    logging.error("fill_prediction_matrix error: {}".format(e))

        ## TEST PRINT OUT
        ## ALSO UPDATING NUMPY PRINT OPTIONS
        #np.set_printoptions(threshold=np.inf,linewidth=np.inf)  ## SET PRINT THRESHOLD TO INFINITY
        #logging.debug("prediction_matrix: {}".format(self.prediction_matrix))
        #np.set_printoptions(threshold=10)     ## SET PRINT THRESHOLD TO 10





