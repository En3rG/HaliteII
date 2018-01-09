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
    battle_heap = []

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
            values = MyMoves.myMap.section_enemy_summary

            logging.debug("ship_id:: {} ship_coords: {} ship_section: {}".format(ship_id,ship_coords,ship_section))

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
            enemy_section_point, section_distance = MyCommon.get_coord_closest_most_enemies_from_section(seek_val, v_sectioned, d_sectioned)


            if enemy_section_point: ## AN ENEMY WAS FOUND
                ## PLACE THIS SECTION TO BATTLING
                set_section_in_battle(MyMoves, ship_section, enemy_section_point)

                if section_distance == 0:
                    ## ENEMY WITHIN THE SAME SECTION
                    ## GET ACTUAL COORDS/DISTANCE OF THE ENEMY
                    value = MyMoves.myMatrix.matrix[MyMoves.myMap.my_id][0]  ## 1 FOR HP MATRIX


                    v_section = MyCommon.get_section_with_padding(value, ship_coords, 7, 0)

                    d_section = MyMoves.EXP.sample_distance_matrix

                    ## FIND ACTUAL COORDINATE OF CLOSEST ENEMY
                    seek_val = -0.75
                    enemy_point, enemy_distance = MyCommon.get_coord_closest_most_enemies_from_section(seek_val, v_section, d_section)
                    ## HERE ENEMY_POINT IS IN REFERENCE TO JUST THE SECTION MATRIX, HERE IT IS OKAY SINCE ANGLE AND DISTANCE IS THE SAME

                    ## GET NUMBER OF ENEMIES IN THIS SECTION
                    # num_enemy_in_section = v_sectioned[enemy_section_point[0], enemy_section_point[1]]
                    # num_ally_in_section = MyMoves.myMap.section_ally_summary[ship_section[0],ship_section[1]]

                    ## INSTEAD OF USING ABOVE, COUNT -1 AND 1 ONLY. SINCE ABOVE INCLUDES ENEMY MINING
                    num_enemy_in_section = (v_section==-1).sum()
                    num_ally_in_section = (v_section==1).sum()


                    strong_enough = num_ally_in_section > num_enemy_in_section


                    angle = MyCommon.get_angle(MyCommon.Coordinates(7, 7), MyCommon.Coordinates(enemy_point[0], enemy_point[1]))

                    ## ACTUAL COORDINATE OF ENEMY
                    target_coord = MyCommon.get_destination_coord(ship_coords, angle, thrust=enemy_distance)



                    heapq.heappush(battle_heap, (section_distance, enemy_distance, ship_id, target_coord, None, strong_enough))
                else:
                    ## ENEMY IN A DIFFERENT SECTION

                    ## HERE ENEMY_SECTION_POINT IS ONLY IN REFERENCE WITH JUST THE SECTION MATRIX
                    ## NEED TO TAKE INTO ACCOUNT THE SHIPS SECTION

                    logging.debug("before updating: enemy_section_point {}".format(enemy_section_point))
                    enemy_section_point = (ship_section[0] + (enemy_section_point[0] - MyCommon.Constants.SIZE_SECTIONS_RADIUS),
                                           ship_section[1] + (enemy_section_point[1] - MyCommon.Constants.SIZE_SECTIONS_RADIUS))
                    logging.debug("after updating: enemy_section_point {}".format(enemy_section_point))


                    ## GET ACTUAL ENEMY DISTANCE
                    section_coord = MyCommon.get_coord_from_section(enemy_section_point)

                    enemy_distance = MyCommon.calculate_distance(ship_coords, section_coord)

                    ## NO LONGER REQUIRED SINCE WE GOT ACTUAL COORD OF ENEMY
                    # angle = MyCommon.get_angle(MyCommon.Coordinates(MyCommon.Constants.SIZE_SECTIONS_RADIUS, MyCommon.Constants.SIZE_SECTIONS_RADIUS),
                    #                            MyCommon.Coordinates(enemy_section_point[0], enemy_section_point[1]))
                    # target_coord = MyCommon.get_destination_coord(ship_coords, angle, thrust=over_thrust)

                    over_thrust = 10

                    target_coord = section_coord  ## SECTION COORD SHOULD BE GOOD ENOUGH

                    logging.debug("enemy_section_point {} section_coord {} target_coord {}".format(enemy_section_point, section_coord, target_coord))

                    strong_enough = None
                    heapq.heappush(battle_heap, (section_distance, enemy_distance, ship_id, target_coord, over_thrust, strong_enough))

            else:
                ## NO ENEMY FOUND AROUND ANY OF OUR SHIPS
                ## THIS SHOULDNT HAPPEN RIGHT? OR ELSE WHY IS IT IN BATTLING
                section_distance = MyCommon.Constants.BIG_DISTANCE
                enemy_distance = 0
                target_coord = None
                over_thrust = None
                strong_enough = None
                heapq.heappush(battle_heap, (section_distance,enemy_distance, ship_id, target_coord, over_thrust, strong_enough))

    ## MOVE SHIPS IN ORDER (TO MINIMIZE COLLISION)
    while battle_heap:
        section_distance, enemy_distance, ship_id, target_coord, over_thrust, strong_enough = heapq.heappop(battle_heap)

        if target_coord: ## HAS TARGET
            if over_thrust is None:
                ## MOVE THIS SHIP, IN THE SAME SECTION

                if strong_enough:
                    logging.debug("ship_id: {} from handled_ships in same section (strong enough)".format(ship_id))
                    thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, target_coord, target_distance=enemy_distance, target_planet_id=None)
                    logging.debug("thrust: {} angle: {}".format(thrust, angle))
                    set_commands_status(MyMoves, ship_id, thrust, angle)
                else:
                    ## NOT STRONG ENOUGH (FLIP ANGLE)
                    logging.debug("ship_id: {} from handled_ships in same section (not strong enough)".format(ship_id))
                    thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, target_coord,target_distance=enemy_distance,target_planet_id=None)
                    thrust = MyCommon.Constants.MOVE_BACK_OFFENSE
                    angle = MyCommon.get_reversed_angle(angle)
                    logging.debug("thrust: {} angle: {}".format(thrust, angle))
                    set_commands_status(MyMoves, ship_id, thrust, angle)

                ## DOESNT CARE EVEN IF NOT STRONG ENOUGH
                # logging.debug("ship_id: {} from handled_ships in same section (strong enough)".format(ship_id))
                # thrust, angle = expanding2.get_thrust_angle_from_Astar(MyMoves, ship_id, target_coord, target_distance=enemy_distance, target_planet_id=None)
                # logging.debug("thrust: {} angle: {}".format(thrust, angle))
                # set_commands_status(MyMoves, ship_id, thrust, angle)

            else:
                ## MOVE THIS SHIP NOW, FROM DIFFERENT SECTION
                logging.debug("ship_id: {} from handled_ships in different section".format(ship_id))
                logging.debug("section_distance: {} enemy_distance {} target_coord {}".format(section_distance, enemy_distance,target_coord , over_thrust))
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

    ## NO NEED TO FIND SLOPE, ALREADY TAKEN INTO ACCOUNT BEFORE CALLING THIS
    # MyMoves.myMap.section_in_battle.add(enemy_section_point)

def closest_section_in_battle(MyMoves, ship_id):
    """
    GET CLOSEST SECTION IN WAR AND GO THERE

    NO LONGER USED?
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

    least_distance = MyCommon.Constants.BIG_DISTANCE
    closest_section = None

    ## GET CLOSEST SECTION WITH ENEMY
    for section in MyMoves.myMap.section_with_enemy:
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
        set_commands_status(MyMoves, ship_id, thrust=thrust, angle=angle)
    else:
        return final_distance, target_coord
