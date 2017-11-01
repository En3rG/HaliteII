import logging
from multiprocessing import Process, Pool, freeze_support, Queue, Lock, Value, Array, Pipe ## recv waits until something??
#from testing.test_logs import log_myID, log_numPlayers
import time
from collections import deque
from threading import Thread

class MyProcesses():
    def __init__(self,game):
        ## For testing only
        #log_myID(game.map)
        #log_numPlayers(game.map)

        self.main_conn, self.sub_conn = Pipe()
        self.game_map = game.map
        self.myID = self.get_myID()
        self.enemyIDs = self.get_enemyID()
        self.predictor_processes = {}
        self.trainer_processes = {}
        self.set_predictors()
        self.set_trainers()
        self.exit = False

        self.trainer_handler()



    def get_myID(self):
        """
        Get my ID
        """
        return str(self.game_map.my_id)  ## was int before

    def get_enemyID(self):
        """
        Get IDs of the enemy players
        """
        IDs = []

        for player in self.game_map.all_players():
            player_id = str(player.id)
            if self.myID != player_id:
                IDs.append(player_id)

        return IDs

    def init_process(self):
        """
        Initialize a process and terminate
        """
        p = Process()
        p.start()
        p.terminate()
        return p

    def init_thread(self):
        thread = Thread()
        thread.start()
        return thread

    def set_predictors(self):
        """
        Initialize predictor processes as Player IDs
        """
        for player in self.game_map.all_players():
            player_id = str(player.id)
            if self.myID != player_id:
                #self.predictor_processes[player.id] = self.init_process()  ## HAVING JUST THIS IS MUCH SLOWER, WHY?

                self.predictor_processes[player_id] = {}
                self.predictor_processes[player_id]["processor"] = self.init_process()

    def set_trainers(self):
        """
        Initialize trainer processes as Player IDs
        """
        for player in self.game_map.all_players():
            player_id = str(player.id)
            if self.myID != player_id:
                self.trainer_processes[player_id] = {}
                self.trainer_processes[player_id]["handler"] = None
                self.trainer_processes[player_id]["processor"] = self.init_process()
                self.trainer_processes[player_id]["thread"] = None ## self.init_thread() ## <-- errors?
                self.trainer_processes[player_id]["args_queue"] = Queue()

    def get_logger(self,name):
        """
        Create a logger per processor (doesnt work for multithread??)
        """
        ## Initialize logging
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
        Start a process for predicting
        """
        if self.predictor_processes[id]["processor"].is_alive() == False:
            self.predictor_processes[id]["processor"] = Process(target=self.test_delay, args=arguments)
            self.predictor_processes[id]["processor"].start()

    def handler(self,MP,id):
        """
        Handles the process for training
        """
        logger = self.get_logger(id)
        logger.debug("Handler for {}".format(id))

        while self.exit == False:
            logger.debug("Queue Empty? {} Size: {}".format(self.trainer_processes[id]["args_queue"].empty(),self.trainer_processes[id]["args_queue"].qsize()))
            if not self.trainer_processes[id]["args_queue"].empty():
                logger.debug("Popping from Queue")
                arguments = self.trainer_processes[id]["args_queue"].get()
                self.trainer_processes[id]["thread"] = Thread(target=self.test_delay, args=arguments)
                self.trainer_processes[id]["thread"].start()

            time.sleep(0.0)

        #logger.debug("Kiling")
        self.trainer_processes[id]["processor"].terminate()
        self.trainer_processes[id]["handler"].terminate()

    def trainer_handler(self):
        """
        Starts handler processes per enemy ID
        """
        for id in self.enemyIDs:
            arguments = [self,id]
            self.trainer_processes[id]["handler"] = Process(target=self.handler, args=arguments)
            self.trainer_processes[id]["handler"].start()


    def worker_trainer(self,id,arguments):
        """
        Populates the queue from the main process
        """
        self.trainer_processes[id]["args_queue"].put(arguments)
        #self.trainer_processes[id]["args_queue"].append(arguments)

        # ## WHY IS THIS MUCH FASTER THAN WORKER_PREDICTOR??
        # if self.trainer_processes[id]["processor"].is_alive() == False:
        #     self.trainer_processes[id]["processor"] = Process(target=self.test_delay, args=arguments)
        #     self.trainer_processes[id]["processor"].start()
        #     #self.trainer_processes[id]["processor"].join()  ## If you join it'll timeout
        # else:
        #     self.trainer_processes[id]["args_queue"].append(arguments)

    def test_delay(self,name,num):
        ## When generating logs, times out even at 0.5 per player
        logger = self.get_logger(name)
        logger.info("At {} and sleeping at {}".format(name,time.clock()))
        time.sleep(num)
        logger.info("Time after sleep {}".format(time.clock()))


