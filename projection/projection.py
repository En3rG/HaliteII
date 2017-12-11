
import numpy as np
import logging
from models.model import Matrix_val

class MyProjection():
    def __init__(self, myMap):
        self.myMap = myMap
        if myMap.myMap_prev == None:
            self.turns = {}
        else:
            self.turns = self.get_projection()

    def get_projection(self):
        """
        GET WHERE ENEMY SHIPS ARE PROJECTED TO BE AT (UP TO NEXT 5 TURNS)
        BASED ON SHIPS CURRENT VELOCITY
        """

        ## INITIALIZE EMPTY MATRIX
        turns = {}
        turns[1] = np.zeros((self.myMap.height, self.myMap.width), dtype=np.float)
        turns[2] = np.zeros((self.myMap.height, self.myMap.width), dtype=np.float)
        turns[3] = np.zeros((self.myMap.height, self.myMap.width), dtype=np.float)
        turns[4] = np.zeros((self.myMap.height, self.myMap.width), dtype=np.float)
        turns[5] = np.zeros((self.myMap.height, self.myMap.width), dtype=np.float)

        for player_id, ships in self.myMap.data_ships.items():
            if player_id != self.myMap.my_id:
                for ship_id, ship_data in ships.items():
                    try:
                        current_x = ship_data['x']
                        current_y = ship_data['y']
                        prev_x = self.myMap.myMap_prev.data_ships[player_id][ship_id]['x']
                        prev_y = self.myMap.myMap_prev.data_ships[player_id][ship_id]['y']
                    except:
                        ## SHIP DIDNT EXIST PREVIOUSLY
                        ## GO TO NEXT LOOP
                        continue

                    ## FILL IN MATRIX WITH ENEMY PROJECTION
                    slope = self.get_slope(prev_y,prev_x,current_y,current_x)
                    self.set_turn_projection(1, turns[1], slope, current_y, current_x)
                    self.set_turn_projection(2, turns[2], slope, current_y, current_x)
                    self.set_turn_projection(3, turns[3], slope, current_y, current_x)
                    self.set_turn_projection(4, turns[4], slope, current_y, current_x)
                    self.set_turn_projection(5, turns[5], slope, current_y, current_x)


        return turns

    def get_slope(self,prev_y,prev_x,current_y,current_x):
        return (current_y - prev_y, current_x - prev_x)

    def set_turn_projection(self,multiplier,matrix,slope, current_y, current_x):
        """
        PLACE ENEMY_SHIP VALUE IN MATRIX PROVIDED
        DEPENDS ON MULTIPLIER AND SLOP PROVIDED AS WELL
        """
        new_y = round(current_y + (slope[0] * multiplier))
        new_x = round(current_x + (slope[1] * multiplier))

        matrix[new_y][new_x] = Matrix_val.ENEMY_SHIP.value

    def check_for_enemy(self):
        """
        CHECKS IF ENEMY IS COMING WITHIN THE NEXT 5 TURNS
        WITHIN MY SHIPS PERIMETER
        """
        radius = 10

        for player_id, ships in self.myMap.data_ships.items():
            if player_id == self.myMap.my_id:
                for ship_id, ship_data in ships.items():
                    ## CHECK NEXT 5 TURNS
                    for turn in range(1, 6):
                        if self.turns != {}:
                            current_matrix = self.turns[turn]

                            ## CHECK A CERTAIN SQUARE/PERIMETER IF ENEMY WILL BE THERE IN THAT TURN
                            starting_y = round(ship_data['y']) - radius
                            starting_x = round(ship_data['x']) - radius
                            perimeter = current_matrix[starting_y:round(ship_data['y']) + radius, \
                                                       starting_x:round(ship_data['x']) + radius]

                            if Matrix_val.ENEMY_SHIP.value in perimeter:
                                ## ENEMY DETECTED
                                self.myMap.data_ships[player_id][ship_id]['enemy_in_turn'].append(turn)
                                logging.debug("Enemy detected ship id: {}, turn: {}".format(ship_id, turn))

                                ## GET LOCATION/COORDS OF PROJECTED ENEMY
                                list_coords = np.argwhere(perimeter == Matrix_val.ENEMY_SHIP.value)
                                ## ADD y AND x OFFSET, SINCE PERIMETER IS JUST A SUBSET OF THE MATRIX
                                list_coords[:,0] += starting_y
                                list_coords[:,1] += starting_x

                                self.myMap.data_ships[player_id][ship_id]['enemy_coord'].append(list_coords)
                                logging.debug("Enemy detected in coords: {}".format(list_coords))

#



# import numpy as np
#
# a = np.array([[0., 1., 2., 3., 4.],
#                  [7., 8., 9., 10., 4.],
#                  [14., 15., 16., 17., 4.],
#                  [1., 20., 21., 22., 23.],
#                  [27., 28., 1., 20., 29.]])
#
# b = a[0:4,2:5]
#
# print(b)
#
#
# print(np.argwhere(a == 4.))
# print(np.argwhere(b == 4.))
#
# print(type(np.argwhere(b == 4.)))


