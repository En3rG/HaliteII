import hlt
import logging
from initialization.expansion import Exploration
from testing.test_logs import log_players, log_planets, log_myShip, log_dimensions
from multiprocessor.processors import MyProcesses
from multiprocessing import freeze_support
from models.model import NeuralNet  ## using tensor flow gets sent to engine??
import time
from threading import Thread
from multiprocessing import Process, Pool, freeze_support, Queue, Lock, Value, Array, Pipe

## IF MULTIPROCESS IS RUNNING, CAUSES ENGINE TO RECEIVE 'Using Tensorflow backend'


def set_delay(num):
    """
    Delay to maximize 2 seconds per turn
    Help multiprocesses complete its tasks
    """
    time.sleep(num)

def model_handler(MP,turn):
    """
    Handles training and predicting enemy models, per enemy ID
    """
    for id in MP.enemyIDs:
        # if not MP.queues[id].empty():
        #     ## get new model from the queue
        #     NN.models[id] = MP.queues[id].get()

        args = ["pred_" + id + "_" + str(turn), 1.5]
        MP.worker_predictor(id,args)  ## When loading keras, causes an error? why?
        args = ["train_" + id + "_" + str(turn), 2]
        MP.worker_trainer(id, args)

    return turn + 1

if __name__ == "__main__":
    freeze_support()

    ## GAME START
    ## Initializes log
    game = hlt.Game("En3rG")
    logging.info("Starting my bot!")

    ## Perform Initialization Prep
    Expansion = Exploration(game)

    ## Initialize Models
    #NN = NeuralNet(game)

    ## Initialize processes
    MP = MyProcesses(game)

    turn = 0

    while True:

        start = time.clock()

        turn = model_handler(MP,turn)


        ## TURN START
        ## Update the map for the new turn and get the latest version
        game_map = game.update_map()

        ## For testing only
        log_planets(game_map)
        log_players(game_map)

        ## Here we define the set of commands to be sent to the Halite engine at the end of the turn
        command_queue = []

        ## For every ship that I control
        for ship in game_map.get_me().all_ships():

            log_myShip(ship)

            # If the ship is docked
            if ship.docking_status != ship.DockingStatus.UNDOCKED:
                ## Skip this ship
                continue

            ## For each planet in the game (only non-destroyed planets are included)
            for planet in game_map.all_planets():
                ## If the planet is owned
                if planet.is_owned():
                    ## Skip this planet
                    continue

                ## If we can dock, let's (try to) dock. If two ships try to dock at once, neither will be able to.
                if ship.can_dock(planet):
                    ## We add the command by appending it to the command_queue
                    command_queue.append(ship.dock(planet))
                else:
                    ## If we can't dock, we move towards the closest empty point near this planet (by using closest_point_to)
                    ## with constant speed. Don't worry about pathfinding for now, as the command will do it for you.
                    ## We run this navigate command each turn until we arrive to get the latest move.
                    ## Here we move at half our maximum speed to better control the ships
                    ## In order to execute faster we also choose to ignore ship collision calculations during navigation.
                    ## This will mean that you have a higher probability of crashing into ships, but it also means you will
                    ## make move decisions much quicker. As your skill progresses and your moves turn more optimal you may
                    ## wish to turn that option off.
                    navigate_command = ship.navigate(ship.closest_point_to(planet), game_map, speed=hlt.constants.MAX_SPEED/2, ignore_ships=True)
                    ## If the move is possible, add it to the command_queue (if there are too many obstacles on the way
                    ## or we are trapped (or we reached our destination!), navigate_command will return null;
                    ## don't fret though, we can run the command again the next turn)
                    if navigate_command:
                        command_queue.append(navigate_command)
                break

        ## Set a delay per turn
        end = time.clock()
        set_delay(1.98 - (end - start))

        ## Send our set of commands to the Halite engine for this turn
        game.send_command_queue(command_queue)
        ## TURN END

    MP.exit = True
    ## GAME END
