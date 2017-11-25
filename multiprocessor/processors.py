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
import MyCommon

class MyProcesses():
    def __init__(self,game,disable_log, wait_time, y, x, z):
        ## FOR TESTING ONLY
        #log_myID(game.map)
        #log_numPlayers(game.map)

        #self.main_conn, self.sub_conn = Pipe()  ## Not used

        ## DISABLE LOG IF TRUE
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
        #self.model_queues = self.init_model_queues()

        self.spawn_trainers()
        self.spawn_predictors()

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
            logging.info("NN: {}".format(NN.model))

            ## PROBLEM IS KERAS OBJECT CANNOT BE SERIALIZED OUT OF THE BAT??
            ## http://zachmoshe.com/2017/04/03/pickling-keras-models.html

            #q[id].put(NN.model)
            NN_model_pickled = pickle.dumps(NN.model)
            q[id].put(NN_model_pickled)

            logging.info("Q at init_model_queues empty?: {}".format(q[id].empty()))

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
        model.load_weights(str(id) + ".h5")
        logger.debug("Loaded weights")
        #sgd = SGD(lr=0.01, decay=1e-6, momentum=0.9, nesterov=True)
        sgd = NeuralNet.get_sgd()
        model.compile(loss='categorical_crossentropy', optimizer=sgd)
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
            #model = self.model_queues[id].get()
            #self.model_queues[id].put(copy.deepcopy(model))

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

        #self.model_queues[id].put(model)

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
            #self.trainers[id]["processor"] = self.init_process()
            self.trainers[id]["thread"] = None ## self.init_thread() ## <-- errors! why??
            self.trainers[id]["args_queue"] = Queue()



    def add_predicting(self,id,arguments):
        """
        ADD ARGUMENTS TO QUEUE FOR PREDICTING
        """

        ## CHANGING TO ADDING TO QUEUE
        self.predictors[id]["args_queue"].put(arguments)

    def spawn_predictors(self):
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
            #self.trainers[id]["handler"] = Process(target=self.trainer_handler, args=arguments)
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

                    ## USING MODELS IN QUEUES
                    # model = self.get_model_queues(id, logger)
                    # predictions = model.predict(x_train)
                    # logger.debug("Predictions done")

                    ## LOADING MODEL FROM FILE
                    model = self.load_model(id, logger)
                    logger.debug("Loaded model")
                    predictions = model.predict(x_train)
                    logger.debug("Predictions done")
                    ## WHEN I WAS PASSING Q IN ARGUMENTS, IT SEEMS TO MESS UP THE OTHER QUEUES
                    ## WORKS FINE WHEN IT WAS ADDED TO MP AS PREDICTIONS_QUEUE

                    end = time.clock()
                    logger.debug("Predictions took {}".format(end-start))

                    if (end-start) > (self.wait_time - 0.05):
                        logger.debug("Preditions took too long. Not placing to queue")
                    else:
                        self.predictions_queue.put((id, ship_ids, predictions))
                        logger.debug("Preditions placed in q")

                except:
                    pass

            else:
                logger.debug("Waiting...")

            time.sleep(0.05)

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
            #if not self.trainers[id]["args_queue"].empty():

            #if self.trainers[id]["args_queue"].qsize() > 1 and (self.trainers[id]["thread"] == None or self.trainers[id]["thread"].isAlive() == False):
            if not self.trainers[id]["args_queue"].empty() and (self.trainers[id]["thread"] == None or self.trainers[id]["thread"].isAlive() == False):
                logger.debug("Popping from Queue")
                arguments = self.trainers[id]["args_queue"].get()

                # self.trainers[id]["thread"] = Thread(target=self.worker_train_model, args=arguments)
                # #self.trainers[id]["thread"] = Thread(target=worker_train_model, args=arguments)
                # self.trainers[id]["thread"].start()

                ## DONT START THREADS ANYMORE, DO TRAINING IN THIS PROCESS
                name, id, x_train, y_train = arguments
                model = self.get_model_queues(id, logger)
                logger.info("Got Model")
                #model = copy.deepcopy(model)
                logger.info("Done copying {}".format(type(model)))
                model.fit(x_train, y_train, batch_size=200, epochs=1,verbose=1)  ## ERROR IS HERE. WHY? Sequential object has no attribute model
                logger.info("Trained")
                self.set_model_queues(id, model)
                logger.info("Time after training {}".format(time.clock()))


        ## USING PROCESSORS, NOT WORKING RIGHT
        # while self.exit == False:
        #     logger.debug("Queue Empty? {} Size: {}".format(self.trainers[id]["args_queue"].empty(),
        #                                                    self.trainers[id]["args_queue"].qsize()))
        #     logger.debug("Process status: {}".format(self.trainers[id]["processor"].is_alive() == False))
        #     #if not self.trainers[id]["args_queue"].empty():
        #     if not self.trainers[id]["args_queue"].empty() and not self.trainers[id]["processor"].is_alive(): ## causes error??
        #         logger.debug("Popping from Queue")
        #         arguments = self.trainers[id]["args_queue"].get()
        #         self.trainers[id]["processor"] = Process(target=self.test_delay, args=arguments)
        #         self.trainers[id]["processor"].start()

            time.sleep(0.05)

        #logger.debug("Kiling")
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


                ## USING THREADS DOESNT WORK AT ALL
                # self.trainers[id]["thread"] = Thread(target=self.worker_train_model2, args=arguments+(model,))
                # #self.trainers[id]["thread"] = Thread(target=worker_train_model, args=arguments)
                # self.trainers[id]["thread"].start()


                ## DONT START THREADS ANYMORE, DO TRAINING IN THIS PROCESS
                ## WORKS BUT GETTING UPDATED MAP FROM HLT ENGINE SLOWS DOWN AND TIMES OUT
                name, id, x_train, y_train = arguments
                logger.info("Got Model")
                start = time.clock()
                model.fit(x_train, y_train, batch_size=300, epochs=1,verbose=0)  ## ERROR IS HERE. WHY? Sequential object has no attribute model
                end = time.clock()
                logger.info("Trained")
                logger.info("Training took {}".format(end - start))
                self.save_model(id, model)
                end = time.clock()
                logger.info("Training and Saving model took {}".format(end - start))


            time.sleep(0.05)

        ## TERMINATE PROCESSES
        self.trainers[id]["processor"].terminate()
        self.trainers[id]["handler"].terminate()

    def add_training(self,id,arguments):
        """
        POPULATES THE QUEUE FROM THE MAIN PROCESS
        """
        self.trainers[id]["args_queue"].put(arguments)

    def worker_predict_model(self, name,id,x_train):
        """
        PREDICT MODEL ROM FILE
        """
        logger = MyCommon.get_logger(name)
        MyCommon.disable_log(self.disable_log, logging)
        try:
            # model = self.get_model_queues(id, logger)
            # predictions = model.predict(x_train)
            # logger.debug("Predictions done")
            start = time.clock()
            model = self.load_model(id,logger)
            logger.debug("Loaded model")
            predictions = model.predict(x_train)
            end = time.clock()
            logger.debug("Predictions done {}".format(end-start))
        except:
            pass


    def worker_train_model(self,name,id,x_train,y_train):
        """
        TRAIN MODEL TO QUEUE

        NO LONGER USED.
        """
        logger = MyCommon.get_logger(name)
        MyCommon.disable_log(self.disable_log, logging)
        logger.info("At {} and sleeping at {}".format(name, time.clock()))
        model = self.get_model_queues(id,logger)
        logger.info("Got Model")
        model = copy.deepcopy(model)
        logger.info("Done copying {}".format(type(model)))
        model.fit(x_train, y_train, batch_size=200, epochs=1, verbose=0)    ## ERROR IS HERE. WHY? Sequential object has no attribute model
        logger.info("Trained")
        self.set_model_queues(id, model)
        logger.info("Time after training {}".format(time.clock()))

    def worker_train_model2(self, name, id, x_train, y_train,model):
        """
        TRAIN MODEL TO FILE
        """
        logger = MyCommon.get_logger(name)
        MyCommon.disable_log(self.disable_log, logging)
        logger.info("At {} and sleeping at {}".format(name, time.clock()))
        logger.info("Got Model")
        logger.info("Done copying {}".format(type(model)))
        model.fit(x_train, y_train, batch_size=200, epochs=1,verbose=0)  ## ERROR IS HERE. WHY? Sequential object has no attribute model
        logger.info("Trained")
        self.save_model(id, model)
        logger.info("Time after training {}".format(time.clock()))






