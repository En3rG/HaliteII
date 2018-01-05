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
    """
    MOVE SHIPS THAT COULD BE IN BATTLE IN THE NEXT FIVE TURNS
    """
    heap = []

    ## GET SHIPS TO BE MOVED
    # for k, v in MyMoves.myMap.ships_battling.items():
    #     if len(v) > 0:
    #         handled_ships.update(v)

    ## FASTER WAY THAN LOOPING ABOVE
    handled_ships = set.union(*MyMoves.myMap.ships_battling.values())  ## * TO UNPACK OR ELSE WONT WORK

    logging.debug("handled_ships: {}".format(handled_ships))

    ## ONLY DETERMINE THE DISTANCES AND PLACE INTO THE HEAP, WILL MOVE LATER
    for ship_id in handled_ships:
        if ship_id not in MyMoves.myMap.ships_moved_already:
            ship_coords = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
            ship_section = MyCommon.get_section_num(ship_coords)
            ship_section_coord = MyCommon.Coordinates(ship_section[0], ship_section[1])
            distances = MyMoves.EXP.sections_distance_table[ship_section]
            values = MyMoves.myMap.section_summary

            logging.debug("ship_section: {}".format(ship_section))
            logging.debug("values: {}".format(values.shape))

            ## GET SECTIONED MATRIX
            # d_sectioned = distances[ship_section[0] - MyCommon.Constants.SIZE_SECTIONS_RADIUS:ship_section[0] + MyCommon.Constants.SIZE_SECTIONS_RADIUS + 1,
            #                         ship_section[1] - MyCommon.Constants.SIZE_SECTIONS_RADIUS:ship_section[1] + MyCommon.Constants.SIZE_SECTIONS_RADIUS + 1]
            #
            # v_sectioned = values[ship_section[0] - MyCommon.Constants.SIZE_SECTIONS_RADIUS:ship_section[0] + MyCommon.Constants.SIZE_SECTIONS_RADIUS + 1,
            #                      ship_section[1] - MyCommon.Constants.SIZE_SECTIONS_RADIUS:ship_section[1] + MyCommon.Constants.SIZE_SECTIONS_RADIUS + 1]


            ## NEED TO MASK WHEN SECTION IS OUT OF BOUNDS
            d_sectioned = MyCommon.get_section_with_padding(distances, ship_section_coord, MyCommon.Constants.SIZE_SECTIONS_RADIUS, 0)

            v_sectioned = MyCommon.get_section_with_padding(values, ship_section_coord, MyCommon.Constants.SIZE_SECTIONS_RADIUS, 0)


            ## GET CLOSEST/MOST ENEMIES SECTION POINT
            seek_val = 1
            enemy_section_point, min_distance = MyCommon.get_coord_closest_most_enemies_from_section(seek_val, v_sectioned, d_sectioned)

            logging.debug("enemy_section_point {} min_distance {}".format(enemy_section_point, min_distance))


            if enemy_section_point: ## AN ENEMY WAS FOUND
                ## PLACE THIS SECTION TO BATTLING
                set_section_in_battle(MyMoves, ship_section, enemy_section_point)

                angle = MyCommon.get_angle(MyCommon.Coordinates(MyCommon.Constants.SIZE_SECTIONS_RADIUS,MyCommon.Constants.SIZE_SECTIONS_RADIUS),
                                           MyCommon.Coordinates(enemy_section_point[0], enemy_section_point[1]))

                over_thrust = 10
                target_coord = MyCommon.get_destination_coord(ship_coords, angle, thrust=over_thrust)

                heapq.heappush(heap, (min_distance, ship_id, target_coord, over_thrust))

            else:
                ## NO ENEMY FOUND AROUND ANY OF OUR SHIPS
                ## THIS SHOULDNT HAPPEN RIGHT? OR ELSE WHY IS IT IN BATTLING
                heapq.heappush(heap, (99999, ship_id, None, None))

    ## MOVE SHIPS IN ORDER (TO MINIMIZE COLLISION)
    while heap:
        min_distance, ship_id, target_coord, over_thrust = heapq.heappop(heap)

        if min_distance == 0:
            logging.debug("ship_id: {} from handled_ships in same section".format(ship_id))
            ## ENEMY WITHIN THE SAME SECTION
            ship_coords = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
            ship_point = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['point']
            #ship_section = MyCommon.get_section_num(ship_coords)

            value = MyMoves.myMatrix.matrix[MyMoves.myMap.my_id][0]  ## 1 FOR HP MATRIX

            #v_section = value[ship_point[0]-7:ship_point[0]+7+1, ship_point[1]-7:ship_point[1]+7+1]
            v_section = MyCommon.get_section_with_padding(value, ship_coords, 7, 0)

            d_section = MyMoves.EXP.sample_distance_matrix

            ## FIND ACTUAL COORDINATE OF CLOSEST ENEMY
            seek_val = -0.75
            enemy_point, min_dist = MyCommon.get_coord_closest_most_enemies_from_section(seek_val, v_section, d_section)

            angle = MyCommon.get_angle(MyCommon.Coordinates(7,7), MyCommon.Coordinates(enemy_point[0], enemy_point[1]))

            ## ACTUAL COORDINATE OF ENEMY
            target_coord = MyCommon.get_destination_coord(ship_coords, angle, thrust=min_dist)

            logging.debug("Enemy found at target_coord: {}".format(target_coord))

            thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, target_coord, target_distance=min_dist, target_planet_id=None)
            set_commands_status(MyMoves, ship_id, thrust, angle)

        elif target_coord:
            logging.debug("ship_id: {} from handled_ships in different section".format(ship_id))
            thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, target_coord, target_distance=over_thrust, target_planet_id=None)
            logging.debug("thrust: {} angle: {}".format(thrust, angle))
            set_commands_status(MyMoves, ship_id, thrust, angle)
        else:
            logging.debug("ship_id: {} from handled_ships no enemy found around it".format(ship_id))
            ## NO ENEMY FOUND AROUND ANY OF OUR SHIPS
            closest_section_with_enemy(MyMoves, ship_id, move_now=True)

def set_section_in_battle(MyMoves, ship_section, enemy_section_point):
    """
    SET SECTIONS IN WAR
    """
    slope = (enemy_section_point[0] - MyCommon.Constants.SIZE_SECTIONS_RADIUS, enemy_section_point[1] - MyCommon.Constants.SIZE_SECTIONS_RADIUS)
    section = (ship_section[0] + slope[0], ship_section[1] + slope[1])

    MyMoves.myMap.section_in_battle.add(section)

def closest_section_in_battle(MyMoves, ship_id):
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

    final_distance = (min_distance + 1) * 7
    target_coord = MyCommon.get_coord_from_section(closest_section)

    if move_now:
        thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, target_coord, final_distance, target_planet_id=None)
        set_commands_status(MyMoves, ship_id, thrust=thrust, angle=angle)
    else:
        return final_distance, target_coord
