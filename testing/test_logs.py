import logging
import datetime

def log_players(game_map):
    logging.debug("------Players Info------")
    for player in game_map.all_players():
        logging.debug("-----Player ID: {}-----".format(player.id))
        for ship in player.all_ships():
            logging.debug("----Ship ID: {}----".format(ship.id))
            logging.debug("X: {}".format(ship.x))
            logging.debug("Y: {}".format(ship.y))
            logging.debug("Health: {}".format(ship.health))
            logging.debug("Docking status: {}".format(ship.docking_status))  ## UNDOCKED, DOCKED, DOCKING, UNDOCKING

    logging.debug(" ")

def log_planets(game_map):
    logging.debug("------Planet Info------")
    for planet in game_map.all_planets():
        logging.debug("----Planet Id: {}----".format(planet.id))
        logging.debug("X: {}".format(planet.x))
        logging.debug("Y: {}".format(planet.y))
        logging.debug("Num of docking spots: {}".format(planet.num_docking_spots))
        logging.debug("Current production: {}".format(planet.current_production))
        logging.debug("docked_ship_ids: {}".format(planet._docked_ship_ids))
        logging.debug("Health: {}".format(planet.health))
        logging.debug("Radius: {}".format(planet.radius))
        logging.debug("Owner: {}".format(planet.owner))
        logging.debug("Owned: {}".format(planet.is_owned()))

    logging.debug(" ")

def log_all_ships(myMap):
    logging.debug("Logging all ships:")
    for player_id, dict in myMap.data_ships.items():
        logging.debug("Player id: {}".format(player_id))
        for ship_id, ship in dict.items():
            logging.debug("ship_id: {} with data:{}".format(ship_id,ship))

def log_all_planets(myMap):
    logging.debug("Logging all planets:")
    for planet_id, dict in myMap.data_planets.items():
        logging.debug("Planet id: {} with data: {}".format(planet_id, dict))

def log_myMap_ships(myMap):
    logging.debug("------myMap Ships------")
    logging.debug("Ships (enemy): {}".format(myMap.ships_enemy))
    logging.debug("Ships (mine): {}".format(myMap.ships_owned))
    logging.debug("Ships (new): {}".format(myMap.ships_new))
    logging.debug("Ships (died): {}".format(myMap.ships_died))
    logging.debug("Ships (mining) (mine): {}".format(myMap.ships_mining_ally))
    logging.debug("Ships (mining) (enemy): {}".format(myMap.ships_mining_enemy))
    logging.debug("Ships (attacking): {}".format(myMap.ships_attacking))
    logging.debug("Ships (defending): {}".format(myMap.ships_defending))
    logging.debug("Ships (expanding): {}".format(myMap.ships_expanding))
    logging.debug("Ships (running): {}".format(myMap.ships_running))

def log_myMap_planets(myMap):
    logging.debug("------myMap Planets------")
    logging.debug("Planets (mine): {}".format(myMap.planets_owned))
    logging.debug("Planets (enemy): {}".format(myMap.planets_enemy))
    logging.debug("Planets (unowned): {}".format(myMap.planets_unowned))

def log_myShip(ship):
    logging.debug("My ship id: {}, x: {}, y: {}".format(ship.id, ship.x, ship.y))
    logging.debug(" ")

def log_dimensions(game_map):
    logging.debug("Width: {} x Height: {}".format(game_map.width,game_map.height))
    logging.debug(" ")

def log_myID(game_map):
    logging.debug("My ID: {}".format(game_map.my_id))
    logging.debug(" ")

def log_numPlayers(game_map):
    logging.debug("Number of players: {}".format(len(game_map._players)))
    logging.debug(" ")





# import numpy as np
#
# def fill_circle(array, h, w, center_y, center_x, radius, value, cummulative=False):
#     """
#     MASK A CIRCLE ON THE ARRAY WITH VALUE PROVIDED
#     """
#     height = h
#     width = w
#
#     y, x = np.ogrid[-center_y:height - center_y, -center_x:width - center_x]
#     ## y IS JUST AN ARRAY OF 1xY (ROWS)
#     ## x IS JUST AN ARRAY OF 1xX (COLS)
#     mask = x * x + y * y <= radius * radius
#     ## MASKS IS A HEIGHTxWIDTH ARRAY WITH TRUE INSIDE THE CIRCLE SPECIFIED
#
#     if cummulative:
#         array[mask] += -1
#     else:
#         array[mask] = value
#
#     return array
#
#
# n = 10
# array = np.ones((n, n))
# array = fill_circle(array, n, n, 3,3, 3, 0, cummulative=True)
# array = fill_circle(array, n, n, 3,3, 3, 0, cummulative=True)
# print("Ans",array)

