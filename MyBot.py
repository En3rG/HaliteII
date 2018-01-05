## DISABLE STDOUT, BY POINTING TO DEVNULL
import sys, os
stderr = sys.stderr
sys.stderr = open(os.devnull, 'w')


import hlt
import logging
from initialization.explore import Exploration
from testing.test_logs import log_players, log_planets, log_myShip, log_dimensions, log_all_ships, log_myMap_ships, \
                              log_myMap_planets, log_all_planets
import multiprocessor.processors as processors
from multiprocessor.processors import MyProcesses
from multiprocessing import freeze_support, Queue
#from models.model import NeuralNet, make_keras_picklable
from models.data import MyMap, MyMatrix
from projection.projection import MyProjection
from movement import moves
from movement import moves2
import MyCommon
import time
import copy
import numpy as np
import datetime
import os
import signal
#from memory_profiler import profile       ## USING @profile PER FUNCTIONS, RUN WITH -m memory_profile FLAG
#from memory_profiler import memory_usage
import traceback


## BEFORE IF MULTIPROCESS IS RUNNING, CAUSES ENGINE TO RECEIVE 'Using Tensorflow backend'. N/A ANYMORE.


if __name__ == "__main__":
    freeze_support()

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
        # MP = MyProcesses(game,
        #                  MyCommon.Constants.DISABLE_LOG,
        #                  MyCommon.Constants.WAIT_TIME,
        #                  MyCommon.Constants.INPUT_MATRIX_Y,
        #                  MyCommon.Constants.INPUT_MATRIX_X,
        #                  MyCommon.Constants.INPUT_MATRIX_Z,
        #                  MyCommon.Constants.NUM_EPOCH,
        #                  MyCommon.Constants.BATCH_SIZE)

        start = datetime.datetime.now()

        ## PERFORM INITIALIZATION PREP
        EXP = Exploration(game)

        logging.info("EXP time: <<< {} >>>".format(datetime.timedelta.total_seconds(datetime.datetime.now() - start)))

    except Exception as e:
        logging.error("Error found: ==> {}".format(e))

        for index, frame in enumerate(traceback.extract_tb(sys.exc_info()[2])):
            fname, lineno, fn, text = frame
            logging.error("Error in {} on line {}".format(fname, lineno))


    ## ALLOW SOME TIME FOR CHILD PROCESSES TO SPAWN
    time.sleep(2)

    predictions = {}
    turn = 0
    myMap_prev = None
    myMatrix_prev = None

    ## DISABLE LOGS, IF TRUE
    MyCommon.disable_log(MyCommon.Constants.DISABLE_LOG,logging)

    ## REENABLE STDOUT
    sys.stderr = stderr

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
            myMatrix = MyMatrix(myMap,myMatrix_prev,MyCommon.Constants.INPUT_MATRIX_Y,MyCommon.Constants.INPUT_MATRIX_X)
            logging.info("myMatrix completed: <<< {} >>>".format(datetime.timedelta.total_seconds(datetime.datetime.now() - start)))
            start = datetime.datetime.now()

            ## FOR TRAINING/PREDICTING MODEL
            #predictions, turn = processors.model_handler(MP,turn, myMap, myMatrix)
            turn += 1
            logging.info("model_handler completed: <<< {} >>>".format(datetime.timedelta.total_seconds(datetime.datetime.now() - start)))
            start = datetime.datetime.now()
            ## GETTING MEMORY USAGE IS QUITE SLOW (TIMES OUT)
            # mem_usage = memory_usage((model_handler, (MP,turn, myMap, myMatrix)))
            # logging.debug("mem_usage: {}".format(mem_usage))

            ## TRANSLATE PREDICTIONS
            #predicted_moves = NeuralNet.translate_predictions(predictions)
            #myMatrix.fill_prediction_matrix(predicted_moves)
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
            #processors.set_delay(main_start)
            logging.info("about to send commands {}".format(datetime.datetime.now()))
            logging.info("at turn: {} Command_queue: {}".format(turn-1, command_queue))

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
        #MP.exit = True
        #os.killpg(0, signal.SIGKILL) ## MP.exit SEEMS ENOUGH (NEED TO CLOSE WINDOW THOUGH)
        ## GAME END
        pass


## KERAS/TENSORFLOW ERROR ON SERVER. COMMENT OUT THE FOLLOWING
## - KERAS IMPORT
## - MP
## - MODEL_HANDLER
## - PREDICTION
## - SET_DELAY
## - MP.exit = True



## OLD MAP USED
## .\halite -d "240 160" -s "326461518" "python MyBot.py" "python StarterBot.py" "python MyBot.py" "python StarterBot.py"
## .\halite -d "240 160" -s "4160918419" "python MyBot.py" "python StarterBot.py" "python MyBot.py" "python StarterBot.py"