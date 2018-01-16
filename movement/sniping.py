import numpy as np
import MyCommon
import movement.attacking as attacking
import movement.expanding2 as expanding2
import logging
from models.data import Matrix_val


# def fill_position_matrix_intermediate_steps(MyMoves, ship_id, angle, thrust, mining):
#     """
#     FILL IN INTERMEDIATE POSITION MATRIXES
#     """
#     ship_coord = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
#     dx = thrust/7
#
#     for x in range(1, 7):  ## 7 WILL BE FILLED BY ANOTHER FUNCTION
#         intermediate_coord = MyCommon.get_destination_coord(ship_coord, angle, int(round(dx*x)))
#         intermediate_point = MyCommon.get_rounded_point(intermediate_coord)
#
#         # logging.debug("About to fill intermediate step: {}".format(x))
#         fill_position_matrix(MyMoves.position_matrix[x], intermediate_point, mining, intermediate=True)
#         # if thrust == 0:
#         #     ## IF THRUST IS 0, DOCKING
#         #     ## NEED TO FILL DIAGONALS
#         #     fill_position_matrix(MyMoves.position_matrix[x], intermediate_point, intermediate=False)
#         # else:
#         #     fill_position_matrix(MyMoves.position_matrix[x], intermediate_point, intermediate=True)
#
#     ## LAST TURN
#     x = 7
#     intermediate_coord = MyCommon.get_destination_coord(ship_coord, angle, int(round(dx * x)))
#     intermediate_point = MyCommon.get_rounded_point(intermediate_coord)
#
#     fill_position_matrix(MyMoves.position_matrix[x], intermediate_point, mining, intermediate=False)


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
    #for ship_id in [0]:
        try:
            thrust, angle = find_enemy(MyMoves, ship_id)

            target_coord = None
            ship_task = MyCommon.ShipTasks.SNIPING
            set_commands_status(MyMoves, ship_id, thrust, angle, target_coord, ship_task)

        except:
            pass


def find_enemy(MyMoves, ship_id):
    """
    LOOKS FOR CLOSEST DOCKED ENEMY
    """
    ship_coord = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']

    enemy_distance, enemy_target_coord = attacking.closest_section_with_enemy(MyMoves, ship_id, move_now=False, docked_only=True)
    angle = MyCommon.get_angle(ship_coord, enemy_target_coord)
    enemy_target_coord = MyCommon.get_destination_coord(ship_coord, angle, enemy_distance, rounding=False)
    thrust = 10 if enemy_distance >= 7 else enemy_distance

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

    r, c = np.where(v_enemy >= 1)


    thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, enemy_target_coord, target_distance=thrust, target_planet_id=None, override_section_matrix=section_matrixes)

    return thrust, angle
