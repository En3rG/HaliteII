import logging

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
        logging.debug("Owned: {}".format(planet.is_owned()))

    logging.debug(" ")

def log_myShip(ship):
    logging.info("My ship id: {}, x: {}, y: {}".format(ship.id, ship.x, ship.y))
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