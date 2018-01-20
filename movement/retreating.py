import MyCommon
import logging
import movement.expanding2 as expanding2

def move_all_ships(MyMoves):
    num_enemy = len(MyMoves.myMap.ships_enemy)
    num_ships = len(MyMoves.myMap.ships_owned)

    if num_enemy * MyCommon.Constants.RETREAT_PERCENTAGE > num_ships:
        logging.debug("RETREATING")
        ## RETREAT ALL SHIPS

        ## UNDOCKED DOCKED SHIPS
        undock_ships(MyMoves)

        ## MOVE THE REST OF OUR SHIPS
        move_other_ships(MyMoves)


def undock_ships(MyMoves):
    for ship_id in MyMoves.myMap.ships_mining_ally:
        ship_coord = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
        target_planet_id = None
        target_type = MyCommon.Target.NOTHING
        ship_task = MyCommon.ShipTasks.RETREATING
        MyMoves.set_ship_statuses(ship_id, target_type, target_planet_id, ship_coord, ship_task, angle=0, thrust=0, target_coord=None)
        MyMoves.command_queue.append(MyCommon.convert_for_command_queue(ship_id))

def move_other_ships(MyMoves):
    for ship_id, ship in MyMoves.myMap.data_ships[MyMoves.myMap.my_id].items():
        if ship_id not in MyMoves.myMap.ships_moved_already:
            ship_coord = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
            target_planet_id = None
            target_type = MyCommon.Target.NOTHING
            ship_task = MyCommon.ShipTasks.RETREATING

            angle, thrust = get_to_closest_corner(MyMoves, ship_id, ship_coord)

            MyMoves.set_ship_statuses(ship_id, target_type, target_planet_id, ship_coord, ship_task, angle, thrust, target_coord=None)
            MyMoves.command_queue.append(MyCommon.convert_for_command_queue(ship_id, thrust, angle))

def get_to_closest_corner(MyMoves, ship_id, ship_coord):
    h = MyMoves.myMap.height - 1 ## SINCE WE ADDED BEFORE
    w = MyMoves.myMap.width - 1

    tl = MyCommon.Coordinates(0, 0)
    tr = MyCommon.Coordinates(0, w)
    bl = MyCommon.Coordinates(h, 0)
    br = MyCommon.Coordinates(h, w)
    corners = [tl, tr, bl, br]

    ## GET CLOSEST CORNER
    min_distance = MyCommon.Constants.BIG_DISTANCE
    closest_corner = None
    for corner_coord in corners:
        distance = MyCommon.calculate_distance(ship_coord, corner_coord, rounding=False)

        if distance < min_distance:
            min_distance = distance
            closest_corner = corner_coord

    thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, closest_corner, min_distance, target_planet_id=None)

    return angle, thrust