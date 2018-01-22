import logging
from multiprocessing import Process, Pool, freeze_support, Queue, Lock, Value, Array, Pipe ## recv waits until something??
#from testing.test_logs import log_myID, log_numPlayers
import time
import sys
from collections import deque
from threading import Thread
#sys.path.append("../models")
from models.model import NeuralNet
import copy
import pickle
from keras.models import model_from_json
from keras.optimizers import SGD
import keras
import MyCommon
import datetime
import gc
import tensorflow as tf



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
    sleep_time = MyCommon.Constants.MAX_DELAY - used
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
    while datetime.timedelta.total_seconds(end - start) < MyCommon.Constants.WAIT_TIME:
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

    ## SINCE Q.empty() MAY NOT BE ACCURATE AND CAUSES .get() TO LOCK UP
    ## WE'LL USE TIMEOUT INSTEAD
    while True:
        try:
            item = Q.get(timeout=MyCommon.Constants.GET_TIMEOUT)
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

        ## SINCE Q.empty() MAY NOT BE ACCURATE AND CAUSES .get() TO LOCK UP
        ## WE'LL USE TIMEOUT INSTEAD
        while True:
            try:
                garbage = MP.predictors[id]["args_queue"].get(timeout=MyCommon.Constants.GET_TIMEOUT)
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


    logging.debug("Done cleaning: {}".format(datetime.datetime.now()))

def model_handler(MP, turn, myMap, myMatrix):
    """
    HANDLES TRAINING AND PREDICTING ENEMY MODELS, PER ENEMY ID
    BEFORE, WAS PASSING NN TO THE ARGUMENTS AND WAS CAUSING ISSUE
    WHERE ITS TRAINING OLDER MODEL. NOW NO LONGER PASSING NN, GRAB NN
    FROM THE MODEL QUEUES TO ENSURE ITS THE LATEST ONE

    RETURNS PREDICTIONS AS DICTIONARY, WITH KEY OF ENEMY IDs
    """

    start = datetime.datetime.now()

    for id in MP.enemyIDs:
        logging.debug("Model handler for player: {}".format(id))

        ## GET DATA FOR TRAINING
        get_data_training(id, myMap, myMatrix, MP, turn)

        ## GET DATA FOR PREDICTING
        get_data_predicting(id, myMap, myMatrix, MP, turn)

    ## GATHER/CLEANUP QUEUES
    predictions = gather_clean_predictions(MP,start,turn)

    return predictions, turn + 1


def get_data_training(id, myMap, myMatrix, MP, turn):
    """
    GET DATA FOR TRAINING
    """
    args = None

    x_train, y_train = NeuralNet.get_training_data(id, myMap, myMatrix)
    if y_train is not None:
        args = ("train_" + str(id) + "_" + str(turn), id, x_train, y_train)
        MP.add_training(id, args)

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


def gather_clean_predictions(MP,start,turn):
    """
    GATHER AND CLEAN UP PREDICTION QUEUES
    """
    wait_predictions_queue(MP.predictions_queue, start)
    predictions = get_predictions_queue(MP.predictions_queue)
    clean_predicting_args(MP)

    return predictions




class MyProcesses():
    def __init__(self,game,disable_log, wait_time, y, x, z, num_epoch, batch_size):

        ## DISABLE LOG IF TRUE
        self.num_epoch = num_epoch
        self.batch_size = batch_size
        self.disable_log = disable_log
        MyCommon.disable_log(self.disable_log, logging)

        self.y = y
        self.x = x
        self.z = z
        self.game_map = game.map
        self.wait_time = wait_time
        self.myID = self.get_myID()
        self.enemyIDs = self.get_enemyID()
        self.predictors = {}
        self.trainers = {}
        self.set_predictors()
        self.set_trainers()
        self.exit = False
        self.predictions_queue = Queue()

        self.spawn_trainers()
        self.spawn_predictors(1)

    def get_myID(self):
        """
        GET MY ID
        FROM THE ENGINE, PLAYER IDs ARE INTEGER
        """
        return self.game_map.my_id

    def get_enemyID(self):
        """
        GET IDs OF THE ENEMY PLAYERS, AS INTEGERS
        """
        IDs = []

        for player in self.game_map.all_players():
            id = player.id
            if self.myID != id:
                IDs.append(id)

        return IDs

    def init_process(self):
        """
        INITIALIZE A PROCESS AND TERMINATE.
        IS THIS NECESSARY?
        CURRENTLY NOT USED, JUST INITIALIZING TO None
        """
        p = Process()
        p.start()
        p.terminate()
        return p

    def init_thread(self):
        """
        INITIALIZE A THREAD
        NOT USED.  THREADS ARE CURRENTLY INITIALIZED TO None
        """
        thread = Thread()
        thread.start()
        return thread

    def init_model_queues(self):
        """
        INITIALIZE QUEUES FOR COMMUNICATING WITH THE MAIN PROCESS.
        ONE PER ENEMY ID

        NO LONGER USED.  SAVING MODEL AS A FILE
        """
        q = {}
        for id in self.enemyIDs:
            q[id] = Queue()

            ## INITIALIZE MODELS
            NN = NeuralNet(self.y,self.x,self.z)
            logging.debug("NN: {}".format(NN.model))

            ## PROBLEM IS KERAS OBJECT CANNOT BE SERIALIZED OUT OF THE BAT??
            ## http://zachmoshe.com/2017/04/03/pickling-keras-models.html

            #q[id].put(NN.model)
            NN_model_pickled = pickle.dumps(NN.model)
            q[id].put(NN_model_pickled)

            logging.debug("Q at init_model_queues empty?: {}".format(q[id].empty()))

        return q

    def init_save_model(self,id):
        """
        SAVE MODELS/WEIGHTS TO FILE
        PER ENEMY ID SPECIFIED
        """
        NN = NeuralNet(self.y,self.x,self.z)
        model_json = NN.model.to_json()
        with open(str(id) + ".json", "w") as json_file:
            json_file.write(model_json)

        ## SERIALIZE WEIGHTS TO HDF5
        NN.model.save_weights(str(id) + ".h5")

        return NN.model

    def save_model(self,id,model):
        """
        SAVE MODELS/WEIGHTS TO FILE
        USED AFTER TRAINING A MODEL
        """
        model_json = model.to_json()
        with open(str(id) + ".json", "w") as json_file:
            json_file.write(model_json)

        ## SERIALIZE WEIGHTS TO HDF5
        model.save_weights(str(id) + ".h5")

    def load_model(self, id,logger):
        """
        LOAD MODELS/WEIGHTS FROME FILE

        THIS TAKES ABOUT 0.4 SECS.  ALMOST SAME AS UNPICKLING A PICKLED MODEL
        """
        json_file = open(str(id) + ".json", "r")
        logger.debug("Json file found")
        loaded_model_json = json_file.read()
        logger.debug("Json file read")
        json_file.close()
        logger.debug("Json file closed")
        model = model_from_json(loaded_model_json)
        logger.debug("Model loaded")

        ## LOAD WEIGHTS INTO MODEL
        try:
            model.load_weights(str(id) + ".h5")
        except Exception as e:
            ## FAILED (TRAINER POSSIBLY SAVING IT)
            logger.error("Error loading: {}.  Wait and try again".format(e))
            time.sleep(0.05)
            model.load_weights(str(id) + ".h5")

        logger.debug("Loaded weights")
        #sgd = SGD(lr=0.01, decay=1e-6, momentum=0.9, nesterov=True)
        opt = NeuralNet.get_optimizer()
        model.compile(loss='categorical_crossentropy', optimizer=opt)
        logger.debug("Compiled model")

        return model

    def get_model_queues(self,id,logger):
        """
        RETURN THE MODEL IN THE QUEUE
        MAKES A COPY JUST IN CASE ITS THE LAST ITEM IN THE QUEUE

        NO LONGER USED.
        """
        if self.model_queues[id].empty():
            model = None
            logger.error("get_model_queues called but its empty!!!")
        else:
            model_pickled = self.model_queues[id].get()
            model = pickle.loads(model_pickled)
            self.model_queues[id].put(model_pickled)

        return model

    def set_model_queues(self,id,model):
        """
        RESETS THE QUEUE WITH THE MODEL
        FIRST REMOVE ALL ITEMS IN THE QUEUE
        SETTING QUEUE TO NONE/QUEUE() DOESNT WORK

        NO LONGER USED.
        """
        if not self.model_queues[id].empty():
            discard = self.model_queues[id].get()
            discard = None

        model_pickled = pickle.dumps(model)
        self.model_queues[id].put(model_pickled)


    def set_predictors(self):
        """
        INITIALIZE PREDICTOR PROCESSES AS PLAYER IDs
        """
        for id in self.enemyIDs:
            self.predictors[id] = {}
            self.predictors[id]["handler"] = None
            self.predictors[id]["args_queue"] = Queue()

    def set_trainers(self):
        """
        INITIALIZE TRAINER PROCESSES AS PLAYER IDs
        """
        for id in self.enemyIDs:
            self.trainers[id] = {}
            self.trainers[id]["handler"] = None
            self.trainers[id]["thread"] = None ## self.init_thread() ## <-- errors! why??
            self.trainers[id]["args_queue"] = Queue()



    def add_predicting(self,id,arguments):
        """
        ADD ARGUMENTS TO QUEUE FOR PREDICTING
        """

        ## CHANGING TO ADDING TO QUEUE
        self.predictors[id]["args_queue"].put(arguments)

        ## MINIMIZE MEMORY CONSUMPTION (DOESNT REALLY DO ANYTHING)
        arguments = None

    def terminate_predictors(self,odd_even_turn):
        """
        TERMINATE ALL SPAWNED PREDICTORS

        NO LONGER USED
        """
        logging.debug("About to terminate predictors at: {}".format(datetime.datetime.now()))
        for id in self.enemyIDs:
            self.predictors[id]["handler"].terminate()


    def spawn_predictors(self,odd_even_turn):
        """
        STARTS HANDLER PROCESSES PER ENEMY ID

        BEFORE SPAWNING PREDICTORS, WAS ALWAYS SPAWNING PROCESSORS PER TURN PER ENEMY IDs, WHICH WAS TIMING OUT
        THIS SEEMS TO BE A BETTER ARCHITECTURE
        """
        for id in self.enemyIDs:
            arguments = (id,)
            self.predictors[id]["handler"] = Process(target=self.predictor_handler, args=arguments)
            self.predictors[id]["handler"].start()


    def spawn_trainers(self):
        """
        STARTS HANDLER PROCESSES PER ENEMY ID
        """
        for id in self.enemyIDs:
            arguments = (id,)
            self.trainers[id]["handler"] = Process(target=self.trainer_handler2, args=arguments)
            self.trainers[id]["handler"].start()

    def predictor_handler(self, id):
        """
        HANDLES PREDICTIONS

        IF TAKING MORE THAN XX, DO NOT PUT INTO QUEUE
        """
        logger = MyCommon.get_logger(str(id) + "_predictor_handler")
        MyCommon.disable_log(self.disable_log,logging)
        logger.debug("Handler for {}".format(str(id)))

        ## USING THREADS
        while self.exit == False:
            if not self.predictors[id]["args_queue"].empty():
                logger.debug("Popping from Queue")
                arguments = self.predictors[id]["args_queue"].get()
                name, id, x_train, ship_ids = arguments

                try:
                    start = time.clock()

                    ## IS THIS REALLY REQUIRED TO clear_session? I DONT THINK SO
                    config = tf.ConfigProto(intra_op_parallelism_threads=4,
                                            inter_op_parallelism_threads=4,
                                            allow_soft_placement=True)
                    session = tf.Session(config=config)
                    keras.backend.set_session(session)


                    ## LOADING MODEL FROM FILE
                    model = self.load_model(id, logger)
                    logger.info("Loaded model")
                    predictions = model.predict(x_train)
                    logger.info("Predictions done")
                    ## WHEN I WAS PASSING Q IN ARGUMENTS, IT SEEMS TO MESS UP THE OTHER QUEUES
                    ## WORKS FINE WHEN IT WAS ADDED TO MP AS PREDICTIONS_QUEUE


                    end = time.clock()
                    logger.info("Predictions took {}".format(end-start))

                    if (end-start) > (self.wait_time - 0.05):
                        logger.debug("Preditions took too long. Not placing to queue")
                    else:
                        self.predictions_queue.put((id, ship_ids, predictions))
                        logger.debug("Preditions placed in q")

                except Exception as e:
                    logger.error("predictor_handler error: {}".format(str(e)))

                ## MINIMIZE MEMORY CONSUMPTION
                arguments, model, predictions = None, None, None ## DOESNT REALLY DO MUCH
                keras.backend.clear_session() ## THIS REALLY HELPS THOUGH
                gc.collect() ## DOESNT REALLY DO MUCH

            else:
                logger.debug("Waiting...")

            time.sleep(0.10)


        ## TERMINATE PROCESS
        self.predictors[id]["handler"].terminate()


    def trainer_handler(self,id):
        """
        HANDLES THE PROCESS FOR TRAINING, PER ID
        TRAINING A MODEL COULD TAKE LONGER THAN 2 SECS
        AVOID HAVING THE TRAINING TAKE MORE THAN 2 SECS THOUGH

        MODEL.FIT STILL NOT WORKING HERE. EVEN AFTER COMPILING AFTER UNPICKING

        NO LONGER USED.
        """

        logger = MyCommon.get_logger(str(id) + "_trainer_handler")
        MyCommon.disable_log(self.disable_log,logging)
        logger.debug("Handler for {}".format(str(id)))

        ## USING THREADS
        while self.exit == False:
            logger.debug("Queue Empty? {} Size: {}".format(self.trainers[id]["args_queue"].empty(),self.trainers[id]["args_queue"].qsize()))

            if not self.trainers[id]["args_queue"].empty() and (self.trainers[id]["thread"] == None or self.trainers[id]["thread"].isAlive() == False):
                logger.debug("Popping from Queue")
                arguments = self.trainers[id]["args_queue"].get()

                ## DONT START THREADS ANYMORE, DO TRAINING IN THIS PROCESS
                name, id, x_train, y_train = arguments
                model = self.get_model_queues(id, logger)
                logger.info("Got Model")
                logger.info("Done copying {}".format(type(model)))
                model.fit(x_train, y_train, batch_size=self.batch_size, epochs=self.num_epoch,verbose=1)  ## ERROR IS HERE. WHY? Sequential object has no attribute model
                logger.info("Trained")
                self.set_model_queues(id, model)
                logger.info("Time after training {}".format(time.clock()))

            time.sleep(0.05)

        self.trainers[id]["processor"].terminate()
        self.trainers[id]["handler"].terminate()

    def trainer_handler2(self, id):
        """
        LOADING/SAVING THE MODEL IN JSON
        WAS ERRORING BEFORE ON FIT SINCE I FORGOT TO COMPILE THE MODEL AFTER LOADING

        HANDLES THE PROCESS FOR TRAINING, PER ID
        TRAINING A MODEL COULD TAKE LONGER THAN 2 SECS
        AVOID HAVING THE TRAINING TAKE MORE THAN 2 SECS THOUGH
        """
        from keras.models import Sequential
        from keras.layers import Dense, Dropout, Flatten
        from keras.layers import Conv2D, MaxPooling2D
        from keras.models import model_from_json
        from keras.utils import np_utils
        from keras import optimizers
        from keras import regularizers
        from keras.optimizers import SGD
        import keras

        ## UPDATED SO MODEL WILL NEVER BE READ ON THIS THREAD
        model = self.init_save_model(id)

        logger = MyCommon.get_logger(str(id) + "_trainer_handler")
        MyCommon.disable_log(self.disable_log, logging)
        logger.debug("Handler for {}".format(str(id)))

        while self.exit == False:
            logger.debug("Queue Empty? {} Size: {}".format(self.trainers[id]["args_queue"].empty(),self.trainers[id]["args_queue"].qsize()))

            if not self.trainers[id]["args_queue"].empty() and (self.trainers[id]["thread"] == None or self.trainers[id]["thread"].isAlive() == False):
                logger.debug("Popping from Queue")
                arguments = self.trainers[id]["args_queue"].get()

                ## DONT START THREADS ANYMORE, DO TRAINING IN THIS PROCESS
                ## WORKS BUT GETTING UPDATED MAP FROM HLT ENGINE SLOWS DOWN AND TIMES OUT
                name, id, x_train, y_train = arguments
                logger.info("Got Model")
                start = time.clock()
                model.fit(x_train, y_train, batch_size=self.batch_size, epochs=self.num_epoch,verbose=0)  ## ERROR IS HERE. WHY? Sequential object has no attribute model
                end = time.clock()
                logger.info("Trained")
                logger.info("Training took {}".format(end - start))
                self.save_model(id, model)
                end = time.clock()
                logger.info("Training and Saving model took {}".format(end - start))


            time.sleep(0.05)
            ## MINIMIZE MEMORY CONSUMPTION
            arguments = None ## NOT REALLY DOING MUCH


        ## TERMINATE PROCESSES
        self.trainers[id]["processor"].terminate()
        self.trainers[id]["handler"].terminate()

    def add_training(self,id,arguments):
        """
        POPULATES THE QUEUE FROM THE MAIN PROCESS
        """
        self.trainers[id]["args_queue"].put(arguments)

        ## MINIMIZE MEMORY CONSUMPTION
        arguments = None ## NOT REALLY DOING MUCH








