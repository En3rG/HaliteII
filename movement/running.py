
import MyCommon
import movement.expanding2 as expanding2
import logging
import traceback
import sys
from models.data import Matrix_val

def set_commands_status(MyMoves, ship_id, thrust, angle, target_coord, ship_task):
    """
    SET COMMAND TO SEND
    MOVE SHIP AND FILL POSITION MATRIX
    """
    MyMoves.command_queue.append(MyCommon.convert_for_command_queue(ship_id, thrust, angle))

    ship_coord = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
    target_type = MyCommon.Target.NOTHING
    target_id = None
    MyMoves.set_ship_statuses(ship_id, target_type ,target_id, ship_coord, ship_task, angle=angle, thrust=thrust, target_coord=target_coord)


def move_running_ships(MyMoves):
    """
    MOVE RUNNING/DISTRACTION SHIPS
    """

    for ship_id in MyMoves.myMap.myMap_prev.ships_running:
    #for ship_id in [0]:
        try:
            ship_coord = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
            thrust, angle = find_enemy(MyMoves, ship_id)
            enemy_target_coord = MyCommon.get_destination_coord(ship_coord, angle, thrust, rounding=False)
            thrust = 10 if thrust >= 7 else thrust
            thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, enemy_target_coord, target_distance=thrust, target_planet_id=None)

            target_coord = None
            ship_task = MyCommon.ShipTasks.RUNNING
            set_commands_status(MyMoves, ship_id, thrust, angle, target_coord, ship_task)

        except:
            pass


def find_enemy(MyMoves, ship_id):
    """
    LOOKS FOR CLOSEST ENEMY
    IF CLOSE, WILL RUN AWAY FROM IT
    IF FAR GO TOWARDS ENEMY
    """
    ship_coords = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
    ship_section = MyCommon.get_section_num(ship_coords)
    ship_section_coord = MyCommon.Coordinates(ship_section[0], ship_section[1])
    distances = MyMoves.EXP.sections_distance_table[ship_section]
    values = MyMoves.myMap.section_enemy_summary

    ## GET CLOSEST/MOST ENEMIES SECTION POINT
    seek_val = 1
    enemy_section_point, section_distance, enemy_val = MyCommon.get_coord_closest_seek_value(seek_val, values, distances)

    enemy_section_coord = MyCommon.Coordinates(enemy_section_point[0], enemy_section_point[1])
    angle = MyCommon.get_angle(ship_section_coord, enemy_section_coord)
    thrust = 7

    logging.debug("section_distance: {}".format(section_distance))

    if section_distance <= 2.3: ## ENEMY IS CLOSE
        value = MyMoves.myMatrix.matrix[MyMoves.myMap.my_id][0]  ## 1 IS FOR HP MATRIX
        v_enemy = MyCommon.get_section_with_padding(value, ship_coords, MyCommon.Constants.ATTACKING_RADIUS, 0)

        d_section = MyMoves.EXP.distance_matrix_RxR

        ## FIND ACTUAL COORDINATE OF CLOSEST ENEMY
        seek_val = -0.75
        enemy_point, enemy_distance, enemy_val = MyCommon.get_coord_closest_seek_value(seek_val, v_enemy, d_section)


        mid_point = (MyCommon.Constants.ATTACKING_RADIUS, MyCommon.Constants.ATTACKING_RADIUS)
        angle = MyCommon.get_angle(MyCommon.Coordinates(mid_point[0], mid_point[1]),
                                   MyCommon.Coordinates(enemy_point[0], enemy_point[1]))

        if enemy_val == Matrix_val.ENEMY_SHIP.value or -1 in v_enemy:  ## ONLY MOVE BACK IF ENEMY SHIP IS NOT DOCKED
        #if enemy_val == Matrix_val.ENEMY_SHIP.value:
            angle = MyCommon.get_reversed_angle(angle)
        elif enemy_distance <= 7:
            thrust = max(0, enemy_distance - 1)


    return thrust, angle

