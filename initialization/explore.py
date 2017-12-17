import logging
from testing.test_logs import log_players, log_planets, log_myShip, log_dimensions
import math
import heapq
import numpy as np
import MyCommon
from models.data import MyMatrix, Matrix_val
from initialization.astar import a_star
import datetime


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
        self.planet_matrix = self.fill_planets_paths(matrix,self.game_map)
        self.get_launch_coords()

        self.paths = self.get_paths()

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


    def get_distances_me(self):
        """
        GET DISTANCES FROM MY LOCATION TO ALL THE PLANETS
        """
        distances = {}

        for id, val in self.planets.items():
            distances[id] = MyCommon.calculate_distance(val['coords'],self.myLocation)

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

    def get_launch_coords(self):
        """
        DETERMINE LAUNCH COORDS PER START (PLANET) TO TARGET (PLANET)
        """
        launch_distance = 8  ## OFFSET FROM PLANET RADIUS

        for planet_id, start_planet in self.planets.items():
            for target_planet in self.game_map.all_planets():
                ## GET FLY OFF COORD
                angle = MyCommon.get_angle(start_planet['coords'],MyCommon.Coordinates(target_planet.y,target_planet.x))
                distance = start_planet['radius'] + launch_distance
                fly_off_coord = MyCommon.get_destination(start_planet['coords'], angle, distance)

                ## GET LAND ON COORD
                angle = MyCommon.get_angle(MyCommon.Coordinates(target_planet.y, target_planet.x),start_planet['coords'])
                distance = target_planet.radius + launch_distance
                land_on_coord = MyCommon.get_destination(MyCommon.Coordinates(target_planet.y, target_planet.x), angle, distance)

                ## EACH PLANET WILL HAVE TARGET TO EACH OTHER PLANETS AND ITS LAUNCH PAD INFO
                self.planets[planet_id][target_planet.id] = LaunchPads(fly_off_coord,land_on_coord)

    def fill_planets_paths(self, matrix, game_map):
        """
        FILL PLANETS (AND ITS ENTIRE RADIUS) FOR A* MATRIX

        ADDING 2.5 ON RADIUS TO PREVENT COLLIDING ON MINING SHIPS
        """
        mining_area = 2.5

        for planet in game_map.all_planets():
            value = Matrix_val.PREDICTION_PLANET.value
            matrix = MyCommon.fill_circle(matrix, \
                                          game_map.height, \
                                          game_map.width, \
                                          MyCommon.Coordinates(planet.y, planet.x), \
                                          planet.radius + mining_area, \
                                          value, \
                                          cummulative=False)

        return matrix

    def get_paths(self):
        """
        GET A* PATHS FROM PLANET (START LAUNCHPAD) TO PLANET (TARGET LAUNCHPAD)
        """
        paths = {}
        done = set()

        start = datetime.datetime.now()

        for planet_id, planet in self.planets.items():
            for target_planet in self.game_map.all_planets():
                if (planet_id,target_planet.id) not in done:
                    fly_off_coords = (self.planets[planet_id][target_planet.id].fly_off.y, \
                                      self.planets[planet_id][target_planet.id].fly_off.x)
                    land_on_coords = (self.planets[planet_id][target_planet.id].land_on.y, \
                                      self.planets[planet_id][target_planet.id].land_on.x)

                    ## GET PATHS
                    paths_coords = a_star(self.planet_matrix, fly_off_coords, land_on_coords)
                    simplified_paths = self.simplify_paths(paths_coords)
                    path_table_1 = self.get_start_target_table(simplified_paths)
                    path_table_2 = self.get_start_target_table([] if simplified_paths == [] else simplified_paths[::-1])

                    paths[(planet_id, target_planet.id)] = path_table_1
                    paths[(target_planet.id, planet_id)] = path_table_2

                    ## ADD TO DONE ALREADY
                    done.add((planet_id,target_planet.id))
                    done.add((target_planet.id,planet_id))

        end = datetime.datetime.now()
        time_used = datetime.timedelta.total_seconds(end-start)
        logging.info("A* algo took: {}".format(time_used))

        return paths

    def simplify_paths(self,path_coords):
        """
        SIMPLIFY PATH.  COMBINE MOVEMENT WITH THE SAME SLOPES
        NEED TO MAXIMIZE THRUST OF 7 (MAX)
        """
        #logging.info("Original path: {}".format(path_coords))

        if path_coords != []:
            simplified_path = [path_coords[-1]]
            prev_coord = path_coords[-1]
            prev_angle = None
            tempCoord = None
            distance = 0
            length = len(path_coords) - 1 ## MINUS THE PREVIOUS

            ## SINCE STARTING IS AT THE END, SKIP LAST ONE (PREV COORD)
            for i, current_coord in enumerate(path_coords[-2::-1], start=1):
                ## GATHER PREVIOUS AND CURRENT COORD
                prevCoord = MyCommon.Coordinates(prev_coord[0],prev_coord[1])
                currentCoord = MyCommon.Coordinates(current_coord[0],current_coord[1])

                if i == length:  ## IF ITS THE LAST ITEM
                    ## ADD LAST ITEM TO SIMPLIFIED LIST
                    simplified_path.append((currentCoord.y, currentCoord.x))
                else:
                    if tempCoord: ## BASE IT ON TEMP COORD, NOT PREV COORD
                        current_angle = MyCommon.get_angle(tempCoord, currentCoord)
                        current_distance = MyCommon.calculate_distance(tempCoord, currentCoord)
                    else:
                        current_angle = MyCommon.get_angle(prevCoord, currentCoord)
                        current_distance = MyCommon.calculate_distance(prevCoord, currentCoord)

                    ## IF THE SAME SLOPE/ANGLE AS BEFORE AND STILL BELOW 7, CAN CONTINUE TO COMBINE/SIMPLIFY
                    if distance + current_distance < 7 and \
                            (prev_angle is None or prev_angle == current_angle):
                        tempCoord = currentCoord
                        distance = distance + current_distance

                    else: ## CANT COMBINE, NEED TO CHANGE DIRECTION
                        if tempCoord:
                            simplified_path.append((tempCoord.y,tempCoord.x))
                            current_angle = MyCommon.get_angle(tempCoord, currentCoord)  ## NEW ANGLE FROM TEMP TO CURRENT
                        else:
                            prevCoord = MyCommon.Coordinates(prev_coord[0], prev_coord[1])
                            current_angle = MyCommon.get_angle(prevCoord,currentCoord)  ## NEW ANGLE FROM TEMP TO CURRENT

                        currentCoord = MyCommon.Coordinates(current_coord[0], current_coord[1])
                        prev_coord = current_coord
                        prev_angle = current_angle
                        simplified_path.append((currentCoord.y, currentCoord.x))
                        distance = current_distance ## RESET DISTANCE
                        tempCoord = None ## RESET

            #logging.info("simplified path: {}".format(simplified_path))

            return simplified_path

        return []


    def get_start_target_table(self,simplified_path):
        """
        TAKES SIMPLIFIED PATH AND GENERATE A HASH TABLE
        KEY AS CURRENT COORD AND VALUE AS TARGET (DESTINATION) COORD
        """
        hash_table = {}

        if simplified_path != []:
            for i, coord in enumerate(simplified_path[:-1]): ## SKIPPING LAST ELEMENT
                hash_table[coord] = simplified_path[i+1]

        return hash_table










