import logging
import numpy as np
import MyCommon
import movement.expanding2 as expanding2

def set_commands_status(MyMoves, ship_id, thrust, angle):
    ## SET COMMAND TO SEND
    MyMoves.command_queue.append(MyCommon.convert_for_command_queue(ship_id, thrust, angle))
    MyMoves.set_ship_moved_and_fill_position(ship_id, angle=angle, thrust=thrust, mining=True)

def get_battling_ships(MyMoves):
    handled_ships = set()  ## SHIPS THAT WILL BE ATTACKED WITHIN 5 MOVES

    ## ENEMY WITHIN IMMEDIATE REACH
    # for ship_id in MyMoves.myMap.ships_battling[1]:
    #     ship_coords = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
    #     enemy_coords = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['enemy_coords'][1] ## GRAB TURN 1 ONLY
    #
    #     y, x = enemy_coords[0] ## JUST GRAB FIRST COORDS
    #     enemy_coord = MyCommon.Coordinates(y, x)
    #
    #     thrust = 7 if MyCommon.calculate_distance(ship_coords, enemy_coord) > 7 else MyCommon.calculate_distance(ship_coords, enemy_coord)
    #     angle = MyCommon.get_angle(ship_coords, enemy_coord)
    #
    #     set_commands_status(MyMoves, ship_id, thrust, angle)


    ## REST OF SHIPS TO BE MOVED
    for k, v in MyMoves.myMap.ships_battling.items():
        if len(v) > 0:
            handled_ships.update(v)

    for ship_id in handled_ships:
        if ship_id not in MyMoves.myMap.ships_moved_already:
            logging.debug("ship_id to attack: {} ".format(ship_id))
            ship_coords = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
            ship_section = MyCommon.get_section_num(ship_coords)
            distances = MyMoves.EXP.sections_distance_table[ship_section]
            values = MyMoves.myMap.section_summary

            ## GET SECTIONED MATRIX
            d_sectioned = distances[ship_section[0] - MyCommon.Constants.SIZE_SECTIONS_RADIUS:ship_section[0] + MyCommon.Constants.SIZE_SECTIONS_RADIUS + 1,
                                    ship_section[1] - MyCommon.Constants.SIZE_SECTIONS_RADIUS:ship_section[1] + MyCommon.Constants.SIZE_SECTIONS_RADIUS + 1]

            v_sectioned = values[ship_section[0] - MyCommon.Constants.SIZE_SECTIONS_RADIUS:ship_section[0] + MyCommon.Constants.SIZE_SECTIONS_RADIUS + 1,
                                 ship_section[1] - MyCommon.Constants.SIZE_SECTIONS_RADIUS:ship_section[1] + MyCommon.Constants.SIZE_SECTIONS_RADIUS + 1]

            ## GET CLOSEST/MOST ENEMIES SECTION POINT
            enemy_section_point, min_distance = MyCommon.get_coord_closest_most_enemies_from_section(v_sectioned, d_sectioned)

            if enemy_section_point:
                set_section_in_battle(MyMoves, ship_section, enemy_section_point)

                angle = MyCommon.get_angle(MyCommon.Coordinates(MyCommon.Constants.SIZE_SECTIONS_RADIUS,MyCommon.Constants.SIZE_SECTIONS_RADIUS),
                                           MyCommon.Coordinates(enemy_section_point[0], enemy_section_point[1]))
                thrust = 7

                set_commands_status(MyMoves, ship_id, thrust, angle)
            else:
                ## NO ENEMY FOUND AROUND ANY OF OUR SHIPS
                thrust, angle = closest_section_with_enemy(MyMoves, ship_id)
                set_commands_status(MyMoves, ship_id, thrust=thrust, angle=angle)

def set_section_in_battle(MyMoves, ship_section, enemy_section_point):
    """
    SET SECTIONS IN WAR
    """
    slope = (enemy_section_point[0] - MyCommon.Constants.SIZE_SECTIONS_RADIUS, enemy_section_point[1] - MyCommon.Constants.SIZE_SECTIONS_RADIUS)
    section = (ship_section[0] + slope[0], ship_section[1] + slope[1])

    MyMoves.myMap.section_in_battle.add(section)

def closest_section_in_war(MyMoves, ship_id):
    """
    GET CLOSEST SECTION IN WAR AND GO THERE
    """
    ship_coords = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
    ship_section = MyCommon.get_section_num(ship_coords)

    min_distance = 99999
    closest_section = None

    ## GET CLOSEST SECTION IN BATTLE
    for section in MyMoves.myMap.section_in_battle:
        distance = MyMoves.EXP.sections_distance_table[ship_section][section[0]][section[1]]

        if distance < min_distance:
            closest_section = section
            min_distance = distance

    if closest_section:
        final_distance = min_distance*7
        target_coord = MyCommon.get_coord_from_section(closest_section)

        thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, target_coord, final_distance, target_planet_id=None)

        set_commands_status(MyMoves, ship_id, thrust, angle)
    else:
        ## NO SECTION IN BATTLE
        thrust, angle = closest_section_with_enemy(MyMoves, ship_id)
        set_commands_status(MyMoves, ship_id, thrust=thrust, angle=angle)


def closest_section_with_enemy(MyMoves, ship_id):
    """
    GET CLOSEST SECTION WITH ENEMY
    """
    ship_coords = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
    ship_section = MyCommon.get_section_num(ship_coords)

    min_distance = 99999
    closest_section = None

    ## GET CLOSEST SECTION WITH ENEMY
    for section in MyMoves.myMap.section_with_enemy:
        distance = MyMoves.EXP.sections_distance_table[ship_section][section[0]][section[1]]

        if distance < min_distance:
            closest_section = section
            min_distance = distance

    final_distance = min_distance * 7
    target_coord = MyCommon.get_coord_from_section(closest_section)

    thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, target_coord, final_distance, target_planet_id=None)

    return thrust, angle
