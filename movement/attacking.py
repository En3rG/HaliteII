import logging
import numpy as np
import MyCommon
import movement.expanding2 as expanding2
import heapq
from models.data import Matrix_val

def set_commands_status(MyMoves, ship_id, thrust, angle, target_coord, ship_task):
    """
    SET COMMAND TO SEND
    MOVE SHIP AND FILL POSITION MATRIX
    """
    MyMoves.command_queue.append(MyCommon.convert_for_command_queue(ship_id, thrust, angle))
    #MyMoves.set_ship_moved_and_fill_position(ship_id, angle=angle, thrust=thrust, mining=False)
    ship_coord = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
    target_type = MyCommon.Target.SHIP
    target_id = None
    MyMoves.set_ship_statuses(ship_id, target_type ,target_id, ship_coord, ship_task, angle=angle, thrust=thrust, target_coord=target_coord)


def move_battling_ships(MyMoves):
    """
    MOVE SHIPS THAT COULD BE IN BATTLE IN THE NEXT FIVE TURNS
    """
    battle_heap = []

    ## GET SHIPS TO BE MOVED
    # for k, v in MyMoves.myMap.ships_battling.items():
    #     if len(v) > 0:
    #         handled_ships.update(v)

    ## FASTER WAY THAN LOOPING ABOVE
    ## BASICALLY COMBINING ALL SET FROM THE DICTIONARY
    #handled_ships = set.union(*MyMoves.myMap.ships_battling.values())  ## * TO UNPACK OR ELSE WONT WORK

    # ## MOVE SHIPS FROM PROJECTIONS
    # for ship_id in handled_ships:
    #     if ship_id not in MyMoves.myMap.ships_moved_already:
    #         get_battling_ships_heap(MyMoves, ship_id, battle_heap)
    #
    # ## MOVE SHIPS IN ORDER (TO MINIMIZE COLLISIONS)
    # move_battle_heap(MyMoves, battle_heap)

    ## ONLY DETERMINE THE DISTANCES AND PLACE INTO THE HEAP, WILL MOVE LATER
    for ship_id, ship in MyMoves.myMap.data_ships[MyMoves.myMap.my_id].items(): ## INSTEAD OF JUST LOOPING THROUGH HANDLED_SHIPS
        if ship_id not in MyMoves.myMap.ships_moved_already:
            get_battling_ships_heap(MyMoves, ship_id, battle_heap)

    ## MOVE SHIPS IN ORDER (TO MINIMIZE COLLISIONS)
    move_battle_heap(MyMoves, battle_heap)

def get_battling_ships_heap(MyMoves, ship_id, battle_heap):
    """
    GET SHIPS INFO (IF BATTLING)
    """
    ship_coords = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
    ship_section = MyCommon.get_section_num(ship_coords)
    ship_section_coord = MyCommon.Coordinates(ship_section[0], ship_section[1])

    ## CHECK IF ENEMIES WITHIN A PERIMETER
    enemy_matrix = MyMoves.myMatrix.matrix[MyMoves.myMap.my_id][0]  ## 1 FOR HP MATRIX
    perimeter = MyCommon.get_section_with_padding(enemy_matrix, ship_coords, MyCommon.Constants.PERIMETER_CHECK_RADIUS, pad_values=0)

    if Matrix_val.ENEMY_SHIP.value not in perimeter and Matrix_val.ENEMY_SHIP_DOCKED.value not in perimeter:
        ## NO ENEMY FOUND, SKIP
        logging.debug("ship_id: {} did not find any enemy".format(ship_id))
        return

    logging.debug("ship_id:: {} ship_coords: {} ship_section: {}".format(ship_id,ship_coords,ship_section))

    distances = MyMoves.EXP.sections_distance_table[ship_section]
    values = MyMoves.myMap.section_enemy_summary

    ## GET SECTIONED MATRIX
    ## NEED TO MASK WHEN SECTION IS OUT OF BOUNDS
    d_sectioned = MyCommon.get_section_with_padding(distances, ship_section_coord, MyCommon.Constants.SIZE_SECTIONS_RADIUS, 0)
    v_sectioned = MyCommon.get_section_with_padding(values, ship_section_coord, MyCommon.Constants.SIZE_SECTIONS_RADIUS, 0)

    ## GET CLOSEST/MOST ENEMIES SECTION POINT
    seek_val = 1
    enemy_section_point, section_distance, enemy_val = MyCommon.get_coord_closest_seek_value(seek_val, v_sectioned, d_sectioned)

    #logging.debug("v_sectioned {}".format(v_sectioned))

    if enemy_section_point: ## AN ENEMY WAS FOUND (CLOSEST AND MOST ENEMY)
        ## PLACE THIS SECTION TO BATTLING
        set_section_in_battle(MyMoves, ship_section, enemy_section_point) ## NO LONGER USED?

        ## IF WITHIN ATTACKING_RADIUS
        #if section_distance == 0:
        #if section_distance == 0 or section_distance == 1:
        if section_distance <= 1.5:
            ## ENEMY WITHIN THE SAME SECTION


            ## USING SECTIONED FOUND ABOVE
            # slope = (enemy_section_point[0] - MyCommon.Constants.SIZE_SECTIONS_RADIUS,
            #          enemy_section_point[1] - MyCommon.Constants.SIZE_SECTIONS_RADIUS)
            # actual_enemy_section_point = (ship_section[0] + slope[0], ship_section[1] + slope[1])
            # enemy_section_coord = MyCommon.get_coord_from_section(actual_enemy_section_point)
            # strong_enough, v_enemy = check_if_strong_enough(MyMoves, enemy_section_coord)
            # angle = MyCommon.get_angle(ship_coords, enemy_section_coord)
            # enemy_distance = MyCommon.calculate_distance(ship_coords, enemy_section_coord, rounding=False)

            ## FIND ACTUAL COORDINATE OF CLOSEST ENEMY (ORIG LIKE BOT50)
            strong_enough, v_enemy = check_if_strong_enough(MyMoves, ship_coords)
            seek_val = -0.75
            d_section = MyMoves.EXP.distance_matrix_AxA
            enemy_point, enemy_distance, enemy_val = MyCommon.get_coord_closest_seek_value(seek_val, v_enemy, d_section)

            ## GET ANGLE FROM MIDDLE OF MATRIX (7,7) TO ENEMY POINT
            mid_point = (MyCommon.Constants.ATTACKING_RADIUS, MyCommon.Constants.ATTACKING_RADIUS)
            angle = MyCommon.get_angle(MyCommon.Coordinates(mid_point[0], mid_point[1]),
                                       MyCommon.Coordinates(enemy_point[0], enemy_point[1]))

            ## ACTUAL COORDINATE OF ENEMY (MINUS SOME TO AVOID COLLIDING)
            target_coord = MyCommon.get_destination_coord(ship_coords, angle, thrust=enemy_distance)

            over_thrust = None
            heapq.heappush(battle_heap, (section_distance, enemy_distance, ship_id, target_coord, over_thrust, strong_enough, enemy_val))
        else:
            ## ENEMY IN A DIFFERENT SECTION

            ## HERE ENEMY_SECTION_POINT IS ONLY IN REFERENCE WITH JUST THE SECTION MATRIX
            ## NEED TO TAKE INTO ACCOUNT THE SHIPS SECTION
            enemy_section_point = (ship_section[0] + (enemy_section_point[0] - MyCommon.Constants.SIZE_SECTIONS_RADIUS),
                                   ship_section[1] + (enemy_section_point[1] - MyCommon.Constants.SIZE_SECTIONS_RADIUS))

            ## GET ACTUAL ENEMY DISTANCE (FROM MIDDLE OF ENEMY SECTION)
            section_coord = MyCommon.get_coord_from_section(enemy_section_point)
            enemy_distance = MyCommon.calculate_distance(ship_coords, section_coord, rounding=False)

            ## NO LONGER REQUIRED SINCE WE GOT ACTUAL COORD OF ENEMY
            # angle = MyCommon.get_angle(MyCommon.Coordinates(MyCommon.Constants.SIZE_SECTIONS_RADIUS, MyCommon.Constants.SIZE_SECTIONS_RADIUS),
            #                            MyCommon.Coordinates(enemy_section_point[0], enemy_section_point[1]))
            # target_coord = MyCommon.get_destination_coord(ship_coords, angle, thrust=over_thrust)

            over_thrust = 10
            target_coord = section_coord  ## SECTION COORD SHOULD BE GOOD ENOUGH (MIDDLE)

            strong_enough = None
            enemy_val = None
            heapq.heappush(battle_heap, (section_distance, enemy_distance, ship_id, target_coord, over_thrust, strong_enough, enemy_val))

    else:
        ## NO ENEMY FOUND AROUND ANY OF OUR SHIPS
        ## THIS SHOULDNT HAPPEN RIGHT? OR ELSE WHY IS IT IN BATTLING
        section_distance = MyCommon.Constants.BIG_DISTANCE
        enemy_distance = 0
        target_coord = None
        over_thrust = None
        strong_enough = None
        enemy_val = None
        heapq.heappush(battle_heap, (section_distance,enemy_distance, ship_id, target_coord, over_thrust, strong_enough, enemy_val))


def check_if_strong_enough(MyMoves, middle_coord):
    """
    CHECK A SECTION, BASED ON COORDS PROVIDED, IF ITS STRONG ENOUGH
    """

    ## GET ACTUAL COORDS/DISTANCE OF THE ENEMY
    value = MyMoves.myMatrix.matrix[MyMoves.myMap.my_id][0]  ## 1 IS FOR HP MATRIX
    # v_enemy = MyCommon.get_section_with_padding(value, ship_coords, MyCommon.Constants.ATTACKING_RADIUS, 0)
    v_enemy = MyCommon.get_section_with_padding(value, middle_coord, MyCommon.Constants.ATTACKING_RADIUS, 0)

    value = MyMoves.myMatrix.ally_matrix
    # v_ally = MyCommon.get_section_with_padding(value, ship_coords, MyCommon.Constants.ATTACKING_RADIUS, 0)
    v_ally = MyCommon.get_section_with_padding(value, middle_coord, MyCommon.Constants.ATTACKING_RADIUS, 0)

    ## INSTEAD OF USING ABOVE, COUNT -1 AND 1 ONLY. SINCE ABOVE INCLUDES ENEMY MINING
    ## ONLY GRAB A SECTION (STRONG ENOUGH RADIUS) OF THE SECTION (ATTACKING RADIUS)
    ## INCLUDE DOCKED SHIPS WHEN CALCULATING ALLY POWER
    ## TO PREVENT ONE SHIP FROM BACKING OUT WHEN PROTECTING DOCKED SHIPS AGAINST 1 ENEMY SHIP
    # num_enemy_in_section = (v_enemy==-1).sum()
    # num_ally_in_section = (v_ally==1).sum()
    num_enemy_in_section = (v_enemy[
                            MyCommon.Constants.ATTACKING_RADIUS - MyCommon.Constants.STRONG_ENOUGH_RADIUS:MyCommon.Constants.ATTACKING_RADIUS + MyCommon.Constants.STRONG_ENOUGH_RADIUS + 1,
                            MyCommon.Constants.ATTACKING_RADIUS - MyCommon.Constants.STRONG_ENOUGH_RADIUS:MyCommon.Constants.ATTACKING_RADIUS + MyCommon.Constants.STRONG_ENOUGH_RADIUS + 1] == -1).sum()  ## JUST GET A 7x7 matrix
    # num_ally_in_section = (v_ally[MyCommon.Constants.ATTACKING_RADIUS-MyCommon.Constants.STRONG_ENOUGH_RADIUS:MyCommon.Constants.ATTACKING_RADIUS+MyCommon.Constants.STRONG_ENOUGH_RADIUS+1,
    #                        MyCommon.Constants.ATTACKING_RADIUS-MyCommon.Constants.STRONG_ENOUGH_RADIUS:MyCommon.Constants.ATTACKING_RADIUS+MyCommon.Constants.STRONG_ENOUGH_RADIUS+1] == 1).sum() \
    #                       + (v_ally[MyCommon.Constants.ATTACKING_RADIUS-MyCommon.Constants.STRONG_ENOUGH_RADIUS:MyCommon.Constants.ATTACKING_RADIUS+MyCommon.Constants.STRONG_ENOUGH_RADIUS+1,
    #                          MyCommon.Constants.ATTACKING_RADIUS-MyCommon.Constants.STRONG_ENOUGH_RADIUS:MyCommon.Constants.ATTACKING_RADIUS+MyCommon.Constants.STRONG_ENOUGH_RADIUS+1] == 0.75).sum()
    ## MATRIX ALLY CONTAINS SHIP ID NOW
    num_ally_in_section = (v_ally[
                           MyCommon.Constants.ATTACKING_RADIUS - MyCommon.Constants.STRONG_ENOUGH_RADIUS:MyCommon.Constants.ATTACKING_RADIUS + MyCommon.Constants.STRONG_ENOUGH_RADIUS + 1,
                           MyCommon.Constants.ATTACKING_RADIUS - MyCommon.Constants.STRONG_ENOUGH_RADIUS:MyCommon.Constants.ATTACKING_RADIUS + MyCommon.Constants.STRONG_ENOUGH_RADIUS + 1] != -1).sum()

    strong_enough = num_ally_in_section > num_enemy_in_section

    return strong_enough, v_enemy


def move_battle_heap(MyMoves, battle_heap):
    """
    MOVE SHIPS ACCORDING TO THE HEAP PROVIDED
    """
    while battle_heap:
        section_distance, enemy_distance, ship_id, target_coord, over_thrust, strong_enough, enemy_val = heapq.heappop(battle_heap)

        if ship_id not in MyMoves.myMap.ships_moved_already:

            ship_coords = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
            ship_point = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['point']
            ship_health = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['health']
            ship_dying = ship_health <= MyCommon.Constants.DYING_HP

            if target_coord: ## HAS TARGET
                if over_thrust is None:
                    ## MOVE THIS SHIP, IN THE SAME SECTION

                    ## IF NOT STRONG ENOUGH, GO BACK 7 UNITS, BUT ALSO KEEP TRACK OF BACKUP MATRIX
                    if strong_enough or ship_dying:
                        ## STRONG ENOUGH, CAN JUST ATTACK TOWARDS ENEMY
                        ## IF DYING, ATTACK TOWARDS ENEMY
                        logging.debug("ship_id: {} from handled_ships in same section (strong enough).  ship_dying: {}".format(ship_id, ship_dying))
                        thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, target_coord, target_distance=enemy_distance, target_planet_id=None)
                        logging.debug("thrust: {} angle: {} enemy_distance: {}".format(thrust, angle, enemy_distance))

                        ## IF TARGET IS REACHABLE, MOVE BACK BY 2 TO PREVENT COLLIDING WITH ENEMY
                        ## COMMENTING THIS OUT GIVES A HIGHER RANKING
                        if int(round(enemy_distance)) - 1 <= thrust:
                            logging.debug("docked enemy_val: {} ".format(enemy_val))
                            if enemy_val == Matrix_val.ENEMY_SHIP_DOCKED.value and not(ship_dying): ## ONLY MOVE BACK IF ENEMY IS DOCKED
                                thrust = max(0, thrust - 2)
                                logging.debug("updated thrust for docked enemy: {} angle: {}".format(thrust, angle))

                        ship_task = MyCommon.ShipTasks.ATTACKING_FRONTLINE
                        set_commands_status(MyMoves, ship_id, thrust, angle, target_coord, ship_task)

                        ## SET COMAND STATUS LATER (MOVE OTHERS FIRST)
                        # ship_task2 = MyCommon.ShipTasks.SUPPORTING
                        # move_ships_towards_this_coord(MyMoves, ship_id, ship_task, ship_task2, target_coord)

                    else:
                        ## NOT STRONG ENOUGH (FLIP ANGLE)
                        logging.debug("ship_id: {} from handled_ships in same section (not strong enough)".format(ship_id))
                        angle = MyCommon.get_angle(ship_coords, target_coord)
                        flip_angle = MyCommon.get_reversed_angle(angle)
                        over_thrust = 10
                        new_target_coord = MyCommon.get_destination_coord(ship_coords,flip_angle,over_thrust,rounding=False)
                        thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, new_target_coord, target_distance=over_thrust, target_planet_id=None)
                        logging.debug("thrust: {} angle: {}".format(thrust, angle))
                        ship_task = MyCommon.ShipTasks.EVADING

                        ## COMMENTING THIS OUT BECAUSE WILL MOVE LATER
                        #set_commands_status(MyMoves, ship_id, thrust, angle, new_target_coord, ship_task)

                        ## ADD TO BACKUP MATRIX
                        #MyMoves.myMatrix.backup_matrix[ship_point[0], ship_point[1]] = 1  ## WAS ON BOT25
                        ## +2 TO MOVE BACK FURTHER FOR BACKUP TO GO THERE

                        try:
                            backup_coord = MyCommon.get_destination_coord(ship_coords, angle, thrust + 2, rounding=True)
                            MyMoves.myMatrix.backup_matrix[backup_coord.y, backup_coord.x] = 1
                        except:
                            ## GOING OVER THE MAP
                            backup_coord = MyCommon.get_destination_coord(ship_coords, angle, thrust, rounding=True)
                            MyMoves.myMatrix.backup_matrix[backup_coord.y, backup_coord.x] = 1

                        ship_task2 = MyCommon.ShipTasks.SUPPORTING
                        move_ships_towards_this_coord(MyMoves, ship_id, ship_task, ship_task2, backup_coord)

                else:
                    ## MOVE THIS SHIP NOW, FROM DIFFERENT SECTION

                    ## LOOK FOR BACKUP FIRST, IF NONE FOUND MOVE TOWARDS TARGET LIKE NORMAL
                    # pad_values = 0
                    # area_matrix = MyCommon.get_circle_in_square(MyMoves.myMatrix.backup_matrix,
                    #                                             ship_coords,
                    #                                             MyCommon.Constants.BACKUP_CIRCLE_RADIUS,
                    #                                             MyCommon.Constants.BACKUP_SQUARE_RADIUS,
                    #                                             pad_values)
                    # seek_val = 1
                    # backup_point, backup_distance, backup_val = MyCommon.get_coord_closest_seek_value(seek_val,
                    #                                                                       area_matrix,
                    #                                                                       MyMoves.EXP.distance_matrix_backup)
                    #
                    # if backup_point:
                    #     ## MOVE TOWARDS BACKUP
                    #     logging.debug("ship_id: {} from handled_ships in different section. Going to back up".format(ship_id))
                    #     slope = (backup_point[0] - MyCommon.Constants.BACKUP_SQUARE_RADIUS, backup_point[1] - MyCommon.Constants.BACKUP_SQUARE_RADIUS)
                    #     new_target_coord = MyCommon.Coordinates(ship_point[0] + slope[0], ship_point[1] + slope[1])
                    #     logging.debug("backup found at coord: {}".format(new_target_coord))
                    #     thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, new_target_coord,
                    #                                                            target_distance=backup_distance,
                    #                                                            target_planet_id=None)
                    #     logging.debug("thrust: {} angle: {}".format(thrust, angle))
                    #     ship_task = MyCommon.ShipTasks.SUPPORTING
                    #     set_commands_status(MyMoves, ship_id, thrust, angle, new_target_coord, ship_task)
                    #
                    # else:
                    #     ## NO BACKUP CLOSE BY, JUST MOVE TOWARDS ENEMY
                    #     logging.debug("ship_id: {} from handled_ships in different section".format(ship_id))
                    #     logging.debug("section_distance: {} enemy_distance {} target_coord {}".format(section_distance, enemy_distance, target_coord, over_thrust))
                    #     thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, target_coord, target_distance=over_thrust, target_planet_id=None)
                    #     logging.debug("thrust: {} angle: {}".format(thrust, angle))
                    #     ship_task = MyCommon.ShipTasks.ATTACKING
                    #     set_commands_status(MyMoves, ship_id, thrust, angle, target_coord, ship_task)


                    ## BACKUP IS MOVED ALREADY AT THIS POINT (USING GET SHIPS IN ARRAY)
                    logging.debug("ship_id: {} from handled_ships in different section".format(ship_id))
                    logging.debug("section_distance: {} enemy_distance {} target_coord {}".format(section_distance, enemy_distance, target_coord, over_thrust))
                    thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, target_coord, target_distance=over_thrust, target_planet_id=None)
                    logging.debug("thrust: {} angle: {}".format(thrust, angle))
                    ship_task = MyCommon.ShipTasks.ATTACKING

                    set_commands_status(MyMoves, ship_id, thrust, angle, target_coord, ship_task)

                    ## DOING THIS GENERATED A LOWER RANK (BOT 52)
                    # if enemy_distance < 14:
                    #     ## PREVENTS COLLIDING TO ENEMY
                    #     thrust = int(max(1, enemy_distance - 8))
                    #     logging.debug("updated thrust to prevent collision: {} angle: {}".format(thrust, angle))
                    #     set_commands_status(MyMoves, ship_id, thrust, angle, target_coord, ship_task)
                    # else:
                    #     set_commands_status(MyMoves, ship_id, thrust, angle, target_coord, ship_task)


            else:
                logging.debug("ship_id: {} from handled_ships no enemy found around it".format(ship_id))
                ## NO ENEMY FOUND AROUND ANY OF OUR SHIPS
                #closest_section_with_enemy(MyMoves, ship_id, move_now=True)
                closest_section_with_enemy(MyMoves, ship_id, move_now=True, docked_only=True)


def move_ships_towards_this_coord(MyMoves, ship_id, ship_task, _ship_task, backup_coord):
    """
    GET BACKUP SHIPS AROUND THIS AREA

    MOVE SHIPS CLOSEST TO THE BACK UP POINT FIRST
    """
    ship_coords = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']

    pad_values = -1
    area_matrix = MyCommon.get_circle_in_square(MyMoves.myMatrix.ally_matrix,
                                                backup_coord,
                                                MyCommon.Constants.BACKUP_CIRCLE_RADIUS,
                                                MyCommon.Constants.BACKUP_SQUARE_RADIUS,
                                                pad_values,
                                                pad_outside_circle=True)

    #logging.debug("area_matrix {}".format(area_matrix))

    ships = MyCommon.get_ship_ids_in_array(area_matrix, MyMoves.EXP.distance_matrix_backup)


    for _ship_id in ships:
        _ship_id = int(_ship_id)
        if _ship_id != ship_id and _ship_id not in MyMoves.myMap.ships_moved_already:
            logging.debug("_ship_id: {}".format(_ship_id))
            ## MOVE SHIP TOWARDS BACKUP COORD
            _ship_coords = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][_ship_id]['coords']
            _d = MyCommon.calculate_distance(_ship_coords, backup_coord)
            _thrust, _angle = expanding2.get_thrust_angle_from_Astar(MyMoves, _ship_id, backup_coord, target_distance=_d, target_planet_id=None)
            set_commands_status(MyMoves, _ship_id, _thrust, _angle, backup_coord, _ship_task)

    ## MOVE ORIGINAL SHIP_ID
    logging.debug("_ship_id (orig): {}".format(ship_id))
    d = MyCommon.calculate_distance(ship_coords, backup_coord)
    thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, backup_coord,target_distance=d, target_planet_id=None)
    set_commands_status(MyMoves, ship_id, thrust, angle, backup_coord, ship_task)


def set_section_in_battle(MyMoves, ship_section, enemy_section_point):
    """
    SET SECTIONS IN WAR
    """
    slope = (enemy_section_point[0] - MyCommon.Constants.SIZE_SECTIONS_RADIUS, enemy_section_point[1] - MyCommon.Constants.SIZE_SECTIONS_RADIUS)
    section = (ship_section[0] + slope[0], ship_section[1] + slope[1])
    MyMoves.myMap.section_in_battle.add(section)

    ## NO NEED TO FIND SLOPE, ALREADY TAKEN INTO ACCOUNT BEFORE CALLING THIS
    # MyMoves.myMap.section_in_battle.add(enemy_section_point)

def closest_section_in_battle(MyMoves, ship_id):
    """
    GET CLOSEST SECTION IN WAR AND GO THERE

    NOT USED RIGHT NOW, SHOULD USE IT TO HELP DEFEND MINING SHIPS
    """
    ship_coords = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
    ship_section = MyCommon.get_section_num(ship_coords)

    min_distance = MyCommon.Constants.BIG_DISTANCE
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

        ship_task = MyCommon.ShipTasks.ATTACKING
        set_commands_status(MyMoves, ship_id, thrust, angle, target_coord, ship_task)
    else:
        ## NO SECTION IN BATTLE
        closest_section_with_enemy(MyMoves, ship_id)


def closest_section_with_enemy(MyMoves, ship_id, docked_only=False, move_now=False):
    """
    GET CLOSEST SECTION WITH ENEMY
    """
    def get_closest_section_enemy(MyMoves, least_distance, closest_section):
        for section in MyMoves.myMap.sections_with_enemy:
            distance = MyMoves.EXP.sections_distance_table[ship_section][section[0]][section[1]]

            if distance < least_distance:
                closest_section = section
                least_distance = distance

        return closest_section

    def get_closest_section_docked(MyMoves, least_distance, closest_section):
        for section in MyMoves.myMap.sections_with_enemy_docked:
            distance = MyMoves.EXP.sections_distance_table[ship_section][section[0]][section[1]]

            if distance < least_distance:
                closest_section = section
                least_distance = distance

        return closest_section

    ship_coords = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
    ship_section = MyCommon.get_section_num(ship_coords)

    least_distance = MyCommon.Constants.BIG_DISTANCE
    closest_section = None

    ## CAN UPDATE THIS LATER TO USE JUST NUMPY (A BIT HARD SINCE DISTANCE TABLE CHANGES BASED ON LOCATION OF SHIP
    ## GET CLOSEST SECTION WITH ENEMY
    if docked_only:
        closest_section = get_closest_section_docked(MyMoves, least_distance, closest_section)

        if closest_section is None:
            ## NO MORE DOCKED ENEMY SHIPS IN THE MAP
            closest_section = get_closest_section_enemy(MyMoves, least_distance, closest_section)
    else:
        closest_section = get_closest_section_enemy(MyMoves, least_distance, closest_section)


    ## BEFORE
    # target_coord = MyCommon.get_coord_from_section(closest_section)
    # final_distance = MyCommon.calculate_distance(ship_coords, target_coord)

    ## HANDLING IF IN THE SAME SECTION
    if closest_section == ship_section:
        ## DISTANCE IS NOT ACCURATE IF 2 SHIPS ARE IN THE SAME SECTION AND TARGET IN SAME SECTION
        value = MyMoves.myMatrix.matrix[MyMoves.myMap.my_id][0]  ## 1 IS FOR HP MATRIX
        v_enemy = MyCommon.get_section_with_padding(value, ship_coords, MyCommon.Constants.ATTACKING_RADIUS, 0)

        seek_val = -0.75
        d_section = MyMoves.EXP.distance_matrix_AxA
        enemy_point, enemy_distance, enemy_val = MyCommon.get_coord_closest_seek_value(seek_val, v_enemy, d_section)

        slope = (enemy_point[0] - MyCommon.Constants.ATTACKING_RADIUS, enemy_point[1] - MyCommon.Constants.ATTACKING_RADIUS)
        target_coord = MyCommon.Coordinates(ship_coords.y + slope[0], ship_coords.x + slope[1])

        final_distance = enemy_distance

    else:
        target_coord = MyCommon.get_coord_from_section(closest_section)

        ## INSTEAD OF DOING FINAL DISTANCE AS SECTION TO SECTION, LETS GET ACTUAL DISTANCE OF SHIP COORD TO THAT SECTION
        # final_distance = (min_distance + 1) * 7
        final_distance = MyCommon.calculate_distance(ship_coords, target_coord)

    logging.debug("closest_section_with_enemy final_distance {} ship_coords {} target_coord {}".format(final_distance, ship_coords, target_coord))

    if move_now:
        thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, target_coord, final_distance, target_planet_id=None)
        ship_task = MyCommon.ShipTasks.ATTACKING
        set_commands_status(MyMoves, ship_id, thrust=thrust, angle=angle, target_coord=target_coord, ship_task=ship_task)
    else:
        return final_distance, target_coord






