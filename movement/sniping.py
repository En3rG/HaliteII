import numpy as np
import MyCommon
import movement.attacking as attacking
import movement.expanding2 as expanding2
import logging
import initialization.astar as astar
from models.data import Matrix_val


def fill_matrix_intermediate_steps(center, r, c, section_matrixes):
    """
    FILL IN INTERMEDIATE ATTACK RANGE OF ENEMY
    """
    center_coord = MyCommon.Coordinates(center, center)

    for r, c in zip(r, c):
        enemy_coord = MyCommon.Coordinates(r, c)
        angle = MyCommon.get_angle(enemy_coord, center_coord)
        distance = MyCommon.calculate_distance(enemy_coord, center_coord,rounding=True)
        thrust = 7 if distance > 7 else distance
        dx = thrust/7
        value = 1

        for x in range(1, 7):
            intermediate_coord = MyCommon.get_destination_coord(enemy_coord, angle, int(round(dx*x)))
            intermediate_point = MyCommon.get_rounded_point(intermediate_coord)

            intermediate_coord = MyCommon.Coordinates(intermediate_point[0], intermediate_point[1])
            MyCommon.fill_circle(section_matrixes[x], intermediate_coord, MyCommon.Constants.ATTACK_RADIUS, value)

        ## LAST TURN
        x = 7
        intermediate_coord = MyCommon.get_destination_coord(enemy_coord, angle, int(round(dx * x)))
        intermediate_point = MyCommon.get_rounded_point(intermediate_coord)

        intermediate_coord = MyCommon.Coordinates(intermediate_point[0], intermediate_point[1])
        MyCommon.fill_circle(section_matrixes[x], intermediate_coord, MyCommon.Constants.ATTACK_RADIUS, value)


    return section_matrixes



def take_Astar_section(center, section_matrixes):
    """
    CROP SECTION MATRIX TO MATCH A* SECTION MATRIX
    """
    new_section_matrixes = {}
    center_coord = MyCommon.Coordinates(center, center)
    pad_values = -1

    for x in range(1,8):
        new_section_matrixes[x] = MyCommon.get_circle_in_square(section_matrixes[x],
                                                                center_coord,
                                                                MyCommon.Constants.ASTAR_CIRCLE_RADIUS,
                                                                MyCommon.Constants.ASTAR_SQUARE_RADIUS,
                                                                pad_values)

    return new_section_matrixes

def set_commands_status(MyMoves, ship_id, thrust, angle, target_coord, ship_task):
    """
    SET COMMAND TO SEND
    MOVE SHIP AND FILL POSITION MATRIX
    """
    MyMoves.command_queue.append(MyCommon.convert_for_command_queue(ship_id, thrust, angle))

    ship_coord = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
    target_type = MyCommon.Target.NOTHING
    target_id = None
    logging.debug("moving ship_id: {} in sniping".format(ship_id))
    MyMoves.set_ship_statuses(ship_id, target_type ,target_id, ship_coord, ship_task, angle=angle, thrust=thrust, target_coord=target_coord)


def move_sniping_ships(MyMoves):
    """
    MOVE SHIP TOWARDS ASSASSINATING ENEMY DOCKED SHIPS
    """
    for ship_id in MyMoves.myMap.myMap_prev.ships_sniping:
    #for ship_id in [2]:

        if ship_id not in MyMoves.myMap.ships_moved_already:
            try:
                logging.debug("At move sniping ships ship_id {}".format(ship_id))
                thrust, angle = find_enemy(MyMoves, ship_id)

                target_coord = None
                ship_task = MyCommon.ShipTasks.SNIPING
                set_commands_status(MyMoves, ship_id, thrust, angle, target_coord, ship_task)

                ## ADD IT BACK TO SNIPING SHIPS
                MyMoves.myMap.ships_sniping.add(ship_id)
            except:
                logging.debug("Except hit for ship_id {}".format(ship_id))
                pass


def find_enemy(MyMoves, ship_id):
    """
    LOOKS FOR CLOSEST DOCKED ENEMY
    """
    ship_coord = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']

    enemy_distance, enemy_target_coord = attacking.closest_section_with_enemy(MyMoves, ship_id, move_now=False, docked_only=True)
    angle = MyCommon.get_angle(ship_coord, enemy_target_coord)
    enemy_target_coord = MyCommon.get_destination_coord(ship_coord, angle, enemy_distance, rounding=False)
    thrust = 7 if enemy_distance >= 7 else enemy_distance

    square_radius = 16
    circle_radius = 15

    ## GET POSITION MATRIX
    pad_values = -1
    section_matrixes = {}
    for step in range(1, 8):
        section_matrixes[step] = MyCommon.get_circle_in_square(MyMoves.position_matrix[step],
                                                               ship_coord,
                                                               circle_radius,
                                                               square_radius,
                                                               pad_values)

    value = MyMoves.myMatrix.matrix[MyMoves.myMap.my_id][0]  ## 1 IS FOR HP MATRIX
    v_enemy = MyCommon.get_section_with_padding(value, ship_coord, square_radius, 0)

    r, c = np.where(v_enemy == -1)

    center = square_radius
    section_matrixes = fill_matrix_intermediate_steps(center, r, c, section_matrixes)

    section_matrixes = take_Astar_section(center, section_matrixes)

    mid_point = (8, 8)
    mid_coord = MyCommon.Coordinates(8, 8)
    section_target_coord = MyCommon.get_destination_coord(mid_coord,angle, thrust)
    path_points = astar.a_star2(section_matrixes, mid_point, (section_target_coord.y, section_target_coord.x))

    next_coord = MyCommon.Coordinates(path_points[-2][0], path_points[-2][1])
    angle = MyCommon.get_angle(mid_coord, next_coord)
    thrust = 7
    return thrust, angle

