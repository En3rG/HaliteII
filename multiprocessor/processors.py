import logging
from multiprocessing import Process, Pool, freeze_support, Queue, Lock, Value, Array, Pipe ## recv waits until something??
#from testing.test_logs import log_myID, log_numPlayers
import time
from collections import deque
from threading import Thread

class MyProcesses():
    def __init__(self,game):
        ## FOR TESTING ONLY
        #log_myID(game.map)
        #log_numPlayers(game.map)

        #self.main_conn, self.sub_conn = Pipe()  ## Not used
        self.game_map = game.map
        self.myID = self.get_myID()
        self.enemyIDs = self.get_enemyID()
        self.predictors = {}
        self.trainers = {}
        self.set_predictors()
        self.set_trainers()
        self.exit = False
        self.queues = self.set_queues()

        self.trainer_handler()

    def get_myID(self):
        """
        GET MY ID, AS STRING
        FORM THE ENGINE, PLAYER IDs ARE INTs
        """
        return str(self.game_map.my_id)

    def get_enemyID(self):
        """
        GET IDs OF THE ENEMY PLAYERS, AS STRINGS
        """
        IDs = []

        for player in self.game_map.all_players():
            id = str(player.id)
            if self.myID != id:
                IDs.append(id)

        return IDs

    def init_process(self):
        """
        INITIALIZE A PROCESS AND TERMINATE.
        IS THIS NECESSARY? SHOULD WE JUST INITIALIZE TO None?
        """
        p = Process()
        p.start()
        p.terminate()
        return p

    def init_thread(self):
        thread = Thread()
        thread.start()
        return thread

    def set_queues(self):
        """
        INITIALIZE QUEUES FOR COMMUNICATING WITH THE MAIN PROCESS.
        ONE PER ENEMY ID
        """
        q = {}
        for id in self.enemyIDs:
            q[id] = Queue()

        return q

    def set_predictors(self):
        """
        INITIALIZE PREDICTOR PROCESSES AS PLAYER IDs
        """
        for id in self.enemyIDs:
            self.predictors[id] = None
            #self.predictors[id] = self.init_process()  ## HAVING JUST THIS IS MUCH SLOWER, WHY?

            # self.predictors[id] = {}
            # self.predictors[id]["processor"] = self.init_process()

    def set_trainers(self):
        """
        INITIALIZE TRAINER PROCESSES AS PLAYER IDs
        """
        for id in self.enemyIDs:
            self.trainers[id] = {}
            self.trainers[id]["handler"] = None
            self.trainers[id]["processor"] = self.init_process()
            self.trainers[id]["thread"] = None ## self.init_thread() ## <-- errors! why??
            self.trainers[id]["args_queue"] = Queue()

    def get_logger(self,name):
        """
        CREATE A LOGGER PER PROCESSOR
        """
        ## INITIALIZE LOGGING
        fh = logging.FileHandler(name + '.log')
        fmt = logging.Formatter("%(asctime)-6s: %(name)s - %(levelname)s - %(message)s)")
        fh.setFormatter(fmt)
        local_logger = logging.getLogger(name)
        local_logger.setLevel(logging.DEBUG)
        # local_logger = multiprocessing.get_logger()
        local_logger.addHandler(fh)
        local_logger.info(name + ' (worker) Process started')

        return local_logger

    def worker_predictor(self,id,arguments):
        """
        START A PROCESS FOR PREDICTING
        PREDICTION SHOULD TAKE 1 SEC? SINCE WE STILL NEED TO PERFORM OUR ALGORITHM PER SHIP'S MOVEMENT
        """
        ## Making it a thread makes it pass the keras/mutiprocess issue
        if self.predictors[id] is None or self.predictors[id].isAlive() == False:
            self.predictors[id] = Thread(target=self.test_delay, args=arguments)
            self.predictors[id].start()

        # if self.predictors[id] is None or self.predictors[id].is_alive() == False:
        #     self.predictors[id] = Process(target=self.test_delay, args=arguments)
        #     self.predictors[id].start()

        # if self.predictors[id]["processor"].is_alive() == False:
        #     self.predictors[id]["processor"] = Process(target=self.test_delay, args=arguments)
        #     self.predictors[id]["processor"].start()

    def trainer_handler(self):
        """
        STARTS HANDLER PROCESSES PER ENEMY ID
        """
        for id in self.enemyIDs:
            arguments = [id]
            self.trainers[id]["handler"] = Process(target=self.handler, args=arguments)
            self.trainers[id]["handler"].start()

    def handler(self,id):
        """
        HANDLES THE PROCESS FOR TRAINING
        TRAINING A MODEL COULD TAKE LONGER THAN 2 SECS
        AVOID HAVING THE TRAINING TAKE MORE THAN 2 SECS THOUGH
        """
        logger = self.get_logger(id)
        logger.debug("Handler for {}".format(id))

        ## USING THREADS
        while self.exit == False:
            logger.debug("Queue Empty? {} Size: {}".format(self.trainers[id]["args_queue"].empty(),self.trainers[id]["args_queue"].qsize()))
            #if not self.trainers[id]["args_queue"].empty():
            if not self.trainers[id]["args_queue"].empty() and (self.trainers[id]["thread"] == None or not self.trainers[id]["thread"].isAlive()):
                logger.debug("Popping from Queue")
                arguments = self.trainers[id]["args_queue"].get()
                self.trainers[id]["thread"] = Thread(target=self.test_delay, args=arguments)
                self.trainers[id]["thread"].start()

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

            time.sleep(0.20)

        #logger.debug("Kiling")
        self.trainers[id]["processor"].terminate()
        self.trainers[id]["handler"].terminate()

    def worker_trainer(self,id,arguments):
        """
        POPULATES THE QUEUE FROM THE MAIN PROCESS
        """
        self.trainers[id]["args_queue"].put(arguments)
        #self.trainers[id]["args_queue"].append(arguments)

        # ## WHY IS THIS MUCH FASTER THAN WORKER_PREDICTOR??
        # if self.trainers[id]["processor"].is_alive() == False:
        #     self.trainers[id]["processor"] = Process(target=self.test_delay, args=arguments)
        #     self.trainers[id]["processor"].start()
        #     #self.trainers[id]["processor"].join()  ## If you join it'll timeout
        # else:
        #     self.trainers[id]["args_queue"].append(arguments)

    def test_delay(self,name,num):
        ## WHEN GENERATING LOGS, TIMES OUT EVEN AT 0.5 PER PLAYER?
        logger = self.get_logger(name)
        logger.info("At {} and sleeping at {}".format(name,time.clock()))
        time.sleep(num)
        logger.info("Time after sleep {}".format(time.clock()))


