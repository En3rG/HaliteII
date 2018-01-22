

import numpy as np
import logging
import time
import copy
import tensorflow as tf
import pickle
from threading import Thread
import types
import tempfile
import keras.models
import keras
from enum import Enum
import math
import datetime
from keras.optimizers import SGD
from initialization.explore import Exploration
from models.data import Matrix_val
import MyCommon

graph = tf.get_default_graph()      ## FROM ONLINE FOR MULTITHREADING


def make_keras_picklable():
    """
    THIS FUNCTION IS REQUIRED TO PICKLE KERAS MODEL

    TEMP FILE IS PLACED AT: 'Users\Gio\AppData\Local\Temp'

    NO LONGER USED.
    """
    def __getstate__(self):
        model_str = ""
        with tempfile.NamedTemporaryFile(suffix='.hdf5', delete=False) as fd:
            keras.models.save_model(self, fd.name, overwrite=True)
            model_str = fd.read()
        d = { 'model_str': model_str }
        return d

    def __setstate__(self, state):
        with tempfile.NamedTemporaryFile(suffix='.hdf5', delete=False) as fd:
            fd.write(state['model_str'])
            fd.flush()
            model = keras.models.load_model(fd.name)
        self.__dict__ = model.__dict__


    cls = keras.models.Model
    cls.__getstate__ = __getstate__
    cls.__setstate__ = __setstate__


class NeuralNet():
    def __init__(self,y,x,z):
        """
        42x42 MATRIX AT 300 SAMPLES CAUSES A TIME OUT IN HLT ENGINE

        28x28 TIMES OUT WITH 4 PLAYERS
        """
        self.y = y ## 42, 28
        self.x = x ## 42, 28
        self.z = z ## 4   ## UNITS, HP, PREVIOUS LOCATION, DOCKING STATUS (CAN BE TAKEN INTO ACCOUNT IN UNITS)
        self.num_classes = 225 ## 15x15
        self.model = self.neural_network_model(self.y,self.x,self.z,self.num_classes)

    # def train_model(self, x_train, y_train):
    #     self.model.fit(x_train, y_train, batch_size=self.batch, epochs=self.epoch,verbose=0)  # pickle_safe = True ## ONLY FOR FIT_GENERATOR?
    #
    #     return self.model

    def neural_network_model(self,y,x,z,num_classes):
        from keras.models import Sequential
        from keras.layers import Dense, Dropout, Flatten
        from keras.layers import Conv2D, MaxPooling2D
        from keras.models import model_from_json
        from keras.utils import np_utils
        from keras import optimizers
        from keras import regularizers
        from keras.optimizers import SGD
        import keras

        model = None
        with graph.as_default():  ## ADDED FROM ONLINE FOR MULTITHREADING


            ## SIMPLEST VERSION (decent, better one to get (0,0) prediction
            model = Sequential()
            model.add(Dense(100, input_shape=(y, x, z), activation='tanh', kernel_regularizer=regularizers.l2(0.01)))
            model.add(Flatten())
            model.add(Dense(50, activation='tanh'))
            model.add(Dense(num_classes, activation='softmax'))

            opt = NeuralNet.get_optimizer()
            model.compile(loss='categorical_crossentropy', optimizer=opt)

        return model

    @staticmethod
    def get_optimizer():
        ## SGD
        ## decay IS LEARNING RATE DECAY OVER EACH UPDATE
        ## ORIGINALLY AT lr=0.01, decay=1e-6
        ## CHANGED TO lr=0.7
        ## CHANGED TO lr=0.9
        ## CHANGED TO lr=0.0033
        ## CHANGED TO lr=0.005
        #return SGD(lr=0.01, decay=1e-6, momentum=0.9, nesterov=True)

        ## RMSprop
        #return keras.optimizers.RMSprop(lr=0.001, rho=0.9, epsilon=1e-08, decay=0.0)

        ## Adagrad
        #return keras.optimizers.Adagrad(lr=0.01, epsilon=1e-08, decay=0.0)

        ## Adadelta
        #return keras.optimizers.Adadelta(lr=1.0, rho=0.95, epsilon=1e-08, decay=0.0)

        ## Adam
        #return keras.optimizers.Adam(lr=0.001, beta_1=0.9, beta_2=0.999, epsilon=1e-08, decay=0.0)

        ## Adamax
        return keras.optimizers.Adamax(lr=0.002, beta_1=0.9, beta_2=0.999, epsilon=1e-08, decay=0.0)

        ## Nadam
        #return keras.optimizers.Nadam(lr=0.002, beta_1=0.9, beta_2=0.999, epsilon=1e-08, schedule_decay=0.004)


    @staticmethod
    def get_training_data(player_id, myMap, myMatrix):
        """
        GATHER TRAINING DATA FOR INPUT TO MODEL
        x_train AND y_train
        """
        ## DEFAULT VALUES IF NO DATA FOR TRAINING
        x_train_data = []
        y_train_data = []
        x_train = None
        y_train = None

        if myMap.myMap_prev is not None and myMap.myMap_prev.myMap_prev is not None:
            ## GO THROUGH PREVIOUS SHIPS OF CURRENT PLAYER
            for ship_id, ship_data in myMap.myMap_prev.data_ships[player_id].items():
                ## ship_data HAS x, y, health, dock_status

                ## PREVIOUS SHIP POSITION
                prev_x = round(ship_data['x'])
                prev_y = round(ship_data['y'])

                ## MATRICES BASED ON PREVIOUS MATRIX
                matrix, matrix_hp = myMatrix.matrix_prev.matrix[player_id]

                ## GET MATRIX, WITH SHIP IN THE MIDDLE
                ## +1 TO INCLUDE VALUE AT half_y
                half_y = math.floor(myMatrix.input_matrix_y / 2)
                half_x = math.floor(myMatrix.input_matrix_x / 2)

                ## HERE CURRENT MATRIX IS REALLY PREVIOUS MATRIX
                matrix_current = matrix[prev_y - half_y:prev_y + half_y + 1, \
                                        prev_x - half_x:prev_x + half_x + 1]

                ## CHECK IF ENEMY WAS FOUND IN SIGHT
                if Matrix_val.ENEMY_SHIP.value in matrix_current:
                ##-->


                    ## GET MATRIX HP
                    ## +1 TO INCLUDE VALUE AT half_y
                    matrix_hp_current = matrix_hp[prev_y - half_y:prev_y + half_y + 1, \
                                                  prev_x - half_x:prev_x + half_x + 1]


                    ## CHECK IF SHIP EXIST BEFORE
                    ## PREVIOUS PREVIOUS LOCATION
                    ship_prev = myMap.myMap_prev.myMap_prev.data_ships[player_id].get(ship_id)


                    matrix_prev_loc = np.zeros((myMatrix.input_matrix_y, myMatrix.input_matrix_x), dtype=np.int8)
                    if ship_prev:  ## WILL BE NONE IF SHIP DIDNT EXIST PREVIOUSLY

                        ## GET PREVIOUS LOCATION OF THIS SHIP
                        prev_prev_y = round(ship_prev.get('y'))
                        prev_prev_x = round(ship_prev.get('x'))

                        row = half_y + (prev_prev_y - prev_y)
                        col = half_x + (prev_prev_x - prev_x)

                        ## PLACE A 1 TO REPRESENT PREVIOUS LOCATION
                        matrix_prev_loc[row][col] = Matrix_val.ALLY_SHIP.value

                    ## NEED TO GET y_train FOR THIS SHIP
                    y_train_current = np.zeros((15, 15), dtype=np.int8)

                    now_ship = myMap.data_ships[player_id].get(ship_id)

                    if now_ship: ## IF NONE, SHIP DIED
                        ## CURRENT SHIP POSITION
                        now_x = round(now_ship['x'])
                        now_y = round(now_ship['y'])

                        row = 7 + (now_y - prev_y)
                        col = 7 + (now_x - prev_x)


                        logging.debug("Training data with player id: {} ship id: {}".format(player_id,ship_id))
                        try: logging.debug("Prev Prev position x: {} y: {}".format(prev_prev_x, prev_prev_y))
                        except: pass
                        logging.debug("Prev position x: {} y: {}".format(prev_x, prev_y))
                        logging.debug("Current position x: {} y: {}".format(now_x, now_y))
                        logging.debug("Place prev matrix at pos x: {} y: {}".format(col, row))


                        y_train_current[row][col] = Matrix_val.ALLY_SHIP.value



                    ## ADD JUST THE SHIP IN A MATRIX (ONLY NECESSARY FOR 4 INPUT MATRIX)
                    matrix_ship_loc = np.zeros((myMatrix.input_matrix_y, myMatrix.input_matrix_x), dtype=np.int8)
                    matrix_ship_loc[7][7] = matrix_current[7][7]

                    ## GET 3D ARRAY FOR TRAINING
                    x_train_data_current = NeuralNet.get_3D([matrix_ship_loc, matrix_prev_loc, matrix_current, matrix_hp_current])  ## 4 INPUT
                    #x_train_data_current = NeuralNet.get_3D([matrix_hp_current,matrix_prev_loc, matrix_current])  ## ONLY 3 INPUT
                    x_train_data.append(x_train_data_current)


                    # ## ADD ROTATED VERSIONS OF THE ARRAY, TO INCREASE TRAINING DATA
                    ## ROTATE 90 COUNTER CLOCKWISE
                    matrix_current_1 = np.rot90(matrix_current)
                    matrix_hp_current_1 = np.rot90(matrix_hp_current)
                    matrix_prev_loc_1 = np.rot90(matrix_prev_loc)


                    ## ROTATE 180 COUNTER CLOCKWISE
                    matrix_current_2 = np.rot90(matrix_current, 2)
                    matrix_hp_current_2 = np.rot90(matrix_hp_current, 2)
                    matrix_prev_loc_2 = np.rot90(matrix_prev_loc, 2)

                    ## ROTATE 90 CLOCKWISE
                    matrix_current_3 = np.flipud(matrix_current)
                    matrix_hp_current_3 = np.flipud(matrix_hp_current)
                    matrix_prev_loc_3 = np.flipud(matrix_prev_loc)


                    ## GET 3D ARRAY FOR TRAINING FOR ROTATED MATRIXES
                    x_train_data_current = NeuralNet.get_3D([matrix_ship_loc, matrix_prev_loc_1, matrix_current_1, matrix_hp_current_1])
                    #x_train_data_current = NeuralNet.get_3D([matrix_hp_current_1,matrix_prev_loc_1, matrix_current_1])
                    x_train_data.append(x_train_data_current)

                    x_train_data_current = NeuralNet.get_3D([matrix_ship_loc, matrix_prev_loc_2, matrix_current_2, matrix_hp_current_2])
                    #x_train_data_current = NeuralNet.get_3D([matrix_hp_current_2,matrix_prev_loc_2, matrix_current_2])
                    x_train_data.append(x_train_data_current)

                    x_train_data_current = NeuralNet.get_3D([matrix_ship_loc, matrix_prev_loc_3, matrix_current_3, matrix_hp_current_3])
                    #x_train_data_current = NeuralNet.get_3D([matrix_hp_current_3,matrix_prev_loc_3, matrix_current_3])
                    x_train_data.append(x_train_data_current)


                    ## FLATTEN FOR Y_TRAIN
                    y_train_current_ = np.ndarray.flatten(y_train_current)
                    y_train_data.append(y_train_current_)

                    ## ADD ROTATED VERSIONS OF THE ARRAY, TO INCREASE TRAINING DATA
                    ## ROTATE 90 COUNTER CLOCKWISE
                    y_train_current_1 = np.rot90(y_train_current)
                    y_train_current_1_ = np.ndarray.flatten(y_train_current_1)
                    y_train_data.append(y_train_current_1_)

                    ## ROTATE 180 COUNTER CLOCKWISE
                    y_train_current_2 = np.rot90(y_train_current, 2)
                    y_train_current_2_ = np.ndarray.flatten(y_train_current_2)
                    y_train_data.append(y_train_current_2_)

                    ## ROTATE 90 CLOCKWISE
                    y_train_current_3 = np.flipud(y_train_current)
                    y_train_current_3_ = np.ndarray.flatten(y_train_current_3)
                    y_train_data.append(y_train_current_3_)


                ##<-- ## UNTAB IF TRAINING WITH EVERY TURN, NOT JUST WHEN ENEMY IN SIGHT

            ## GET 4D ARRAY FOR TRAINING
            x_train = NeuralNet.get_4D(x_train_data)
            y_train = NeuralNet.get_2D(y_train_data)


        return x_train, y_train

    @staticmethod
    def get_predicting_data(player_id, myMap, myMatrix):
        """
        GET SHIPS THAT HAVE ENEMY ON SIGHT
        PREP DATA FOR INPUT TO MODEL
        """
        ship_ids = []
        test_data = []

        ## GO THROUGH SHIPS OF CURRENT PLAYER
        for ship_id, ship_data in myMap.data_ships[player_id].items():
            ## ship_data HAS x, y, health, dock_status

            ## CURRENT SHIP POSITION
            now_x = round(ship_data['x'])
            now_y = round(ship_data['y'])

            matrix, matrix_hp = myMatrix.matrix[player_id]

            ## GET MATRIX, WITH SHIP IN THE MIDDLE
            ## +1 TO INCLUDE VALUE AT half_y
            half_y = math.floor(myMatrix.input_matrix_y / 2)
            half_x = math.floor(myMatrix.input_matrix_x / 2)
            matrix_current = matrix[now_y - half_y:now_y + half_y + 1,\
                                    now_x - half_x:now_x + half_x + 1]

            ## CHECK IF ENEMY IS FOUND IN SIGHT
            if Matrix_val.ENEMY_SHIP.value in matrix_current:

                ## ADD THIS SHIP ID
                ship_ids.append(ship_id)

                ## GET MATRIX HP
                ## +1 TO INCLUDE VALUE AT half_y
                matrix_hp_current = matrix_hp[now_y - half_y:now_y + half_y + 1, \
                                              now_x - half_x:now_x + half_x + 1]

                ## CHECK IF SHIP EXIST BEFORE
                ship_prev = myMap.myMap_prev.data_ships[player_id].get(ship_id)

                matrix_prev_loc = np.zeros((myMatrix.input_matrix_y, myMatrix.input_matrix_x), dtype=np.int8)
                if ship_prev:  ## WILL BE NONE IF SHIP DIDNT EXIST PREVIOUSLY
                    ## GET PREVIOUS LOCATION OF THIS SHIP
                    prev_y = round(ship_prev.get('y'))
                    prev_x = round(ship_prev.get('x'))

                    row = half_y + (prev_y - now_y)
                    col = half_x + (prev_x - now_x)

                    ## PLACE A 1 TO REPRESENT PREVIOUS LOCATION
                    matrix_prev_loc[row][col] = Matrix_val.ALLY_SHIP.value

                ## ADD JUST THE SHIP IN A MATRIX (ONLY NECESSARY FOR 4 INPUT MATRIX)
                matrix_ship_loc = np.zeros((myMatrix.input_matrix_y, myMatrix.input_matrix_x), dtype=np.int8)
                matrix_ship_loc[7][7] = matrix_current[7][7]

                ## GET 3D ARRAY FOR PREDICTING
                test_data_current = NeuralNet.get_3D([matrix_ship_loc,matrix_prev_loc,matrix_current,matrix_hp_current])  ## 4 INPUT
                #test_data_current = NeuralNet.get_3D([matrix_hp_current,matrix_prev_loc, matrix_current]) ## ONLY 3 INPUT
                test_data.append(test_data_current)


        ## GET 4D ARRAY FOR PREDICTING
        x_test = NeuralNet.get_4D(test_data)

        return x_test, ship_ids

    @staticmethod
    def get_2D(array_1d):
        """
        TAKES A LIST OF 1D ARRAY WITH LEN X
        RETURNS YxX ARRAY
        """
        if array_1d == []:
            return None
        else:
            return np.vstack(array_1d)

    @staticmethod
    def get_3D(array_2d):
        """
        TAKES A LIST OF 2D ARRAY WITH YxX
        RETURNS YxXxZ ARRAY
        """
        return np.dstack(array_2d)

    @staticmethod
    def get_4D(array_3d):
        """
        TAKES A LIST OF 3D ARRAY WITH YxXxZ
        RETURNS DxYxXxZ ARRAY
        """
        if array_3d == []:
            return None
        else:
            return np.stack(array_3d)

    @staticmethod
    def translate_predictions(predictions):
        predicted_coords = {}
        if predictions:
            for player_id, dict in predictions.items():

                ## LOOPING WILL BE VERY SLOW, USE MAP!!!!!!!!!!!!!!!!!!!!!!!!!!!

                predicted_coords[player_id] = {}

                ship_ids, data = dict

                for id, pred in zip(ship_ids,data):

                    argmax = np.argmax(pred) ## GET INDEX WITH HIGHEST PROBABILITY
                    new_location = Predicted.get_new_location(argmax) ## RETURN COORDINATE GIVEN THE ARGMAX

                    ## SET NEW COORD INTO THE DICTIONARY
                    if new_location == (-10,-10):
                        predicted_coords[player_id][id] = MyCommon.Coordinates(0,0)
                    else:
                        predicted_coords[player_id][id] = MyCommon.Coordinates(new_location[0],new_location[1])

                    logging.debug("Predicted ship id: {} new location: {} percentage: {}".format(id, new_location, max(pred)))

        else:
            logging.debug("Translate predictions is None")

        return predicted_coords


class Predicted():

    """
    0	    1	    2	    3	    4	    5	    6	    7	    8	    9	    10	    11	    12	    13	    14
    (0,0)	(0,0)	(0,0)	(0,0)	(0,0)	(0,0)	(0,0)	(0,7)	(0,0)	(0,0)	(0,0)	(0,0)	(0,0)	(0,0)	(0,0)

    15	    16	    17	    18	    19	    20	    21	    22	    23	    24	    25	    26	    27	    28	    29
    (0,0)	(0,0)	(0,0)	(0,0)	(1,4)	(1,5)	(1,6)	(1,7)	(1,8)	(1,9)	(1,10)	(0,0)	(0,0)	(0,0)	(0,0)

    30	    31	    32	    33	    34	    35	    36	    37	    38	    39	    40	    41	    42	    43	    44
    (0,0)	(0,0)	(0,0)	(2,3)	(2,4)	(2,5)	(2,6)	(2,7)	(2,8)	(2,9)	(2,10)	(2,11)	(0,0)	(0,0)	(0,0)

    45	    46	    47	    48	    49	    50	    51	    52	    53	    54	    55	    56	    57	    58	    59
    (0,0)	(0,0)	(3,2)	(3,3)	(3,4)	(3,5)	(3,6)	(3,7)	(3,8)	(3,9)	(3,10)	(3,11)	(3,12)	(0,0)	(0,0)

    60	    61	    62	    63	    64	    65	    66	    67	    68	    69	    70	    71	    72	    73	    74
    (0,0)	(4,1)	(4,2)	(4,3)	(4,4)	(4,5)	(4,6)	(4,7)	(4,8)	(4,9)	(4,10)	(4,11)	(4,12)	(4,13)	(0,0)

    75	    76	    77	    78	    79	    80	    81	    82	    83	    84	    85	    86	    87	    88	    89
    (0,0)	(5,1)	(5,2)	(5,3)	(5,4)	(5,5)	(5,6)	(5,7)	(5,7)	(5,8)	(5,9)	(5,10)	(5,11)	(5,12)	(0,0)

    90	    91	    92	    93	    94	    95	    96	    97	    98	    99	    100	    101	    102	    103	    104
    (0,0)	(6,1)	(6,2)	(6,3)	(6,4)	(6,5)	(6,6)	(6,7)	(6,7)	(6,8)	(6,9)	(6,10)	(6,11)	(6,12)	(0,0)

    105	    106	    107	    108	    109	    110	    111	    112	    113	    114	    115	    116	    117	    118	    119
    (7,0)	(7,0)	(7,2)	(7,3)	(7,4)	(7,5)	(7,6)	(7,7)	(7,8)	(7,9)	(7,10)	(7,11)	(7,12)	(7,13)	(7,14)

    120	    121	    122	    123	    124	    125	    126	    127	    128	    129	    130	    131	    132	    133	    134
    (0,0)	(8,0)	(8,2)	(8,3)	(8,4)	(8,5)	(8,6)	(8,7)	(8,8)	(8,9)	(8,10)	(8,11)	(8,12)	(8,13)	(0,0)

    135	    136	    137	    138	    139	    140	    141	    142	    143	    144	    145	    146	    147	    148	    149
    (0,0)	(9,0)	(9,2)	(9,3)	(9,4)	(9,5)	(9,6)	(9,7)	(9,8)	(9,9)	(9,10)	(9,11)	(9,12)	(9,13)	(0,0)

    150	    151	    152	    153	    154	    155	    156	    157	    158	    159	    160	    161	    162	    163	    164
    (0,0)	(10,0)	(10,2)	(10,3)	(10,4)	(10,5)	(10,6)	(10,7)	(10,8)	(10,9)	(10,10)	(10,11)	(10,12)	(10,13)	(0,0)

    165	    166	    167	    168	    169	    170	    171	    172	    173	    174	    175	    176	    177	    178	    179
    (0,0)	(0,0)	(11,2)	(11,3)	(11,4)	(11,5)	(11,6)	(11,7)	(11,8)	(11,9)	(11,10)	(11,11)	(11,12)	(0,0)	(0,0)

    180	    181	    182	    183	    184	    185	    186	    187	    188	    189	    190	    191	    192	    193	    194
    (0,0)	(0,0)	(0,0)	(12,3)	(12,4)	(12,5)	(12,6)	(12,7)	(12,8)	(12,9)	(12,10)	(12,11)	(0,0)	(0,0)	(0,0)

    195	    196	    197	    198	    199	    200	    201	    202	    203	    204	    205 	206	    207	    208	    209
    (0,0)	(0,0)	(0,0)	(0,0)	(13,4)	(13,5)	(13,6)	(13,7)	(13,8)	(13,9)	(13,10)	(0,0)	(0,0)	(0,0)	(0,0)

    210	    211	    212	    213	    214	    215	    216	    217	    218	    219	    220 	221	    222	    223	    224
    (0,0)	(0,0)	(0,0)	(0,0)	(0,0)	(0,0)	(0,0)	(14,7)	(0,0)	(0,0)	(0,0)	(0,0)	(0,0)	(0,0)	(0,0)


    (0,0) MEANS ITS IMPOSSIBLE TO BE THERE, OVER 7 UNITS AWAY FROM MIDDLE (7,7)
    """

    ## CAN GENERATE AN ALGORITHM LATER TO GENERATE THIS, FOR NOW KEEPING IT THIS WAY
    COORDS = {0: (0, 0), 1: (0, 0), 2: (0, 0), 3: (0, 0), 4: (0, 0), 5: (0, 0), 6: (0, 0), 7: (0, 7), 8: (0, 0), 9: (0, 0), 10: (0, 0), 11: (0, 0), 12: (0, 0), 13: (0, 0), 14: (0, 0),
              15: (0, 0), 16: (0, 0), 17: (0, 0), 18: (0, 0), 19: (1, 4), 20: (1, 5), 21: (1, 6), 22: (1, 7), 23: (1, 8), 24: (1, 9), 25: (1, 10), 26: (0, 0), 27: (0, 0), 28: (0, 0), 29: (0, 0),
              30: (0, 0), 31: (0, 0), 32: (0, 0), 33: (2, 3), 34: (2, 4), 35: (2, 5), 36: (2, 6), 37: (2, 7), 38: (2, 8), 39: (2, 9), 40: (2, 10), 41: (2, 11), 42: (0, 0), 43: (0, 0), 44: (0, 0),
              45: (0, 0), 46: (0, 0), 47: (3, 2), 48: (3, 3), 49: (3, 4), 50: (3, 5), 51: (3, 6), 52: (3, 7), 53: (3, 8), 54: (3, 9), 55: (3, 10), 56: (3, 11), 57: (3, 12), 58: (0, 0), 59: (0, 0),
              60: (0, 0), 61: (4, 1), 62: (4, 2), 63: (4, 3), 64: (4, 4), 65: (4, 5), 66: (4, 6), 67: (4, 7), 68: (4, 8), 69: (4, 9), 70: (4, 10), 71: (4, 11), 72: (4, 12), 73: (4, 13), 74: (0, 0),
              75: (0, 0), 76: (5, 1), 77: (5, 2), 78: (5, 3), 79: (5, 4), 80: (5, 5), 81: (5, 6), 82: (5, 7), 83: (5, 7), 84: (5, 8), 85: (5, 9), 86: (5, 10), 87: (5, 11), 88: (5, 12), 89: (0, 0),
              90: (0, 0), 91: (6, 1), 92: (6, 2), 93: (6, 3), 94: (6, 4), 95: (6, 5), 96: (6, 6), 97: (6, 7), 98: (6, 7), 99: (6, 8), 100: (6, 9), 101: (6, 10), 102: (6, 11), 103: (6, 12), 104: (0, 0),
              105: (7, 0), 106: (7, 0), 107: (7, 2), 108: (7, 3), 109: (7, 4), 110: (7, 5), 111: (7, 6), 112: (7, 7), 113: (7, 8), 114: (7, 9), 115: (7, 10), 116: (7, 11), 117: (7, 12), 118: (7, 13), 119: (7, 14),
              120: (0, 0), 121: (8, 0), 122: (8, 2), 123: (8, 3), 124: (8, 4), 125: (8, 5), 126: (8, 6), 127: (8, 7), 128: (8, 8), 129: (8, 9), 130: (8, 10), 131: (8, 11), 132: (8, 12), 133: (8, 13), 134: (0, 0),
              135: (0, 0), 136: (9, 0), 137: (9, 2), 138: (9, 3), 139: (9, 4), 140: (9, 5), 141: (9, 6), 142: (9, 7), 143: (9, 8), 144: (9, 9), 145: (9, 10), 146: (9, 11), 147: (9, 12), 148: (9, 13), 149: (0, 0),
              150: (0, 0), 151: (10, 0), 152: (10, 2), 153: (10, 3), 154: (10, 4), 155: (10, 5), 156: (10, 6), 157: (10, 7), 158: (10, 8), 159: (10, 9), 160: (10, 10), 161: (10, 11), 162: (10, 12), 163: (10, 13), 164: (0, 0),
              165: (0, 0), 166: (0, 0), 167: (11, 2), 168: (11, 3), 169: (11, 4), 170: (11, 5), 171: (11, 6), 172: (11, 7), 173: (11, 8), 174: (11, 9), 175: (11, 10), 176: (11, 11), 177: (11, 12), 178: (0, 0), 179: (0, 0),
              180: (0, 0), 181: (0, 0), 182: (0, 0), 183: (12, 3), 184: (12, 4), 185: (12, 5), 186: (12, 6), 187: (12, 7), 188: (12, 8), 189: (12, 9), 190: (12, 10), 191: (12, 11), 192: (0, 0), 193: (0, 0), 194: (0, 0),
              195: (0, 0), 196: (0, 0), 197: (0, 0), 198: (0, 0), 199: (13, 4), 200: (13, 5), 201: (13, 6), 202: (13, 7), 203: (13, 8), 204: (13, 9), 205: (13, 10), 206: (0, 0), 207: (0, 0), 208: (0, 0), 209: (0, 0),
              210: (0, 0), 211: (0, 0), 212: (0, 0), 213: (0, 0), 214: (0, 0), 215: (0, 0), 216: (0, 0), 217: (14, 7), 218: (0, 0), 219: (0, 0), 220: (0, 0), 221: (0, 0), 222: (0, 0), 223: (0, 0), 224: (0, 0)}

    @staticmethod
    def get_new_location(key):
        """
        RETURNS RELATIVE NEW LOCATION
        BASE ON INDEX OR ARGMAX OF PREDICTION WITH HIGHEST PROBABILITY

        IF RETURNING -1, 1.  MEANS PREDICTED LOCATION IS y+-1, x+1
        WHERE y,x IS THE CURRENT LOCATION

        IF RETURNING -10, -10. SHIP PREDICTED TO DIE OR INVALID LOCATION
        """
        center = (7, 7)
        logging.debug("key {}".format(key))
        coords = Predicted.COORDS[key]

        if coords == (0, 0):
            return (-10, -10)  ## DEAD OR INVALID PREDICTION
        else:
            return coords[0] - center[0], coords[1] - center[1]

