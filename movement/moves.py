import logging
from testing.test_logs import log_players, log_planets, log_myShip, log_dimensions
import hlt

def starter_bot_moves(game_map,command_queue):
    """
    MOVES FROM STARTER BOT
    """
    ## FOR EVERY SHIP I CONTROL
    for ship in game_map.get_me().all_ships():

        log_myShip(ship)

        ## IF SHIP IS DOCKED
        if ship.docking_status != ship.DockingStatus.UNDOCKED:
            ## SKIP THIS SHIP
            continue

        ## FOR EACH PLANET IN THE GAME (ONLY NON-DESTROYED PLANETS ARE INCLUDED)
        for planet in game_map.all_planets():
            ## IF THE PLANET IS OWNED
            if planet.is_owned():
                ## SKIP THIS PLANET
                continue

            ## If we can dock, let's (try to) dock. If two ships try to dock at once, neither will be able to.
            if ship.can_dock(planet):
                ## We add the command by appending it to the command_queue
                command_queue.append(ship.dock(planet))
            else:
                ## If we can't dock, we move towards the closest empty point near this planet (by using closest_point_to)
                ## with constant speed. Don't worry about pathfinding for now, as the command will do it for you.
                ## We run this navigate command each turn until we arrive to get the latest move.
                ## Here we move at half our maximum speed to better control the ships
                ## In order to execute faster we also choose to ignore ship collision calculations during navigation.
                ## This will mean that you have a higher probability of crashing into ships, but it also means you will
                ## make move decisions much quicker. As your skill progresses and your moves turn more optimal you may
                ## wish to turn that option off.
                navigate_command = ship.navigate(ship.closest_point_to(planet), game_map,
                                                 speed=hlt.constants.MAX_SPEED / 2, ignore_ships=True)
                ## If the move is possible, add it to the command_queue (if there are too many obstacles on the way
                ## or we are trapped (or we reached our destination!), navigate_command will return null;
                ## don't fret though, we can run the command again the next turn)
                if navigate_command:
                    command_queue.append(navigate_command)
            break