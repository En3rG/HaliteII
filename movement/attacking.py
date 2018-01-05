import logging
import numpy as np
import MyCommon
import movement.expanding2 as expanding2
import heapq

def set_commands_status(MyMoves, ship_id, thrust, angle):
    ## SET COMMAND TO SEND
    MyMoves.command_queue.append(MyCommon.convert_for_command_queue(ship_id, thrust, angle))
    MyMoves.set_ship_moved_and_fill_position(ship_id, angle=angle, thrust=thrust, mining=True)

def get_battling_ships(MyMoves):
    handled_ships = set()  ## SHIPS THAT WILL BE ATTACKED WITHIN 5 MOVES

    heap = []

    ## GET SHIPS TO BE MOVE
    for k, v in MyMoves.myMap.ships_battling.items():
        if len(v) > 0:
            handled_ships.update(v)

    ## ONLY DETERMINE THE DISTANCES AND PLACE INTO THE HEAP, WILL MOVE LATER
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

                over_thrust = 10
                target_coord = MyCommon.get_destination_coord(ship_coords, angle, thrust=over_thrust)

                heapq.heappush(heap, (min_distance, ship_id, target_coord, over_thrust))

                #thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, target_coord, target_distance=over_thrust, target_planet_id=None)
                #set_commands_status(MyMoves, ship_id, thrust, angle)
            else:
                ## NO ENEMY FOUND AROUND ANY OF OUR SHIPS
                heapq.heappush(heap, (99999, ship_id, None, None))
                #closest_section_with_enemy(MyMoves, ship_id)

    ## MOVE SHIPS IN ORDER (TO MINIMIZE COLLISION)
    while heap:
        min_distance, ship_id, target_coord, over_thrust = heapq.heappop(heap)

        if target_coord:
            thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, target_coord, target_distance=over_thrust, target_planet_id=None)
            set_commands_status(MyMoves, ship_id, thrust, angle)
        else:
            ## NO ENEMY FOUND AROUND ANY OF OUR SHIPS
            closest_section_with_enemy(MyMoves, ship_id, move_now=True)

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

    NO LONGER USED?
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
        closest_section_with_enemy(MyMoves, ship_id)



def closest_section_with_enemy(MyMoves, ship_id, move_now=False):
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

    if move_now:
        thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, target_coord, final_distance, target_planet_id=None)
        set_commands_status(MyMoves, ship_id, thrust=thrust, angle=angle)
    else:
        return final_distance, target_coord
