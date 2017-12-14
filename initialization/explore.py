import logging
from testing.test_logs import log_players, log_planets, log_myShip, log_dimensions
import math
import heapq
import numpy as np
import MyCommon
from models.data import MyMatrix, Matrix_val
from initialization.astar import a_star
import datetime

class Exploration():
    def __init__(self,game):
        ## FOR TESTING ONLY
        #log_dimensions(game.map)
        #log_planets(game.map)
        #log_players(game.map)

        self.game_map = game.map
        self.planets = self.get_planets()
        self.distance_matrix = self.get_distances()
        self.myLocation = self.get_start_coords()
        self.distances_from_me = self.get_distances_me()
        self.best_planet = self.get_planets_score()

        matrix = np.zeros((self.game_map.height, self.game_map.width), dtype=np.float16)
        self.planet_matrix = MyMatrix.fill_planets_predictions(matrix,self.game_map)

        self.paths = self.get_paths()

    def get_planets(self):
        """
        GET ALL THE PLANETS AS IDs (INTs)
        """
        planets = {}

        for planet in self.game_map.all_planets():
            planets[planet.id] = {'coords':MyCommon.Coordinates(planet.y,planet.x), \
                                  'docks':planet.num_docking_spots}

        return planets

    def get_distances(self):
        """
        GET DISTANCES OF EACH PLANET TO ONE ANOTHER
        """
        length = len(self.planets)

        ## INITIALIZE MATRIX
        matrix = [[ 99999 for x in range(length) ] for y in range(length)]
        matrix = self.calculate_distances(matrix)

        return matrix

    def calculate_distances(self,matrix):
        """
        FILLS THE MATRIX WITH ACTUAL DISTANCES BETWEEN PLANETS
        """
        for id, val in self.planets.items():
            for id2, val2 in self.planets.items():

                if id == id2:
                    ## DISTANCE TO ITSELF WILL STAY 99999
                    pass
                elif matrix[id][id2] != 99999:
                    ## ALREADY CALCULATED BEFORE
                    pass
                else:
                    matrix[id][id2] = self.calculate_distance(val['coords'],val2['coords'])
                    matrix[id2][id] = matrix[id][id2]

        return matrix

    def calculate_distance(self,coords1,coords2):
        """
        CALCULATE DISTANCE BETWEEN 2 POINTS
        """
        return math.sqrt((coords1.y - coords2.y) ** 2 + (coords1.x - coords2.x) ** 2)

    def get_start_coords(self):
        """
        GET MIDDLE LOCATION OF MY 3 SHIPS
        """
        coords = []
        for player in self.game_map.all_players():
            if player.id == self.game_map.my_id:
                for ship in player.all_ships():
                    coords.append((ship.y,ship.x))

        return self.calculate_centroid(coords)

    def calculate_centroid(self,arr):
        """
        CALCULATE CENTROID.  COORDS ARE IN (y,x) FORMAT
        CALCULATE MIDDLE POINT OF A TRIANGLE (3 SHIPS)
        BASED ON:
        x = x1+x2+x3 / 3
        y = y1+y2+y3 / 3

        UPDATED TO CALCULATE CENTROID OF MULTIPLE POINTS, NOT JUST 3 POINTS
        """

        ## CONVERT ARR (LIST) TO NDARRAY
        data = np.array(arr)
        length = data.shape[0]
        sum_x = np.sum(data[:, 0])
        sum_y = np.sum(data[:, 1])

        return MyCommon.Coordinates(sum_y / length, sum_x / length)

    @classmethod
    def within_circle(self,point,center,radius):
        """
        RETURNS TRUE OR FALSE
        WHETHER point IS INSIDE THE CIRCLE, AT center WITH radius provided
        point AND center HAVE (y,x) FORMAT
        """
        return ((point.y - center.y) ** 2 + (point.x - center.x) ** 2) < (radius ** 2)

    def get_variance(self,arr):
        """
        RETURN VARIANCE OF THE LIST OF POINTS PROVIDED
        """
        data = np.array(arr)
        return np.var(data)

    def get_distances_me(self):
        """
        GET DISTANCES FROM MY LOCATION TO ALL THE PLANETS
        """
        distances = {}

        for id, val in self.planets.items():
            distances[id] = self.calculate_distance(val['coords'],self.myLocation)

        return distances

    def get_planets_score(self):
        """
        GET SCORE OF TARGET PLANET
        INCLUDING ITS TOP 2 NEIGHBORING PLANET
        TOTAL DOCKS / TOTAL DISTANCES
        """
        scores = {}
        for id, dist in self.distances_from_me.items():
            ## GET 2 SMALLEST DISTANCE
            list_dist = heapq.nsmallest(2, ((d, i) for i, d in enumerate(self.distance_matrix[id])))
            ## INFO FOR PLANET WITH dist AWAY FROM MY STARTING LOCATION
            docks = self.planets[id]['docks']
            distances = dist
            ## GET INFO FOR NEIGHBORING PLANETS
            for d,i in list_dist:
                docks += self.planets[i]['docks']
                distances += d
            scores[id] = docks/distances

        return self.get_highest_score(scores)

    def get_highest_score(self,scores):
        """
        RETURN PLANET ID (KEY) WITH HIGHEST SCORE
        """
        v = list(scores.values())
        k = list(scores.keys())
        return k[v.index(max(v))]

    def get_paths(self):
        """
        GET A* PATHS
        """
        paths = {}

        s = datetime.datetime.now()
        path = a_star(self.planet_matrix, (0,0), (150,150))
        end = datetime.datetime.now()
        used = datetime.timedelta.total_seconds(end-s)
        logging.info("took: {} path: {} ".format(used,path))


        return paths