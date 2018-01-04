import logging
import numpy as np

def get_battling_ships(MyMoves):
    handled_ships = set()

    # for ship_id in MyMoves.myMap.ships_battling[1]:
    #     ship_coords = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
    #     enemy_coords = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['enemy_coords']
    #
    #     logging.debug("enemy_cords {}".format(enemy_coords))
    #
    #     to_points = []
    #     for row in enemy_coords:
    #         for y, x in row:
    #             to_points.append((y,x))
    #
    #
    #     ## GET DISTANCES BETWEEN point and a set of points
    #     start = np.array([ship_coords.y, ship_coords.x])
    #
    #     distances = np.linalg.norm(to_points - start, ord=2, axis=1.)  # distances is a list
    #
    #     logging.debug("distances!!!!!!: {}".format(distances))

    # for ship_id in MyMoves.myMap.ships_battling[2]:
    #
    # for ship_id in MyMoves.myMap.ships_battling[3]:
    #
    # for ship_id in MyMoves.myMap.ships_battling[4]:
    #
    # for ship_id in MyMoves.myMap.ships_battling[5]: