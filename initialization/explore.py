import logging
from testing.test_logs import log_players, log_planets, log_myShip, log_dimensions
import math
import heapq
import numpy as np
import MyCommon
from models.data import Matrix_val
import datetime
import initialization.astar as astar


class Exploration():
    """
    GATHERS ALL PLANETS INFORMATION
    GATHERS DISTANCE OF EACH PLANET TO EACH PLANET
    GATHERS BEST PLANET TO CONQUER FIRST
    GATHERS PATHS, EACH PLANET TO EACH PLANET
    """
    def __init__(self,game):
        self.game_map = game.map
        self.height = self.game_map.height + 1
        self.width = self.game_map.width + 1

        logging.debug("Map height: {}".format(self.height))
        logging.debug("Map width: {}".format(self.width))

        self.planets = self.get_planets()
        self.sections_distance_table = self.get_distances_section()                  ## DISTANCES FROM SECTION TO SECTION
        self.sections_planet_distance_table = self.get_distances_section_to_planet() ## DISTANCES FROM SECTION TO PLANET
        self.sections_planet_score_table = self.get_scores_section_to_planet()       ## DISTANCES FROM SECTION TO PLANET
        self.planets_distance_matrix = self.get_distances()
        self.planets_score_matrix = self.get_planets_score()
        self.myStartCoords = self.get_start_coords()
        self.distances_from_start = self.get_start_distances()
        self.best_planet_id = self.get_best_planet()
        self.planet_matrix = {}                     ## FILLED BY FILL PLANETS FOR PATHS (INDIVIDUAL PLANETS ONLY)
        self.all_planet_matrix, self.all_planet_hp_matrix = self.fill_planets_for_paths()
        self.distance_matrix_AxA = self.get_distance_matrix(MyCommon.Constants.ATTACKING_RADIUS,
                                                            MyCommon.Constants.ATTACKING_RADIUS * 2 + 1)
        self.distance_matrix_DxD_perimeter = self.get_distance_matrix(MyCommon.Constants.DEFENDING_PERIMETER_CHECK,
                                                                      MyCommon.Constants.DEFENDING_PERIMETER_CHECK * 2 + 1)
        self.distance_matrix_DxD_backup = self.get_distance_matrix(MyCommon.Constants.DEFENDING_BACKUP_SQUARE_RADIUS,
                                                            MyCommon.Constants.DEFENDING_BACKUP_SQUARE_RADIUS * 2 + 1)
        self.distance_matrix_backup = self.get_distance_matrix(MyCommon.Constants.BACKUP_SQUARE_RADIUS,
                                                               MyCommon.Constants.BACKUP_SQUARE_RADIUS * 2 + 1)

        self.dockable_matrix = self.fill_dockable_matrix()


    def get_distance_matrix(self, center, square_diameter):
        """
        DISTANCE MATRIX FOR 15x15 MATRIX
        ASSUMING START IS AT THE CENTER
        """
        ## USING NUMPY VECTORIZED
        start_point = (center,center)
        n_rows, n_cols = square_diameter, square_diameter
        return self.calculate_distance_sections(start_point, n_rows, n_cols)


    def get_planets(self):
        """
        GET ALL THE PLANETS AS IDs (INTs)
        """
        planets = {}

        for planet in self.game_map.all_planets():
            planets[planet.id] = {'coords':MyCommon.Coordinates(planet.y,planet.x), \
                                  'point':(int(round(planet.y)), int(round(planet.x))), \
                                  'docks':planet.num_docking_spots, \
                                  'radius':planet.radius}
                              ##  planet.id OF TARGET PLANETS WILL ALSO BE FILLED IN LATER WITH LAUNCHPAD DATA
                              ##  planets[id1][id2] WILL CONTAIN LAUNCPPAD COORD FOR START ID1 TO TARGET ID2

        return planets


    def get_distances(self):
        """
        GET DISTANCES OF EACH PLANET TO ONE ANOTHER
        """
        length = len(self.planets)

        ## INITIALIZE MATRIX
        matrix = [[ 0 for x in range(length) ] for y in range(length)]
        matrix = self.calculate_distance_matrix(matrix)

        return matrix


    def calculate_distance_matrix(self,matrix):
        """
        FILLS THE MATRIX WITH ACTUAL DISTANCES BETWEEN PLANETS
        """
        for id, planet in self.planets.items():
            for id2, planet2 in self.planets.items():

                if id == id2:
                    ## DISTANCE TO ITSELF WILL STAY 0
                    pass
                elif matrix[id][id2] != 0:
                    ## ALREADY CALCULATED BEFORE
                    pass
                else:
                    matrix[id][id2] = MyCommon.calculate_distance(planet['coords'],planet2['coords'])
                    matrix[id2][id] = matrix[id][id2]

        return matrix


    def get_distances_section(self):
        """
        GET DISTANCES OF EACH SECTIONS TO ONE ANOTHER

        table[curr_section][target_section] = distance
        """
        table = {}

        row_length = (self.height // MyCommon.Constants.NUM_SECTIONS) + 1  ## + 1 TO COUNT LAST ITEM FOR RANGE
        col_length = (self.width // MyCommon.Constants.NUM_SECTIONS) + 1

        for r in range(row_length):
            for c in range(col_length):
                curr_section = (r,c)
                table[curr_section] = self.calculate_distance_sections(curr_section, row_length, col_length)

        return table


    def calculate_distance_sections(self, curr_section, row_length, col_length):
        """
        GENERATES A TABLE WITH ACTUAL DISTANCES BETWEEN SECTIONS
        """
        ## USING NUMPY (VECTORIZED), MUCH FASTER
        matrix = np.zeros((row_length, col_length), dtype=np.float16)
        indexes = [(y, x) for y, row in enumerate(matrix) for x, val in enumerate(row)]
        to_points = np.array(indexes)
        start_point = np.array([curr_section[0], curr_section[1]])
        distances = np.linalg.norm(to_points - start_point, ord=2, axis=1.)

        return distances.reshape((row_length, col_length))


    def get_distances_section_to_planet(self):
        """
        GET TABLE OF EACH SECTION'S DISTANCE TO EACH PLANETS

        table[curr_section][planet_id] = distance
        """
        table = {}

        row_length = (self.height// MyCommon.Constants.NUM_SECTIONS) + 1  ## +1 TO COUNT LAST ITEM IN RANGE
        col_length = (self.width// MyCommon.Constants.NUM_SECTIONS) + 1

        for r in range(row_length):
            for c in range(col_length):
                curr_section = (r, c)
                table[curr_section] = self.calculate_distance_to_planets(curr_section)

        return table


    def calculate_distance_to_planets(self, curr_section):
        """
        GET FROM CURRENT SECTION TO EACH PLANETS
        """
        dict = {}

        for planet_id, planet in self.planets.items():
            planet_coords = planet['coords']
            planet_section = MyCommon.get_section_num(planet_coords)

            distance = self.sections_distance_table[curr_section][planet_section[0]][planet_section[1]]
            dict[planet_id] = distance

        return dict


    def get_scores_section_to_planet(self):
        """
        GET TABLE OF EACH SECTION'S SCORES TO EACH PLANETS

        table[curr_section][planet_id] = distance
        """
        table = {}

        row_length = (self.height // MyCommon.Constants.NUM_SECTIONS) + 1  ## +1 TO COUNT LAST ITEM IN RANGE
        col_length = (self.width // MyCommon.Constants.NUM_SECTIONS) + 1

        for r in range(row_length):
            for c in range(col_length):
                curr_section = (r, c)
                table[curr_section] = self.calculate_scores_to_planets(curr_section)

        return table


    def calculate_scores_to_planets(self, curr_section):
        """
        GET FROM CURRENT SECTION TO EACH PLANETS
        """
        dict = {}

        for planet_id, planet in self.planets.items():
            planet_coords = planet['coords']
            planet_section = MyCommon.get_section_num(planet_coords)

            distance = self.sections_distance_table[curr_section][planet_section[0]][planet_section[1]]
            num_docks = planet['docks']
            score = num_docks/distance
            dict[planet_id] = score

        return dict


    def get_start_coords(self):
        """
        GET MIDDLE LOCATION OF MY 3 SHIPS
        """
        coords = []
        for player in self.game_map.all_players():
            if player.id == self.game_map.my_id:
                for ship in player.all_ships():
                    coords.append((ship.y,ship.x))

        return MyCommon.calculate_centroid(coords)


    def get_start_distances(self):
        """
        GET DISTANCES FROM MY LOCATION TO ALL THE PLANETS
        """
        distances = {}

        for id, val in self.planets.items():
            distances[id] = MyCommon.calculate_distance(val['coords'],self.myStartCoords)

        return distances

    def get_planets_score(self):
        """
        GET SCORE OF PLANETS
        TOTAL DOCKS / TOTAL DISTANCES
        """

        length = len(self.planets)

        ## INITIALIZE MATRIX
        matrix = [[0 for x in range(length)] for y in range(length)]

        for id, planet in self.planets.items():
            for id2, planet2 in self.planets.items():

                if id == id2:
                    ## SCORE TO ITSELF WILL STAY 0
                    pass
                else:
                    distance = MyCommon.calculate_distance(planet['coords'],planet2['coords'])
                    num_docks = planet2['docks']
                    score = num_docks/distance
                    matrix[id][id2] = score

        return matrix


    def get_best_planet(self):
        """
        GET SCORE OF TARGET PLANET
        INCLUDING ITS TOP 2 NEIGHBORING PLANET
        TOTAL DOCKS / TOTAL DISTANCES
        """
        scores = {}
        include_planets = 1

        for id, dist in self.distances_from_start.items():
            ## GET 2 SMALLEST DISTANCE
            ## ITS 3 INCLUDING ITSELF
            list_dist = heapq.nsmallest(include_planets, ((d, i) for i, d in enumerate(self.planets_distance_matrix[id])))
            ## INFO FOR PLANET WITH dist AWAY FROM MY STARTING LOCATION
            docks = self.planets[id]['docks']
            distances = dist
            ## GET INFO FOR NEIGHBORING PLANETS
            for d,i in list_dist:
                docks += self.planets[i]['docks']
                distances += d
            #scores[id] = docks/distances
            scores[id] = docks - (distances)  ## DISTANCE IS 3 TIMES LESS TO POINTS

        return self.get_highest_score(scores)


    def get_highest_score(self,scores):
        """
        RETURN PLANET ID (KEY) WITH HIGHEST SCORE
        """
        v = list(scores.values())
        k = list(scores.keys())
        return k[v.index(max(v))]


    def fill_dockable_matrix(self):
        """
        FILL MATRIX WITH DOCKABLE VALUE
        WILL BE USED TO DETERMINE IF CURRENT POINT IS DOCKABLE

        """

        matrix = np.zeros((self.height , self.width), dtype=np.float16)

        for planet in self.game_map.all_planets():
            value = Matrix_val.DOCKABLE_AREA.value
            matrix = MyCommon.fill_circle(matrix,
                                          MyCommon.Coordinates(planet.y, planet.x),
                                          planet.radius,
                                          value,
                                          cummulative=True, override_edges=0)

            matrix = MyCommon.fill_circle(matrix,
                                          MyCommon.Coordinates(planet.y, planet.x),
                                          planet.radius + MyCommon.Constants.DOCK_RADIUS,
                                          value,
                                          cummulative=True, override_edges=0)
        return matrix


    def fill_planets_for_paths(self):
        """
        FILL PLANETS (AND ITS ENTIRE RADIUS) FOR A* MATRIX
        ADDING 4 ON RADIUS TO PREVENT COLLIDING ON MINING SHIPS
        STILL USED, EVEN WHEN USING JUST SECTIONED A*
        """
        matrix = np.zeros((self.height, self.width), dtype=np.float16)
        matrix_hp = np.zeros((self.height, self.width), dtype=np.float16)

        for planet in self.game_map.all_planets():
            value = Matrix_val.PREDICTION_PLANET.value

            ## WITHOUT PADDING
            matrix = MyCommon.fill_circle(matrix,
                                          MyCommon.Coordinates(planet.y, planet.x),
                                          planet.radius,
                                          value,
                                          cummulative=True,
                                          override_edges=2.2)

            ## WITH PADDING
            matrix = MyCommon.fill_circle(matrix,
                                          MyCommon.Coordinates(planet.y, planet.x),
                                          planet.radius + MyCommon.Constants.FILL_PLANET_PAD,
                                          value,
                                          cummulative=True,
                                          override_edges=.1)

            matrix_hp = MyCommon.fill_circle(matrix_hp,
                                             MyCommon.Coordinates(planet.y, planet.x),
                                             planet.radius + MyCommon.Constants.FILL_PLANET_PAD,
                                             planet.health / Matrix_val.MAX_SHIP_HP.value)

            ## FILL THIS SPECIFIC PLANET
            self.fill_one_planet(planet)

        return matrix, matrix_hp


    def fill_one_planet(self, planet):
        """
        FILL ONE SPECIFIC PLANET
        """
        matrix = np.zeros((self.height, self.width), dtype=np.int8)
        value = Matrix_val.PREDICTION_PLANET.value
        matrix = MyCommon.fill_circle(matrix,
                                      MyCommon.Coordinates(planet.y, planet.x),
                                      planet.radius + MyCommon.Constants.FILL_PLANET_PAD,
                                      value,
                                      cummulative=False)

        self.planet_matrix[planet.id] = matrix


