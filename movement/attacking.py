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
    distances = MyMoves.EXP.sections_distance_table[ship_section]
    values = MyMoves.myMap.section_enemy_summary

    ## CHECK IF ENEMIES WITHIN A PERIMETER
    enemy_matrix = MyMoves.myMatrix.matrix[MyMoves.myMap.my_id][0]  ## 1 FOR HP MATRIX
    perimeter = MyCommon.get_section_with_padding(enemy_matrix, ship_coords, MyCommon.Constants.PERIMETER_CHECK_RADIUS, pad_values=0)

    if Matrix_val.ENEMY_SHIP.value not in perimeter and Matrix_val.ENEMY_SHIP_DOCKED.value not in perimeter:
        ## NO ENEMY FOUND, SKIP
        logging.debug("ship_id: {} did not find any enemy".format(ship_id))
        return

    logging.debug("ship_id:: {} ship_coords: {} ship_section: {}".format(ship_id,ship_coords,ship_section))

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
            ## GET ACTUAL COORDS/DISTANCE OF THE ENEMY
            value = MyMoves.myMatrix.matrix[MyMoves.myMap.my_id][0]  ## 1 IS FOR HP MATRIX
            v_enemy = MyCommon.get_section_with_padding(value, ship_coords, MyCommon.Constants.ATTACKING_RADIUS, 0)

            value = MyMoves.myMatrix.ally_matrix
            v_ally = MyCommon.get_section_with_padding(value, ship_coords, MyCommon.Constants.ATTACKING_RADIUS, 0)

            d_section = MyMoves.EXP.distance_matrix_RxR

            ## FIND ACTUAL COORDINATE OF CLOSEST ENEMY
            seek_val = -0.75
            enemy_point, enemy_distance, enemy_val = MyCommon.get_coord_closest_seek_value(seek_val, v_enemy, d_section)
            ## HERE ENEMY_POINT IS IN REFERENCE TO JUST THE SECTION MATRIX, HERE IT IS OKAY SINCE ANGLE AND DISTANCE IS THE SAME


            #logging.debug("v_enemy {}".format(v_enemy))

            ## GET NUMBER OF ENEMIES IN THIS SECTION
            # num_enemy_in_section = v_sectioned[enemy_section_point[0], enemy_section_point[1]]
            # num_ally_in_section = MyMoves.myMap.section_ally_summary[ship_section[0],ship_section[1]]

            ## GET ANGLE FROM MIDDLE OF MATRIX (7,7) TO ENEMY POINT
            mid_point = (MyCommon.Constants.ATTACKING_RADIUS, MyCommon.Constants.ATTACKING_RADIUS)
            angle = MyCommon.get_angle(MyCommon.Coordinates(mid_point[0], mid_point[1]),
                                       MyCommon.Coordinates(enemy_point[0], enemy_point[1]))

            ## INSTEAD OF USING ABOVE, COUNT -1 AND 1 ONLY. SINCE ABOVE INCLUDES ENEMY MINING
            ## ONLY GRAB A SECTION (STRONG ENOUGH RADIUS) OF THE SECTION (ATTACKING RADIUS)
            ## INCLUDE DOCKED SHIPS WHEN CALCULATING ALLY POWER
            ## TO PREVENT ONE SHIP FROM BACKING OUT WHEN PROTECTING DOCKED SHIPS AGAINST 1 ENEMY SHIP
            # num_enemy_in_section = (v_enemy==-1).sum()
            # num_ally_in_section = (v_ally==1).sum()
            num_enemy_in_section = (v_enemy[MyCommon.Constants.ATTACKING_RADIUS - MyCommon.Constants.STRONG_ENOUGH_RADIUS:MyCommon.Constants.ATTACKING_RADIUS+MyCommon.Constants.STRONG_ENOUGH_RADIUS+1,
                                    MyCommon.Constants.ATTACKING_RADIUS-MyCommon.Constants.STRONG_ENOUGH_RADIUS:MyCommon.Constants.ATTACKING_RADIUS+MyCommon.Constants.STRONG_ENOUGH_RADIUS+1] == -1).sum()  ## JUST GET A 7x7 matrix
            num_ally_in_section = (v_ally[MyCommon.Constants.ATTACKING_RADIUS-MyCommon.Constants.STRONG_ENOUGH_RADIUS:MyCommon.Constants.ATTACKING_RADIUS+MyCommon.Constants.STRONG_ENOUGH_RADIUS+1,
                                   MyCommon.Constants.ATTACKING_RADIUS-MyCommon.Constants.STRONG_ENOUGH_RADIUS:MyCommon.Constants.ATTACKING_RADIUS+MyCommon.Constants.STRONG_ENOUGH_RADIUS+1] == 1).sum() \
                                  + (v_ally[MyCommon.Constants.ATTACKING_RADIUS-MyCommon.Constants.STRONG_ENOUGH_RADIUS:MyCommon.Constants.ATTACKING_RADIUS+MyCommon.Constants.STRONG_ENOUGH_RADIUS+1,
                                     MyCommon.Constants.ATTACKING_RADIUS-MyCommon.Constants.STRONG_ENOUGH_RADIUS:MyCommon.Constants.ATTACKING_RADIUS+MyCommon.Constants.STRONG_ENOUGH_RADIUS+1] == 0.75).sum()

            strong_enough = num_ally_in_section > num_enemy_in_section

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



def move_battle_heap(MyMoves, battle_heap):
    """
    MOVE SHIPS ACCORDING TO THE HEAP PROVIDED
    """
    while battle_heap:
        section_distance, enemy_distance, ship_id, target_coord, over_thrust, strong_enough, enemy_val = heapq.heappop(battle_heap)

        if ship_id not in MyMoves.myMap.ships_moved_already:

            ship_coords = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
            ship_point = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['point']

            if target_coord: ## HAS TARGET
                if over_thrust is None:
                    ## MOVE THIS SHIP, IN THE SAME SECTION

                    ## DOESNT CARE EVEN IF NOT STRONG ENOUGH
                    # logging.debug("ship_id: {} from handled_ships in same section (strong enough)".format(ship_id))
                    # thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, target_coord, target_distance=enemy_distance, target_planet_id=None)
                    # logging.debug("thrust: {} angle: {}".format(thrust, angle))
                    # set_commands_status(MyMoves, ship_id, thrust, angle)

                    ## IF NOT STRONG ENOUGH, JUST BACK UP SOME DISTANCE
                    # if strong_enough:
                    #     ## STRONG ENOUGH, CAN JUST ATTACK TOWARDS ENEMY
                    #     logging.debug("ship_id: {} from handled_ships in same section (strong enough)".format(ship_id))
                    #     thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, target_coord, target_distance=enemy_distance, target_planet_id=None)
                    #     logging.debug("thrust: {} angle: {}".format(thrust, angle))
                    #     set_commands_status(MyMoves, ship_id, thrust, angle)
                    # else:
                    #     ## NOT STRONG ENOUGH (FLIP ANGLE)
                    #     logging.debug("ship_id: {} from handled_ships in same section (not strong enough)".format(ship_id))
                    #     thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, target_coord,target_distance=enemy_distance,target_planet_id=None)
                    #     thrust = MyCommon.Constants.MOVE_BACK_OFFENSE
                    #     angle = MyCommon.get_reversed_angle(angle)
                    #     logging.debug("thrust: {} angle: {}".format(thrust, angle))
                    #     set_commands_status(MyMoves, ship_id, thrust, angle)


                    ## IF NOT STRONG ENOUGH, GO BACK 7 UNITS, BUT ALSO KEEP TRACK OF BACKUP MATRIX
                    if strong_enough:
                        ## STRONG ENOUGH, CAN JUST ATTACK TOWARDS ENEMY
                        logging.debug("ship_id: {} from handled_ships in same section (strong enough)".format(ship_id))
                        thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, target_coord, target_distance=enemy_distance, target_planet_id=None)
                        logging.debug("thrust: {} angle: {} enemy_distance: {}".format(thrust, angle, enemy_distance))

                        ## IF TARGET IS REACHABLE, MOVE BACK BY 2 TO PREVENT COLLIDING WITH ENEMY
                        ## COMMENTING THIS OUT GIVES A HIGHER RANKING
                        # if int(round(enemy_distance)) == thrust:
                        #     logging.debug("enemy_val: {} ".format(enemy_val))
                        #     if enemy_val == Matrix_val.ENEMY_SHIP_DOCKED.value: ## ONLY MOVE BACK IF ENEMY IS DOCKED
                        #         thrust = max(0, thrust - 1)
                        #         logging.debug("updated thrust: {} angle: {}".format(thrust, angle))

                        ship_task = MyCommon.ShipTasks.ATTACKING_FRONTLINE
                        set_commands_status(MyMoves, ship_id, thrust, angle, target_coord, ship_task)


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
                        set_commands_status(MyMoves, ship_id, thrust, angle, new_target_coord, ship_task)

                        ## ADD TO BACKUP MATRIX
                        #MyMoves.myMatrix.backup_matrix[ship_point[0], ship_point[1]] = 1  ## WAS ON BOT25
                        ## +2 TO MOVE BACK FURTHER FOR BACKUP TO GO THERE
                        backup_coord = MyCommon.get_destination_coord(ship_coords, angle, thrust+2, rounding=True)
                        try: MyMoves.myMatrix.backup_matrix[backup_coord.y, backup_coord.x] = 1
                        except: MyMoves.myMatrix.backup_matrix[backup_coord.y-2, backup_coord.x-2] = 1  ## GOING OVER THE MAP

                else:
                    ## MOVE THIS SHIP NOW, FROM DIFFERENT SECTION

                    ## LOOK FOR BACKUP FIRST, IF NONE FOUND MOVE TOWARDS TARGET LIKE NORMAL
                    pad_values = 0
                    area_matrix = MyCommon.get_circle_in_square(MyMoves.myMatrix.backup_matrix,
                                                                ship_coords,
                                                                MyCommon.Constants.BACKUP_CIRCLE_RADIUS,
                                                                MyCommon.Constants.BACKUP_SQUARE_RADIUS,
                                                                pad_values)
                    seek_val = 1
                    backup_point, backup_distance, backup_val = MyCommon.get_coord_closest_seek_value(seek_val,
                                                                                          area_matrix,
                                                                                          MyMoves.EXP.distance_matrix_backup)

                    if backup_point:
                        ## MOVE TOWARDS BACKUP
                        logging.debug("ship_id: {} from handled_ships in different section. Going to back up".format(ship_id))
                        slope = (backup_point[0] - MyCommon.Constants.BACKUP_SQUARE_RADIUS, backup_point[1] - MyCommon.Constants.BACKUP_SQUARE_RADIUS)
                        new_target_coord = MyCommon.Coordinates(ship_point[0] + slope[0], ship_point[1] + slope[1])
                        logging.debug("backup found at coord: {}".format(new_target_coord))
                        thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, new_target_coord,
                                                                               target_distance=backup_distance,
                                                                               target_planet_id=None)
                        logging.debug("thrust: {} angle: {}".format(thrust, angle))
                        ship_task = MyCommon.ShipTasks.SUPPORTING
                        set_commands_status(MyMoves, ship_id, thrust, angle, new_target_coord, ship_task)

                    else:
                        ## NO BACKUP CLOSE BY, JUST MOVE TOWARDS ENEMY
                        logging.debug("ship_id: {} from handled_ships in different section".format(ship_id))
                        logging.debug("section_distance: {} enemy_distance {} target_coord {}".format(section_distance, enemy_distance, target_coord, over_thrust))
                        thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, target_coord, target_distance=over_thrust, target_planet_id=None)
                        logging.debug("thrust: {} angle: {}".format(thrust, angle))
                        ship_task = MyCommon.ShipTasks.ATTACKING
                        set_commands_status(MyMoves, ship_id, thrust, angle, target_coord, ship_task)

                    ## BACKUP IS MOVED ALREADY AT THIS POINT
                    # logging.debug("ship_id: {} from handled_ships in different section".format(ship_id))
                    # logging.debug("section_distance: {} enemy_distance {} target_coord {}".format(section_distance, enemy_distance, target_coord, over_thrust))
                    # thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, target_coord, target_distance=over_thrust, target_planet_id=None)
                    # logging.debug("thrust: {} angle: {}".format(thrust, angle))
                    # ship_task = MyCommon.ShipTasks.ATTACKING
                    # set_commands_status(MyMoves, ship_id, thrust, angle, target_coord, ship_task)


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


def closest_section_with_enemy(MyMoves, ship_id, move_now=False):
    """
    GET CLOSEST SECTION WITH ENEMY
    """
    ship_coords = MyMoves.myMap.data_ships[MyMoves.myMap.my_id][ship_id]['coords']
    ship_section = MyCommon.get_section_num(ship_coords)

    least_distance = MyCommon.Constants.BIG_DISTANCE
    closest_section = None

    ## GET CLOSEST SECTION WITH ENEMY
    for section in MyMoves.myMap.sections_with_enemy:
        distance = MyMoves.EXP.sections_distance_table[ship_section][section[0]][section[1]]

        if distance < least_distance:
            closest_section = section
            least_distance = distance

    target_coord = MyCommon.get_coord_from_section(closest_section)

    ## INSTEAD OF DOING FINAL DISTANCE AS SECTION TO SECTION, LETS GET ACTUAL DISTANCE OF SHIP COORD TO THAT SECTION
    # final_distance = (min_distance + 1) * 7
    final_distance = MyCommon.calculate_distance(ship_coords, target_coord)

    if move_now:
        thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, target_coord, final_distance, target_planet_id=None)
        ship_task = MyCommon.ShipTasks.ATTACKING
        set_commands_status(MyMoves, ship_id, thrust=thrust, angle=angle, target_coord=target_coord, ship_task=ship_task)
    else:
        return final_distance, target_coord



