import hlt
import logging
import json

with open('p3.txt') as json_data:
    moves = json.load(json_data)

    game = hlt.Game("p3")
    logging.info("Starting my bot!")
    
    turn = 0

    while True:
        game_map = game.update_map()
        command_queue = moves.pop(0)
        logging.debug("Turn: {} command_queue: {}".format(turn, command_queue))
        game.send_command_queue(command_queue)
        turn += 1