
import hlt
import json
import logging
import numpy as np
import traceback
import sys

player_name = "p3"


def fill_matrix(matrix, ship):
    matrix[int(round(ship.y)), int(round(ship.x))] = ship.id

def get_ships(game_map, matrix):
    for player in game_map.all_players():
        if game_map.my_id == player.id:
            for ship in player.all_ships():
                ship_id = ship.id
                fill_matrix(matrix, ship)
                logging.debug("ship_id: {} y: {} x: {}".format(ship_id, ship.y, ship.x))


with open(player_name + '.txt') as json_data:
    moves = json.load(json_data)

    game = hlt.Game(player_name)
    logging.info("Starting my bot!")

    turn = 0

    while True:

        game_map = game.update_map()

        matrix = np.zeros((game_map.height, game_map.width), dtype=np.int16)

        get_ships(game_map, matrix)

        command_queue = moves.pop(0)
        logging.debug("Turn: {} command_queue: {}".format(turn, command_queue))
        game.send_command_queue(command_queue)
        turn += 1

        np.set_printoptions(threshold=np.inf,linewidth=np.inf)  ## SET PRINT THRESHOLD TO INFINITY
        #logging.debug("Matrix: {}".format(matrix))
        np.set_printoptions(threshold=10)     ## SET PRINT THRESHOLD TO 10





