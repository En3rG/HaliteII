import logging
from multiprocessing import Process, Pool, freeze_support, Queue, Lock
from testing.test_logs import log_myID, log_numPlayers

class MyProcesses():
    def __init__(self,game):
        ## For testing only
        log_myID(game.map)
        log_numPlayers(game.map)

        self.game_map = game.map
        self.myID = self.get_myID()
        self.predictor_processes = {}
        self.trainer_processes = {}
        self.enemyIDs = self.get_enemyID()
        self.get_predictors()
        self.get_trainers()

    def get_myID(self):
        return self.game_map.my_id

    def init_process(self):
        p = Process()
        p.start()
        p.terminate()
        return p

    def get_enemyID(self):
        """
        Get IDs of the enemy players
        """
        IDs = []

        for player in self.game_map.all_players():
            if self.myID != player.id:
                IDs.append(player.id)

        return IDs


    def get_predictors(self):
        """
        Initialize predictor processes as Player IDs
        """
        for player in self.game_map.all_players():
            if self.myID != player.id:
                self.predictor_processes[player.id] = self.init_process()

    def get_trainers(self):
        """
        Initialize trainer processes as Player IDs
        """
        for player in self.game_map.all_players():
            if self.myID != player.id:
                self.trainer_processes[player.id] = self.init_process()
