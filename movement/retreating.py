import MyCommon
import logging
import movement.expanding2 as expanding2
import movement.attacking as attacking
import heapq
import initialization.astar as astar

def move_all_ships(MyMoves):
    """
    IF OUR SHIPS ARE ONLY A CERTAIN NUMBER OF PERCENTAGE
    BASED ON ALL ENEMY, WE UNDOCK AND MOVE TOWARDS THE CORNER
    CAN UPDATE LATER TO MOVE AROUND AND NOT JUST STAY IN THE CORNER
    """
    num_enemy = len(MyMoves.myMap.ships_enemy)
    num_ships = len(MyMoves.myMap.ships_owned)

    if num_enemy * MyCommon.Constants.RETREAT_PERCENTAGE > num_ships:
        logging.debug("RETREATING")
        MyMoves.retreating = True

        ## RETREAT ALL SHIPS

        ## UNDOCKED DOCKED SHIPS
        undock_ships(MyMoves)

        ## MOVE THE REST OF OUR SHIPS
        move_other_ships(MyMoves)


def undock_ships(MyMoves):
    """
    UNDOCK ALL DOCKED SHIPS
    """
    for ship_id in MyMoves.myMap.ships_mining_ally:
        ship_coord = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
        target_planet_id = None
        target_type = MyCommon.Target.NOTHING
        ship_task = MyCommon.ShipTasks.RETREATING
        MyMoves.set_ship_statuses(ship_id,
                                  target_type,
                                  target_planet_id,
                                  ship_coord,
                                  ship_task,
                                  angle=0,
                                  thrust=0,
                                  target_coord=None)
        MyMoves.command_queue.append(MyCommon.convert_for_command_queue(ship_id))

def move_other_ships(MyMoves):
    """
    MOVE ALL REMAINING SHIPS THAT HASNT BEEN MOVE YET AT THIS POINT
    FIRST GET ITS DISTANCE BASE ON CLOSEST ENEMY
    THEN MOVE SHPS FURTHEST FROM THE ENEMY FIRST, SINCE WE ARE RUNNING AWAY (TO AVOID COLLISIONS)
    """
    heap = []
    for ship_id, ship in MyMoves.myMap.data_ships[MyMoves.myMap.my_id].items():
        if ship_id not in MyMoves.myMap.ships_moved_already:
            enemy_distance, enemy_target_coord = attacking.closest_section_with_enemy(MyMoves,
                                                                                      ship_id,
                                                                                      move_now=False,
                                                                                      docked_only=False)
            logging.debug("ship_id: {} heap enemy distance: {}".format(ship_id, enemy_distance))
            heapq.heappush(heap, (-enemy_distance, ship_id)) ## WILL GO FROM FURTHEST TO CLOSEST FROM ENEMY


    while heap:
        enemy_distance, ship_id = heapq.heappop(heap)

        ship_coord = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
        target_planet_id = None
        target_type = MyCommon.Target.NOTHING
        ship_task = MyCommon.ShipTasks.RETREATING

        angle, thrust = get_to_closest_corner(MyMoves, ship_id, ship_coord)

        MyMoves.set_ship_statuses(ship_id,
                                  target_type,
                                  target_planet_id,
                                  ship_coord,
                                  ship_task,
                                  angle,
                                  thrust,
                                  target_coord=None)
        MyMoves.command_queue.append(MyCommon.convert_for_command_queue(ship_id, thrust, angle))


def get_to_closest_corner(MyMoves, ship_id, ship_coord):
    """
    GIVEN THE SHIP, WE DETERMINE WHERE THE CLOSEST CORNER IS
    THEN WE RETURN THE ANGLE/THRUST TOWARDS THAT CORNER
    """

    h = MyMoves.myMap.height - 2 ## SINCE WE ADDED BEFORE
    w = MyMoves.myMap.width - 2

    tl = MyCommon.Coordinates(1, 1)
    tr = MyCommon.Coordinates(1, w)
    bl = MyCommon.Coordinates(h, 1)
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

    thrust, angle = astar.get_thrust_angle_from_Astar(MyMoves,
                                                      ship_id,
                                                      closest_corner,
                                                      min_distance,
                                                      target_planet_id=None)

    return angle, thrust