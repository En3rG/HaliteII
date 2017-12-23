import logging
from testing.test_logs import log_players, log_planets, log_myShip, log_dimensions
import math
import heapq
import numpy as np
import MyCommon
from models.data import MyMatrix, Matrix_val
from initialization.astar import a_star
import datetime
import initialization.astar as astar


class LaunchPads():
    """
    WILL CONTAIN THE COORDINATE OF START PLANET (FLY OFF COORD)
    AND TARGET PLANET (LAND ON COORD)
    """
    def __init__(self,fly_off_coord,land_on_coord):
        self.fly_off = fly_off_coord ## COORDINATE OBJECT
        self.land_on = land_on_coord ## COORDINATE OBJECT

    ## OVERRIDE PRINTING FUNCTION
    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "fly_off: {} land_on: {}".format(self.fly_off, self.land_on)

class Exploration():
    """
    GATHERS ALL PLANETS INFORMATION
    GATHERS DISTANCE OF EACH PLANET TO EACH PLANET
    GATHERS BEST PLANET TO CONQUER FIRST
    GATHERS PATHS, EACH PLANET TO EACH PLANET
    """
    LAUNCH_DISTANCE = 4    ## OFFSET FROM PLANET RADIUS
    LAUNCH_ON_DISTANCE = 4
    MINING_AREA_BUFFER = 1  ## BUFFER PLACED FOR GENERATING A* PATH TO NOT CRASH WITH MINING SHIPS


    def __init__(self,game):
        ## FOR TESTING ONLY
        #log_dimensions(game.map)
        #log_planets(game.map)
        #log_players(game.map)

        self.game_map = game.map
        self.planets = self.get_planets()
        self.planets_distance_matrix = self.get_distances()
        self.myStartCoords = self.get_start_coords()
        self.distances_from_start = self.get_start_distances()
        self.best_planet_id = self.get_planets_score()

        matrix = np.zeros((self.game_map.height, self.game_map.width), dtype=np.float16)
        self.planet_matrix = {} ## FILLED BY FILL PLANETS FOR PATHS
        self.all_planet_matrix = self.fill_planets_for_paths(matrix, self.game_map)
        self.get_launch_coords()

        self.A_paths = self.get_paths()


        for k,v in self.A_paths.items():
            logging.debug("k: {} v: {}".format(k,v))


    def get_planets(self):
        """
        GET ALL THE PLANETS AS IDs (INTs)
        """
        planets = {}

        for planet in self.game_map.all_planets():
            planets[planet.id] = {'coords':MyCommon.Coordinates(planet.y,planet.x), \
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
        matrix = [[ 99999 for x in range(length) ] for y in range(length)]
        matrix = self.calculate_distance_matrix(matrix)

        return matrix

    def calculate_distance_matrix(self,matrix):
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
                    matrix[id][id2] = MyCommon.calculate_distance(val['coords'],val2['coords'])
                    matrix[id2][id] = matrix[id][id2]

        return matrix



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
        GET SCORE OF TARGET PLANET
        INCLUDING ITS TOP 2 NEIGHBORING PLANET
        TOTAL DOCKS / TOTAL DISTANCES
        """
        scores = {}
        for id, dist in self.distances_from_start.items():
            ## GET 2 SMALLEST DISTANCE
            list_dist = heapq.nsmallest(2, ((d, i) for i, d in enumerate(self.planets_distance_matrix[id])))
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

    def get_launch_coords(self):
        """
        DETERMINE LAUNCH COORDS PER START (PLANET) TO TARGET (PLANET)
        """

        for planet_id, start_planet in self.planets.items():
            for target_planet in self.game_map.all_planets():
                ## GET FLY OFF COORD
                angle = MyCommon.get_angle(start_planet['coords'],MyCommon.Coordinates(target_planet.y,target_planet.x))
                distance = start_planet['radius'] + Exploration.LAUNCH_DISTANCE
                fly_off_coord = MyCommon.get_destination_coord(start_planet['coords'], angle, distance)

                ## GET LAND ON COORD
                angle = MyCommon.get_angle(MyCommon.Coordinates(target_planet.y, target_planet.x),start_planet['coords'])
                distance = target_planet.radius + Exploration.LAUNCH_ON_DISTANCE
                land_on_coord = MyCommon.get_destination_coord(MyCommon.Coordinates(target_planet.y, target_planet.x), angle, distance)

                ## EACH PLANET WILL HAVE TARGET TO EACH OTHER PLANETS AND ITS LAUNCH PAD INFO
                self.planets[planet_id][target_planet.id] = LaunchPads(fly_off_coord,land_on_coord)

    def fill_planets_for_paths(self, matrix, game_map):
        """
        FILL PLANETS (AND ITS ENTIRE RADIUS) FOR A* MATRIX

        ADDING 4 ON RADIUS TO PREVENT COLLIDING ON MINING SHIPS
        """
        for planet in game_map.all_planets():
            value = Matrix_val.PREDICTION_PLANET.value
            matrix = MyCommon.fill_circle(matrix, \
                                          game_map.height, \
                                          game_map.width, \
                                          MyCommon.Coordinates(planet.y, planet.x), \
                                          planet.radius + Exploration.MINING_AREA_BUFFER, \
                                          value, \
                                          cummulative=False)

            ## FILL THIS SPECIFIC PLANET
            self.fill_one_planet(planet, game_map)


        return matrix

    def fill_one_planet(self, planet, game_map):
        """
        FILL ONE SPECIFIC PLANET
        """
        matrix = np.zeros((self.game_map.height, self.game_map.width), dtype=np.int8)
        value = Matrix_val.PREDICTION_PLANET.value
        matrix = MyCommon.fill_circle(matrix, \
                                      game_map.height, \
                                      game_map.width, \
                                      MyCommon.Coordinates(planet.y, planet.x), \
                                      planet.radius + Exploration.MINING_AREA_BUFFER, \
                                      #planet.radius, \
                                      value, \
                                      cummulative=False)

        self.planet_matrix[planet.id] = matrix


    def get_paths(self):
        """
        GET A* PATHS FROM PLANET (START LAUNCHPAD) TO PLANET (TARGET LAUNCHPAD)

        GET A* PATH FROM STARTING LOCATION (3 SHIPS) TO BEST PLANET
        """
        paths = {}
        done = set()

        start = datetime.datetime.now()

        ## GET A* PATHS FROM A PLANET TO EACH PLANET
        for planet_id, planet in self.planets.items():
            for target_planet in self.game_map.all_planets():
                if (planet_id,target_planet.id) not in done:
                    fly_off_point = (self.planets[planet_id][target_planet.id].fly_off.y, \
                                      self.planets[planet_id][target_planet.id].fly_off.x)
                    land_on_point = (self.planets[planet_id][target_planet.id].land_on.y, \
                                      self.planets[planet_id][target_planet.id].land_on.x)

                    ## GET PATHS
                    path_table_forward, simplified_paths = astar.get_Astar_table(self.all_planet_matrix, fly_off_point, land_on_point)
                    path_table_reverse = astar.get_start_target_table([] if simplified_paths == [] else simplified_paths[::-1])

                    paths[(planet_id, target_planet.id)] = path_table_forward
                    paths[(target_planet.id, planet_id)] = path_table_reverse

                    #logging.debug("Get Paths Testing. On: {} fly_off_point: {} land_on_point: {} path_table_forward: {}".format((planet_id,target_planet.id),fly_off_point,land_on_point,path_table_forward))

                    ## ADD TO DONE ALREADY
                    done.add((planet_id,target_planet.id))
                    done.add((target_planet.id,planet_id))


        ## USE A* TO GET PATH FROM STARTING CENTROID TO BEST PLANET

        target_planet = self.planets[self.best_planet_id]
        ## GET ANGLE OF CENTROID TO BEST PLANET
        target_coord = MyCommon.Coordinates(target_planet['coords'].y, target_planet['coords'].x)
        angle = MyCommon.get_angle(self.myStartCoords, target_coord)

        ## FOR CENTROID TARGET ONLY
        # fly_off_point = (self.myStartCoords.y, self.myStartCoords.x)
        # distance = target_planet['radius'] + Exploration.LAUNCH_DISTANCE
        # land_on_coord = MyCommon.get_destination_coord(target_coord, angle, distance)
        # land_on_point = (land_on_coord.y, land_on_coord.x)
        #
        # path_points = a_star(self.all_planet_matrix, fly_off_point, land_on_point)
        # simplified_paths = self.simplify_paths(path_points)
        # path_table_forward = self.get_start_target_table(simplified_paths)
        # paths[(-1, self.best_planet_id)] = path_table_forward  ## -1 ID FOR STARTING POINT

        ## GET A* FOR EACH SHIPS
        matrix = self.planet_matrix[self.best_planet_id]
        looking_for_val = Matrix_val.PREDICTION_PLANET.value
        ## GO THROUGH EACH OF OUR SHIPS
        for player in self.game_map.all_players():
            if player.id == self.game_map.my_id:
                for ship in player.all_ships():
                    starting_point = (ship.y, ship.x)
                    starting_coord = MyCommon.Coordinates(ship.y, ship.x)
                    closest_coord = MyCommon.get_coord_closest_value(matrix, starting_coord, looking_for_val, angle)

                    if closest_coord:
                        reverse_angle = MyCommon.get_reversed_angle(angle) ## REVERSE DIRECTION/ANGLE
                        destination_coord = MyCommon.get_destination_coord(closest_coord, reverse_angle, 1) ## MOVE BACK 1
                        closest_point = (destination_coord.y, destination_coord.x)

                        path_table_forward, simplified_paths = astar.get_Astar_table(self.all_planet_matrix, starting_point, closest_point)
                        paths[(-1, ship.id, self.best_planet_id)] = path_table_forward  ## -1 ID FOR STARTING POINT

                    else:
                        ## DIDNT FIND. SHOULDNT HAPPEN FOR THE STARTING 3 SHIPS
                        logging.error("One of the starting ships didnt see the best planet, given the angle.")


        end = datetime.datetime.now()
        time_used = datetime.timedelta.total_seconds(end-start)
        logging.info("A* algo took: {}".format(time_used))

        return paths












