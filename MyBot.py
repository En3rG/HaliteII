import hlt
import logging
from initialization.expansion import Exploration
from testing.test_logs import log_players, log_planets, log_myShip, log_dimensions
from multiprocessor.processors import MyProcesses
from multiprocessing import freeze_support
from models.model import NeuralNet, MyMap, MyMatrix, make_keras_picklable
from movement import moves
import time
import copy
import numpy as np
import sys
import keras

## IF MULTIPROCESS IS RUNNING, CAUSES ENGINE TO RECEIVE 'Using Tensorflow backend'


NN = NeuralNet()





def set_delay(num):
    """
    DELAY TO MAXIMIZE 2 SECONDS PER TURN
    HELP MULTIPROCESSES COMPLETE ITS TASKS
    """
    logging.debug("Setting Delay for: {}".format(num))
    time.sleep(num)

def model_handler(MP,turn):
    """
    HANDLES TRAINING AND PREDICTING ENEMY MODELS, PER ENEMY ID
    BEFORE WAS PASSING NN TO THE ARGUMENTS AND WAS CAUSING ISSUE
    WHERE ITS TRAINING OLDER MODEL. NOW NO LONGER PASSING NN, GRAB NN
    FROM THE MODEL QUEUES TO ENSURE ITS THE LATEST ONE
    """
    for id in MP.enemyIDs:
        #logging.info("Calling model: {}".format(MP.get_model_queues(id)))  ## ERRORING WHY????
        args = ("pred_" + str(id) + "_" + str(turn), id, 0.5)
        MP.worker_predictor(id,args)  ## WHEN LOADING KERAS, CAUSES AN ERROR (UNLESS ITS THREADS)

        samples = 200
        y = 28
        x = 28
        z = 3
        num_classes = 225
        x_train = np.random.random((samples, y, x, z))
        y_train = keras.utils.to_categorical(np.random.randint(10, size=(samples, 1)), num_classes=num_classes)

        #NN.train_model(x_train,y_train)

        args = ("train_" + str(id) + "_" + str(turn), id, x_train,y_train)
        MP.worker_trainer(id, args)

    return turn + 1

if __name__ == "__main__":
    freeze_support()

    ## BY DEFAULT, KERAS MODEL ARE NOT SERIALIZABLE
    ## TO PLACE IN QUEUE, NEED TO BE PICKLED
    make_keras_picklable()

    ## GAME START
    ## INITIALIZES LOG
    game = hlt.Game("En3rG")
    logging.info("Starting my bot!")

    ## PERFORM INITIALIZATION PREP
    EXP = Exploration(game)

    ## INITIALIZE PROCESSES
    MP = MyProcesses(game)

    turn = 0
    myMap_prev = None
    myMatrix_prev = None

    while True:

        start = time.clock()

        logging.info("1")

        ## TURN START
        ## UPDATE THE MAP FOR THE NEW TURN AND GET THE LATEST VERSION
        game_map = game.update_map()

        logging.info("2")

        ## CONVERT game_map TO MY VERSION
        myMap = MyMap(game_map)

        logging.info("3")

        ## GATHER MAP MATRIX
        ## THIS WILL BE USED FOR PREDICTION
        ## PREVIOUS MATRIX WILL BE USED FOR TRAINING (ALONG WITH CURRENT myMap)
        myMatrix = MyMatrix(game_map,myMap_prev)

        logging.info("4")

        ## FOR TRAINING/PREDICTING MODEL
        turn = model_handler(MP,turn)

        logging.info("5")

        ## FOR TESTING ONLY
        #log_planets(game_map)
        #log_players(game_map)

        ## INTIALIZE COMMANDS TO BE SENT TO HALITE ENGINE
        command_queue = []

        logging.info("6")

        ## CURRENTLY FROM STARTER BOT MOVES
        moves.starter_bot_moves(game_map,command_queue)

        logging.info("7")

        ## SET A DELAY PER TURN
        end = time.clock()
        set_delay(1.98 - (end - start))

        logging.info("8")


        ## SEND OUR COMMANDS TO HALITE ENGINE THIS TURN
        game.send_command_queue(command_queue)
        ## TURN END

        logging.info("9")

        ## SAVE OLD DATA FOR NEXT TURN
        ## WHEN USING DEEPCOPY SEEMS TO TIME OUT AFTER 7 TURNS
        myMap_prev = myMap
        myMatrix_prev = myMatrix

        logging.info("10")

    ## TERMINATE MULTIPROCESSES
    MP.exit = True
    ## GAME END
