
import MyCommon
import movement.expanding2 as expanding2

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
        ship_coord = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
        thrust, angle = find_enemy(MyMoves, ship_id)
        enemy_target_coord = MyCommon.get_destination_coord(ship_coord, angle, thrust, rounding=False)
        thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, enemy_target_coord, enemy_distance=10, target_planet_id=None)

        target_coord = None
        ship_task = MyCommon.ShipTasks.RUNNING
        set_commands_status(MyMoves, ship_id, thrust, angle, target_coord, ship_task)

def find_enemy(MyMoves, ship_id):
    ship_coords = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
    ship_section = MyCommon.get_section_num(ship_coords)
    ship_section_coord = MyCommon.Coordinates(ship_section[0], ship_section[1])
    distances = MyMoves.EXP.sections_distance_table[ship_section]
    values = MyMoves.myMap.section_enemy_summary

    ## GET CLOSEST/MOST ENEMIES SECTION POINT
    seek_val = 1
    enemy_section_point, section_distance = MyCommon.get_coord_closest_seek_value(seek_val, values, distances)
    enemy_section_coord = MyCommon.Coordinates(enemy_section_point[0], enemy_section_point[1])
    angle = MyCommon.get_angle(ship_section_coord, enemy_section_coord)
    thrust = 7

    if section_distance < 1.5: ## ENEMY IS CLOSE
        angle = MyCommon.get_reversed_angle(angle)

    return thrust, angle

