import hlt
import logging
from initialization.explore import Exploration
from testing.test_logs import log_players, log_planets, log_myShip, log_dimensions, log_all_ships, log_myMap_ships, \
                              log_myMap_planets, log_all_planets
from multiprocessor.processors import MyProcesses
from multiprocessing import freeze_support, Queue
from models.model import NeuralNet, make_keras_picklable
from models.data import MyMap, MyMatrix
from projection.projection import MyProjection
from movement import moves
from movement import moves2
import MyCommon
import time
import copy
import numpy as np
import sys
import keras
import datetime
import os
import signal
from memory_profiler import profile       ## USING @profile PER FUNCTIONS, RUN WITH -m memory_profile FLAG
from memory_profiler import memory_usage
import traceback


## BEFORE IF MULTIPROCESS IS RUNNING, CAUSES ENGINE TO RECEIVE 'Using Tensorflow backend'. N/A ANYMORE.

def set_delay(start):
    """
    DELAY TO MAXIMIZE 2 SECONDS PER TURN
    HELP MULTIPROCESSES COMPLETE ITS TASKS

    USE TIMEDELTA BASE ON DATETIME INSTEAD OF TIME.CLOCK() FOR BETTER ACCURACY?
    HALITE ENGINE SEEMS TO TIME OUT SOMETIMES
    BUT MOST OF THE TIME WHEN IT TIMES OUT ITS BECAUSE MY PREVIOUS TURN TOOK MORE THAN 2 SECS
    """
    end = datetime.datetime.now()
    used = datetime.timedelta.total_seconds(end-start)
    sleep_time = MAX_DELAY - used
    logging.info("Setting Delay for: {}".format(sleep_time))
    sleep_time = round(sleep_time,3) ## ROUND WITH 3 DECIMAL
    logging.info("Rounded delay: {}".format(sleep_time))
    if sleep_time > 0:
        time.sleep(sleep_time)

def wait_predictions_queue(Q,start):
    """
    WAIT FOR ALL PREDICTIONS TO BE DONE
    BY WAIT_TIME SPECIFIED
    """
    end = datetime.datetime.now()
    while datetime.timedelta.total_seconds(end - start) < WAIT_TIME:
        if Q.qsize() >= 3:
            break
        end = datetime.datetime.now()

    logging.debug("Done waiting for predictions queue")

def get_predictions_queue(Q):
    """
    GET PREDICTIONS FROM QUEUE, PER ID
    WILL RETURN A DICTIONARY PER ID
    CONTAINING SHIP_IDS, AND PREDICTIONS
    """
    q = {}
    logging.debug("At get_queue time: {}".format(datetime.datetime.now()))

    # if Q.empty():
    #     logging.debug("Q is empty")
    # else:
    #     while not Q.empty():
    #         id, ship_ids, data = Q.get()
    #         q[id] = (ship_ids,data)

    ## SINCE Q.empty() MAY NOT BE ACCURATE AND CAUSES .get() TO LOCK UP
    ## WE'LL USE TIMEOUT INSTEAD
    while True:
        try:
            item = Q.get(timeout=GET_TIMEOUT)
            if item:
                id, ship_ids, data = item
                q[id] = (ship_ids,data)
            else:
                break
        except Exception as e:
            logging.debug("Warning exception: {}".format(e))
            logging.debug("Q timed out")
            break

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

        # while not MP.predictors[id]["args_queue"].empty():
        #     logging.debug("Not empty")
        #     garbage = MP.predictors[id]["args_queue"].get()  ## False FOR NO WAIT (SEEMS TO TAKE MORE MEMORY WHEN FALSE)
        #     garbage = None
        #     logging.debug("Cleaned at {}".format(datetime.datetime.now()))

        ## SINCE Q.empty() MAY NOT BE ACCURATE AND CAUSES .get() TO LOCK UP
        ## WE'LL USE TIMEOUT INSTEAD
        while True:
            try:
                garbage = MP.predictors[id]["args_queue"].get(timeout=GET_TIMEOUT)
                if garbage:
                    garbage = None
                    logging.debug("Cleaned at {}".format(datetime.datetime.now()))
                else:
                    break
            except Exception as e:
                logging.debug("Warning exception: {}".format(e))
                garbage = None
                logging.debug("Cleaned timed out {}".format(datetime.datetime.now()))
                break

        ## LETS TRY JUST SETTING IT TO NONE, THEN INITIALIZE QUEUE()
        ## SETTING QUEUE TO NONE/QUEUE() DOESNT WORK (PIPE ERROR)
        # MP.predictors[id]["args_queue"] = None
        # MP.predictors[id]["args_queue"] = Queue()

    logging.debug("Done cleaning: {}".format(datetime.datetime.now()))

def model_handler(MP, turn, myMap, myMatrix):
    """
    HANDLES TRAINING AND PREDICTING ENEMY MODELS, PER ENEMY ID
    BEFORE, WAS PASSING NN TO THE ARGUMENTS AND WAS CAUSING ISSUE
    WHERE ITS TRAINING OLDER MODEL. NOW NO LONGER PASSING NN, GRAB NN
    FROM THE MODEL QUEUES TO ENSURE ITS THE LATEST ONE

    RETURNS PREDICTIONS AS DICTIONARY, WITH KEY OF ENEMY IDs
    """

    # start = datetime.datetime.now()
    #
    # for id in MP.enemyIDs:
    #     logging.debug("Model handler for player: {}".format(id))
    #
    #     ## GET DATA FOR TRAINING
    #     get_data_training(id, myMap, myMatrix, MP, turn)
    #
    #     ## GET DATA FOR PREDICTING
    #     get_data_predicting(id, myMap, myMatrix, MP, turn)
    #
    # ## GATHER/CLEANUP QUEUES
    # predictions = gather_clean_predictions(MP,start,turn)
    #
    # return predictions, turn + 1

    return None, turn + 1

def get_data_training(id, myMap, myMatrix, MP, turn):
    """
    GET DATA FOR TRAINING
    """
    args = None

    x_train, y_train = NeuralNet.get_training_data(id, myMap, myMatrix)
    if y_train is not None:
        args = ("train_" + str(id) + "_" + str(turn), id, x_train, y_train)
        MP.add_training(id, args)

    ## NO DIFFERENCE IN del OR SET TO None. EXCEPT del DELETE VARIABLE AS WELL
    # del x_train
    # del y_train
    # del args
    x_train, y_train, args = None, None, None

def get_data_predicting(id, myMap, myMatrix, MP, turn):
    """
    GET DATA FOR PREDICTING
    """
    args = None

    x_test, ship_ids = NeuralNet.get_predicting_data(id, myMap, myMatrix)
    if x_test is not None:
        args = ("pred_" + str(id) + "_" + str(turn), id, x_test, ship_ids)
        MP.add_predicting(id, args)
        logging.debug("Added to queue for predicting id: {} time: {}".format(str(id), datetime.datetime.now()))
        # MP.worker_predict_model("pred_" + str(id) + "_" + str(turn), id, x_train)  ## CALLS THE FUCTION DIRECTLY

    ## NO DIFFERENCE IN del OR SET TO None. EXCEPT del DELETE VARIABLE AS WELL
    # del x_test
    # del ship_ids
    # del args
    x_test, ship_ids, args = None, None, None


def gather_clean_predictions(MP,start,turn):
    """
    GATHER AND CLEAN UP PREDICTION QUEUES
    """
    wait_predictions_queue(MP.predictions_queue, start)
    predictions = get_predictions_queue(MP.predictions_queue)
    clean_predicting_args(MP)

    ## TERMINATE PREDICTORS THEN SPAWN THEM
    ## THIS HELPS MINIMIZE MEMORY CONSUMPTION TO 1GB?? NOPE
    ## ALSO LOG PER PREDICTORS ARE NOT TRACKED
    ## SPAWNING COULD TAKE 2 SECS, THUS NEED TO SPAWN AND TERMINATE DIFFERENT PROCESSES PER TURN
    ## THIS STILL CAUSES TO TAKE ALOT OF MEMORY!!!!
    ## clear_session() FIXES THE ISSUE
    #MP.terminate_predictors(turn%2) ## TERMINATE FOR THIS TURN
    #MP.spawn_predictors((turn+1)%2) ## SPAWN FOR NEXT TURN

    return predictions


if __name__ == "__main__":
    freeze_support()

    ## UPDATABLE PARAMETERS
    disable_log = False
    MAX_DELAY = 1.825 ## TO MAXIMIZE TIME PER TURN
    WAIT_TIME = 1.100 ## WAIT TIME FOR PREDICTIONS TO GET INTO QUEUE
    GET_TIMEOUT = 0.005 ## TIMEOUT SET FOR .GET()
    input_matrix_y = 27
    input_matrix_x = 27
    input_matrix_z = 4
    num_epoch = 2
    batch_size = 300

    ## BY DEFAULT, KERAS MODEL ARE NOT SERIALIZABLE
    ## TO PLACE IN QUEUE, NEED TO BE PICKLED
    #make_keras_picklable()  ## NO LONGER USED?

    ## GAME START
    ## INITIALIZES LOG
    game = hlt.Game("En3rG")
    logging.info("Starting my bot!")


    try:

        ## INITIALIZE PROCESSES
        ## THIS TAKES ALMOST 800MB OF MEMORY (EVEN WITH THIS FUNCTION ALONE)
        MP = MyProcesses(game,disable_log, WAIT_TIME, input_matrix_y, input_matrix_x, input_matrix_z, num_epoch, batch_size)

        ## PERFORM INITIALIZATION PREP
        EXP = Exploration(game)


    except Exception as e:
        logging.error("Error found: ==> {}".format(e))

        for index, frame in enumerate(traceback.extract_tb(sys.exc_info()[2])):
            fname, lineno, fn, text = frame
            logging.error("Error in {} on line {}".format(fname, lineno))


    ## ALLOW SOME TIME FOR CHILD PROCESSES TO SPAWN
    time.sleep(1)

    predictions = {}
    turn = 0
    myMap_prev = None
    myMatrix_prev = None

    ## DISABLE LOGS, IF TRUE
    MyCommon.disable_log(disable_log,logging)

    try:
        while True:
            main_start = datetime.datetime.now()
            logging.info("Turn # {} Calling update_map() at: {}".format(turn,datetime.datetime.now()))

            ## TURN START
            ## UPDATE THE MAP FOR THE NEW TURN AND GET THE LATEST VERSION
            game_map = game.update_map()
            logging.info("hlt update_map time: <<< {} >>>".format(datetime.timedelta.total_seconds(datetime.datetime.now() - main_start)))
            start = datetime.datetime.now()

            ## CONVERT game_map TO MY VERSION
            myMap = MyMap(game_map,myMap_prev)
            logging.info("myMap completed: <<< {} >>>".format(datetime.timedelta.total_seconds(datetime.datetime.now() - start)))
            start = datetime.datetime.now()

            ## GET PROJECTIONS OF ENEMY SHIPS
            myProjection = MyProjection(myMap)
            logging.info("myProjection completed: <<< {} >>>".format(datetime.timedelta.total_seconds(datetime.datetime.now() - start)))
            start = datetime.datetime.now()



            ## FOR TESTING ONLY
            ## SEE IF ENEMY IS ONCOMING
            myProjection.check_for_enemy()
            logging.info("myProjection.check_for_enemy completed: <<< {} >>>".format(datetime.timedelta.total_seconds(datetime.datetime.now() - start)))
            start = datetime.datetime.now()



            ## GATHER MAP MATRIX
            ## THIS WILL BE USED FOR MODEL PREDICTION
            ## PREVIOUS MATRIX WILL BE USED FOR TRAINING (ALONG WITH CURRENT myMap)
            myMatrix = MyMatrix(myMap,myMatrix_prev,input_matrix_y,input_matrix_x)
            logging.info("myMatrix completed: <<< {} >>>".format(datetime.timedelta.total_seconds(datetime.datetime.now() - start)))
            start = datetime.datetime.now()

            ## FOR TRAINING/PREDICTING MODEL
            predictions, turn = model_handler(MP,turn, myMap, myMatrix)
            logging.info("model_handler completed: <<< {} >>>".format(datetime.timedelta.total_seconds(datetime.datetime.now() - start)))
            start = datetime.datetime.now()
            ## GETTING MEMORY USAGE IS QUITE SLOW (TIMES OUT)
            # mem_usage = memory_usage((model_handler, (MP,turn, myMap, myMatrix)))
            # logging.debug("mem_usage: {}".format(mem_usage))

            ## TRANSLATE PREDICTIONS
            predicted_moves = NeuralNet.translate_predictions(predictions)
            myMatrix.fill_prediction_matrix(predicted_moves)
            logging.info("Predictions completed: <<< {} >>>".format(datetime.timedelta.total_seconds(datetime.datetime.now() - start)))
            start = datetime.datetime.now()

            ## INTIALIZE COMMANDS TO BE SENT TO HALITE ENGINE
            command_queue = []
            ## CURRENTLY FROM STARTER BOT MOVES
            #moves.starter_bot_moves(game_map,command_queue)
            ## MY MOVES
            #myMoves = moves.MyMoves(myMap, myMatrix, EXP)
            myMoves = moves2.MyMoves(myMap, myMatrix, EXP)
            command_queue = myMoves.command_queue
            logging.info("myMoves completed in <<< {} >>>.  Copying files".format(datetime.timedelta.total_seconds(datetime.datetime.now() - start)))
            start = datetime.datetime.now()

            ## SAVE OLD DATA FOR NEXT TURN
            ## WHEN USING DEEPCOPY SEEMS TO TIME OUT AFTER 7 TURNS
            myMap_prev = myMap
            myMatrix_prev = myMatrix

            ## SET A DELAY PER TURN
            #set_delay(main_start)
            logging.info("about to send commands {}".format(datetime.datetime.now()))
            logging.info("Command_queue: {}".format(command_queue))

            ## SEND OUR COMMANDS TO HALITE ENGINE THIS TURN
            game.send_command_queue(command_queue)
            ## TURN END
            logging.info("Commands send at {}".format(datetime.datetime.now()))


            ## TESTING ONLY
            log_myMap_ships(myMap)
            log_myMap_planets(myMap)

            ## FOR TESTING ONLY
            log_all_ships(myMap)
            log_all_planets(myMap)

            ## FOR TESTING ONLY
            # log_planets(game_map)
            # log_players(game_map)

            ## CLEAN UP OBJECTS NO LONGER REQUIRED NEXT TURN
            ## NECESSARY?? NOPE

            logging.info("Total Turn Elapse Time: <<< {} >>> at {}".format(datetime.timedelta.total_seconds(datetime.datetime.now() - main_start), datetime.datetime.now()))


    ## DELETE THIS LATER (FOR DEBUGGING ONLY)
    except Exception as e:
        """
        ERROR: not enough values to unpack (expected at least 1, got 0)

        CAUSES: - Invalid command queue (ie thrust 8)
                - Took over 2 secs
                - Printing out somewhere

        """
        logging.error("Error found: ==> {}".format(e))

        for index, frame in enumerate(traceback.extract_tb(sys.exc_info()[2])):
            fname, lineno, fn, text = frame
            logging.error("Error in {} on line {}".format(fname, lineno))

    finally:
        ## TERMINATE MULTIPROCESSES
        MP.exit = True
        #os.killpg(0, signal.SIGKILL) ## MP.exit SEEMS ENOUGH (NEED TO CLOSE WINDOW THOUGH)
        ## GAME END
