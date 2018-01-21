import numpy as np
import MyCommon
import movement.attacking as attacking
import movement.expanding2 as expanding2
import logging
import initialization.astar as astar
from models.data import Matrix_val


def set_commands_status(MyMoves, ship_id, thrust, angle, target_coord, ship_task):
    """
    SET COMMAND TO SEND
    MOVE SHIP AND FILL POSITION MATRIX
    """
    MyMoves.command_queue.append(MyCommon.convert_for_command_queue(ship_id, thrust, angle))
    ship_coord = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
    target_type = MyCommon.Target.SHIP
    target_id = None
    MyMoves.set_ship_statuses(ship_id, target_type ,target_id, ship_coord, ship_task, angle=angle, thrust=thrust, target_coord=target_coord)


def move_defending_ships(MyMoves):
    """
    GO THROUGH MINING SHIPS
    """
    for ship_id in MyMoves.myMap.ships_mining_ally:
        ship_coord = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']

        defend_if_enemy_near(MyMoves, ship_id, ship_coord)

def defend_if_enemy_near(MyMoves, ship_id, ship_coord):
    """
    CHECK IF ENEMY IS CLOSE BY OUR MINERS
    """
    value_array = MyMoves.myMatrix.matrix[MyMoves.myMap.my_id][0]  ## 1 IS FOR HP MATRIX
    v_section = MyCommon.get_section_with_padding(value_array, ship_coord, MyCommon.Constants.DEFENDING_PERIMETER_CHECK, pad_values=0)

    if Matrix_val.ENEMY_SHIP.value in v_section:
        ## ENEMY DETECTED, CALL FOR BACKUP

        seek_val = Matrix_val.ENEMY_SHIP.value
        d_section = MyMoves.EXP.distance_matrix_DxD
        enemy_point, distance, enemy_val = MyCommon.get_coord_closest_seek_value(seek_val, v_section, d_section)
        enemy_coord = MyCommon.Coordinates(enemy_point[0], enemy_point[1])
        mid_coord = MyCommon.Coordinates(MyCommon.Constants.DEFENDING_PERIMETER_CHECK, MyCommon.Constants.DEFENDING_PERIMETER_CHECK)
        angle = MyCommon.get_angle(mid_coord, enemy_coord)

        ## BEFORE: GETS A DEFEND COORD, THEN MOVE BACKUP TO THIS COORD
        # thrust = 7  ## AWAY FROM MINER
        # defend_coord = MyCommon.get_destination_coord(ship_coord, angle, thrust, rounding=False)

        ## GET BACKUP TO GO TO CLOSEST ENEMY
        target_coord = MyCommon.get_destination_coord(ship_coord, angle, distance, rounding=False)

        ship_task = MyCommon.ShipTasks.DEFENDING
        move_ships_towards_this_coord(MyMoves, ship_id, ship_task, target_coord)


def move_ships_towards_this_coord(MyMoves, ship_id, ship_task, defend_coord):
    """
    GET BACKUP SHIPS AROUND THIS AREA

    MOVE SHIPS CLOSEST TO THE BACK UP POINT FIRST
    """
    pad_values = -1
    area_matrix = MyCommon.get_circle_in_square(MyMoves.myMatrix.ally_matrix,
                                                defend_coord,
                                                MyCommon.Constants.DEFENDING_BACKUP_CIRCLE_RADIUS,
                                                MyCommon.Constants.DEFENDING_BACKUP_SQUARE_RADIUS,
                                                pad_values,
                                                pad_outside_circle=True)

    ships = MyCommon.get_ship_ids_in_array(area_matrix, MyMoves.EXP.distance_matrix_backup)

    logging.debug("ships {}".format(ships))

    for _ship_id in ships:
        _ship_id = int(_ship_id)
        if _ship_id != ship_id \
                and _ship_id not in MyMoves.myMap.ships_mining_ally \
                and _ship_id not in MyMoves.myMap.ships_moved_already:

            ## MOVE SHIP TOWARDS MINER
            _ship_coords = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][_ship_id]['coords']
            _d = MyCommon.calculate_distance(_ship_coords, defend_coord)
            _thrust, _angle = expanding2.get_thrust_angle_from_Astar(MyMoves, _ship_id, defend_coord, target_distance=_d, target_planet_id=None)
            set_commands_status(MyMoves, _ship_id, _thrust, _angle, defend_coord, ship_task)


