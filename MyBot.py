import hlt
import logging
from initialization.expansion import Exploration
from testing.test_logs import log_players, log_planets, log_myShip, log_dimensions
from multiprocessor.processors import MyProcesses
from multiprocessing import freeze_support, Queue
from models.model import NeuralNet, MyMap, MyMatrix, make_keras_picklable
from movement import moves
import MyCommon
import time
import copy
import numpy as np
import sys
import keras
import datetime
from datetime import timedelta
import os
import signal

## BEFORE IF MULTIPROCESS IS RUNNING, CAUSES ENGINE TO RECEIVE 'Using Tensorflow backend'


def set_delay(end,start,max_delay):
    """
    DELAY TO MAXIMIZE 2 SECONDS PER TURN
    HELP MULTIPROCESSES COMPLETE ITS TASKS

    USE TIMEDELTA BASE ON DATETIME INSTEAD OF TIME.CLOCK() FOR BETTER ACCURACY
    HALITE ENGINE SEEMS TO TIME OUT
    """
    used = timedelta.total_seconds(end-start)
    sleep_time = max_delay - used
    logging.debug("Setting Delay for: {}".format(sleep_time))
    if sleep_time > 0:
        time.sleep(sleep_time)

def wait_predictions_queue(Q,start,wait_time):
    """
    WAIT FOR ALL PREDICTIONS TO BE DONE
    BY wait_time SPECIFIED
    """
    end = datetime.datetime.now()
    while timedelta.total_seconds(end - start) < wait_time:
        if Q.qsize() >= 3:
            break
        end = datetime.datetime.now()

def get_predictions_queue(Q):
    """
    GET PREDICTIONS FROM QUEUE, PER ID
    NEED TO DETERMINE SHIP IDs
    """
    q = {}
    logging.debug("At get_queue time: {}".format(datetime.datetime.now()))
    if Q.empty():
        logging.debug("Q is empty")
    else:
        while not Q.empty():
            id, data = Q.get()
            q[id] = data

    logging.debug("Length of Q: {}".format(len(q)))
    return q

def clean_predicting_args(MP):
    """
    SINCE PREDICTING COULD TAKE MORE TIME THAN WE WANT SOMETIMES
    NEED TO MAKE SURE WE CLEAN PREDICTING ARGS QUEUE,
    SINCE IT'LL BE USELESS IF ITS NOT FROM THAT TURN

    THIS MAY NOT RUN AS MUCH NOW, SINCE MODEL COMPLEXITY HAS BEEN REDUCED
    """
    for id in MP.enemyIDs:
        logging.debug("Cleaning args queue for id: {} at {}".format(id,datetime.datetime.now()))
        while not MP.predictors[id]["args_queue"].empty():
            logging.debug("Not empty")
            discard = MP.predictors[id]["args_queue"].get()  ## False FOR NO WAIT (SEEMS TO TAKE MORE MEMORY WHEN FALSE)
            discard = None
            logging.debug("Cleaned at {}".format(datetime.datetime.now()))

    logging.debug("Done cleaning: {}".format(datetime.datetime.now()))

def model_handler(MP, turn, wait_time):
    """
    HANDLES TRAINING AND PREDICTING ENEMY MODELS, PER ENEMY ID
    BEFORE WAS PASSING NN TO THE ARGUMENTS AND WAS CAUSING ISSUE
    WHERE ITS TRAINING OLDER MODEL. NOW NO LONGER PASSING NN, GRAB NN
    FROM THE MODEL QUEUES TO ENSURE ITS THE LATEST ONE

    RETURNS PREDICTIONS AS DICTIONARY, WITH KEY OF ENEMY IDs
    """

    start = datetime.datetime.now()

    for id in MP.enemyIDs:

        ## THESE PARAMETERS ARE ONLY FOR TESTING PURPOSES, DELETE LATER
        samples = 200
        y = 28
        x = 28
        z = 3
        num_classes = 225
        x_train = np.random.random((samples, y, x, z))
        y_train = keras.utils.to_categorical(np.random.randint(10, size=(samples, 1)), num_classes=num_classes)

        args = ("train_" + str(id) + "_" + str(turn), id, x_train,y_train)
        MP.add_training(id, args)

        args = ("pred_" + str(id) + "_" + str(turn), id, x_train)
        MP.add_predicting(id, args)  ## WHEN LOADING KERAS, CAUSES AN ERROR (UNLESS ITS THREADS)
        logging.info("Added to queue for predicting id: {} time: {}".format(str(id),datetime.datetime.now()))
        #MP.worker_predict_model("pred_" + str(id) + "_" + str(turn), id, x_train)  ## CALLS THE FUCTION DIRECTLY


    ## GATHER/CLEANUP QUEUES
    wait_predictions_queue(MP.predictions_queue,start,wait_time)
    predictions = get_predictions_queue(MP.predictions_queue)
    clean_predicting_args(MP)

    return predictions, turn + 1



if __name__ == "__main__":
    freeze_support()

    ## UPDATABLE PARAMETERS
    disable_log = False
    max_delay = 1.900 ## TO MAXIMIZE TIME PER TURN
    wait_time = 1.200 ## WAIT TIME FOR PREDICTIONS TO GET INTO QUEUE

    ## BY DEFAULT, KERAS MODEL ARE NOT SERIALIZABLE
    ## TO PLACE IN QUEUE, NEED TO BE PICKLED
    make_keras_picklable()  ## NO LONGER USED?

    ## GAME START
    ## INITIALIZES LOG
    game = hlt.Game("En3rG")
    logging.info("Starting my bot!")

    ## PERFORM INITIALIZATION PREP
    EXP = Exploration(game)

    ## INITIALIZE PROCESSES
    MP = MyProcesses(game,disable_log,wait_time)

    ## ALLOW SOME TIME FOR CHILD PROCESSES TO SPAWN
    time.sleep(3)

    predictions = {}
    turn = 0
    myMap_prev = None
    myMatrix_prev = None

    ## DISABLE LOGS, IF TRUE
    MyCommon.disable_log(disable_log,logging)

    try:
        while True:

            start = datetime.datetime.now()

            logging.info("Turn # {} Calling update_map() at: {}".format(turn,datetime.datetime.now()))

            ## TURN START
            ## UPDATE THE MAP FOR THE NEW TURN AND GET THE LATEST VERSION
            game_map = game.update_map()

            logging.info("update_map time: {}".format(datetime.datetime.now()-start))

            ## CONVERT game_map TO MY VERSION
            myMap = MyMap(game_map)

            ## GATHER MAP MATRIX
            ## THIS WILL BE USED FOR PREDICTION
            ## PREVIOUS MATRIX WILL BE USED FOR TRAINING (ALONG WITH CURRENT myMap)
            myMatrix = MyMatrix(game_map,myMap_prev)

            ## FOR TRAINING/PREDICTING MODEL
            predictions, turn = model_handler(MP,turn, wait_time)

            ## FOR TESTING ONLY
            #log_planets(game_map)
            #log_players(game_map)

            ## INTIALIZE COMMANDS TO BE SENT TO HALITE ENGINE
            command_queue = []

            ## CURRENTLY FROM STARTER BOT MOVES
            moves.starter_bot_moves(game_map,command_queue)

            logging.info("Completed algo at {}.  Copying files".format(datetime.datetime.now()))

            ## SAVE OLD DATA FOR NEXT TURN
            ## WHEN USING DEEPCOPY SEEMS TO TIME OUT AFTER 7 TURNS
            myMap_prev = myMap
            myMatrix_prev = myMatrix

            ## SET A DELAY PER TURN
            end = datetime.datetime.now()
            set_delay(end,start,max_delay)

            logging.info("about to send commands {}".format(datetime.datetime.now()))

            ## SEND OUR COMMANDS TO HALITE ENGINE THIS TURN
            game.send_command_queue(command_queue)
            ## TURN END

            logging.info("Commands send at {}".format(datetime.datetime.now()))


    finally:
        ## TERMINATE MULTIPROCESSES
        MP.exit = True
        #os.killpg(0, signal.SIGKILL) ## MP.exit SEEMS ENOUGH (NEED TO CLOSE WINDOW THOUGH)
        ## GAME END
