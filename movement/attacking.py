import logging
import numpy as np
import MyCommon

def get_battling_ships(MyMoves):
    handled_ships = set()  ## SHIPS THAT WILL BE ATTACKED WITHIN 5 MOVES

    # for ship_id in MyMoves.myMap.ships_battling[1]:

    for k, v in MyMoves.myMap.ships_battling.items():
        if len(v) > 0:
            handled_ships.update(v)

    for ship_id in handled_ships:
        logging.debug("ship_id to attack: {} ".format(ship_id))
        ship_coords = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
        ship_section = MyCommon.get_section(ship_coords)
        distances = MyMoves.EXP.sections_distance_table[ship_section]
        values = MyMoves.myMap.section_summary

        d_sectioned = distances[ship_section[0] - MyCommon.Constants.SIZE_SECTIONS_RADIUS:ship_section[0] + MyCommon.Constants.SIZE_SECTIONS_RADIUS + 1,
                                ship_section[1] - MyCommon.Constants.SIZE_SECTIONS_RADIUS:ship_section[1] + MyCommon.Constants.SIZE_SECTIONS_RADIUS + 1]

        v_sectioned = values[ship_section[0] - MyCommon.Constants.SIZE_SECTIONS_RADIUS:ship_section[0] + MyCommon.Constants.SIZE_SECTIONS_RADIUS + 1,
                             ship_section[1] - MyCommon.Constants.SIZE_SECTIONS_RADIUS:ship_section[1] + MyCommon.Constants.SIZE_SECTIONS_RADIUS + 1]

        enemy_section_point, min_distance = MyCommon.get_coord_closest_most_enemies_from_section(v_sectioned, d_sectioned)



        angle = MyCommon.get_angle(MyCommon.Coordinates(MyCommon.Constants.SIZE_SECTIONS_RADIUS,MyCommon.Constants.SIZE_SECTIONS_RADIUS),
                                   MyCommon.Coordinates(enemy_section_point[0], enemy_section_point[1]))
        thrust = 7

        MyMoves.command_queue.append(MyCommon.convert_for_command_queue(ship_id, thrust, angle))
        MyMoves.set_ship_moved_and_fill_position(ship_id, angle=angle, thrust=thrust, mining=True)