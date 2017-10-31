import logging
from testing.test_logs import log_players, log_planets, log_myShip, log_dimensions

class Exploration():
    def __init__(self,game):
        ## For testing only
        log_dimensions(game.map)
        log_planets(game.map)
        log_players(game.map)



