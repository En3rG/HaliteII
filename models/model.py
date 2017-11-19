
# import sys
# stdout = sys.stdout
# sys.stdout = open('/dev/null', 'w')
# import keras
# sys.stdout = stdout


## IF I DO THIS THEN HALITE NEVER GET INFORMATION
# import sys, os
# stderr = sys.stderr
# sys.stderr = open(os.devnull, 'w')
# import keras.backend as K
# import tensorflow as tf
# from hyperdash import Experiment
# from keras.models import Sequential, Model
# from keras.layers import Dense, Dropout, Flatten, MaxPooling1D, Conv1D, Reshape, InputLayer, Lambda, LSTM, Masking, TimeDistributed, Input, Embedding, Layer
# from keras.layers.advanced_activations import LeakyReLU, PReLU
# from keras.optimizers import Adam, Nadam, RMSprop, SGD
# from keras.callbacks import ModelCheckpoint, ReduceLROnPlateau, TensorBoard, Callback, EarlyStopping
# from keras.layers.normalization import BatchNormalization
#
# sys.stderr = stderr



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

graph = tf.get_default_graph()      ## FROM ONLINE FOR MULTITHREADING


def make_keras_picklable():
    """
    THIS FUNCTION IS REQUIRED TO PICKLE KERAS MODEL

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



class Matrix_val(Enum):
    ALLY_SHIP = 1
    ALLY_PLANET = 0.75
    UNOWNED_PLANET = 0.25
    DEFAULT = 0
    ENEMY_PLANET = -0.5
    ENEMY_SHIP_DOCKED = -0.75
    ENEMY_SHIP = -1

class MyMap():
    """
    CONVERT GAME_MAP TO DICTIONARY
    ACCESS WITH PLAYER IDs AND SHIP IDs
    """
    MAX_NODES = 3
    NUM_NODES = 0

    def __init__(self,game_map, myMap_prev):
        self.game_map = game_map
        self.myMap_prev = myMap_prev
        self.data = self.get_data()

        ## KEEP A LIMIT OF NODES IN MEMORY
        self.check_limit()

    def check_limit(self):
        """
        DELETE NODES THAT ARE OVER THE MAX LIMIT
        """
        MyMap.NUM_NODES += 1
        if MyMap.NUM_NODES > MyMap.MAX_NODES:
            ## DELETE OLD NODES
            self.myMap_prev.myMap_prev.myMap_prev = None
            MyMap.NUM_NODES -= 1

    def get_data(self):
        """
        RETURN DATA IN DICTIONARY FORM
        DOCKING STATUS:
        0 = UNDOCKED
        1 = DOCKING
        2 = DOCKED
        3 = UNDOCKING
        """
        data = {}
        for player in self.game_map.all_players():
            player_id = player.id
            data[player_id] = {}
            for ship in player.all_ships():
                ship_id = ship.id
                data[player_id][ship_id] = {'x': ship.x, \
                                            'y': ship.y, \
                                            'health': ship.health, \
                                            'dock_status': ship.docking_status.value}

        return data

class MyMatrix():
    MAX_NODES = 3
    NUM_NODES =0

    def __init__(self, game_map, myMatrix_prev,input_matrix_y,input_matrix_x):
        self.game_map = game_map
        self.matrix_prev = myMatrix_prev
        self.input_matrix_y = input_matrix_y
        self.input_matrix_x = input_matrix_x
        self.matrix = self.get_matrix()  ## A DICTIONARY CONTAINING (MATRIX, MATRIX HP) (PER PLAYER ID)

        ## KEEP A LIMIT OF NODES IN MEMORY
        self.check_limit()

    def check_limit(self):
        """
        DELETE NODES THAT ARE OVER THE MAX LIMIT
        """
        MyMatrix.NUM_NODES += 1
        if MyMatrix.NUM_NODES > MyMatrix.MAX_NODES:
            ## DELETE OLD NODES
            self.matrix_prev.matrix_prev.matrix_prev = None
            MyMatrix.NUM_NODES -= 1

    def get_matrix(self):
        """
        GET BASE MATRIX (WITH PLANETS INFO)
        GET MAP MATRIX PER PLAYER ID
        """
        final_matrix = {}
        matrix = np.zeros((self.game_map.height, self.game_map.width), dtype=np.float)
        matrix_hp = np.zeros((self.game_map.height, self.game_map.width), dtype=np.float)

        for player in self.game_map.all_players():
            if player.id == self.game_map.my_id:
                ## SKIPPING IF ITS ME
                continue

            matrix_current = copy.deepcopy(matrix)
            matrix_hp_current = copy.deepcopy(matrix_hp)
            matrix_current, matrix_hp_current = self.fill_planets(matrix_current, matrix_hp_current, player.id)


            ## FILL CURRENT PLAYER'S SHIPS
            matrix_current, matrix_hp_current = self.fill_ships_ally(matrix_current,matrix_hp_current,player)

            for player_enemy in self.game_map.all_players():
                if player_enemy.id == player.id:
                    pass
                else:
                    ## FILL CURRENT PLAYER'S ENEMY SHIPS
                    matrix_current, matrix_hp_current = self.fill_ships_enemy(matrix_current, matrix_hp_current, player_enemy)

            final_matrix[player.id] = (matrix_current,matrix_hp_current)

        return final_matrix

    def fill_planets(self,matrix,matrix_hp, player_id):
        """
        FILL MATRIX WITH:
         0.75 (OWNED BY CURRENT PLAYER)
         0.25 (NOT OWNED)
        -0.5 ENEMY OWNED
        ENTIRE BOX OF PLANET, CAN CHANGE TO CIRCLE LATER

        FILL IN MATRIX_HP OF PLANETS HP
        """
        for planet in self.game_map.all_planets():
            if not planet.is_owned():
                value = Matrix_val.UNOWNED_PLANET.value
            elif planet.owner == player_id:
                value = Matrix_val.ALLY_PLANET.value
            else:
                value = Matrix_val.ENEMY_PLANET.value

            ## INSTEAD OF FILLING JUST THE CENTER, FILL IN A BOX
            #matrix[round(planet.y)][round(planet.x)] = value
            matrix[round(planet.y)-round(planet.radius):round(planet.y)+round(planet.radius)+1, \
                   round(planet.x)-round(planet.radius):round(planet.x)+round(planet.radius)+1] = value

            ## FILL IN MATRIX_HP WITH HP OF PLANET
            matrix_hp[round(planet.y) - round(planet.radius):round(planet.y) + round(planet.radius)+1, \
                      round(planet.x) - round(planet.radius):round(planet.x) + round(planet.radius)+1] = planet.health

        return matrix, matrix_hp

    def fill_ships_ally(self,matrix,matrix_hp,player):
        """
        FILL MATRIX WHERE SHIP IS AT AND ITS HP
        1 FOR ALL ALLY
        """
        value = Matrix_val.ALLY_SHIP.value

        for ship in player.all_ships():
            matrix[round(ship.y)][round(ship.x)] = value
            matrix_hp[round(ship.y)][round(ship.x)] = ship.health

        return matrix, matrix_hp

    def fill_ships_enemy(self, matrix, matrix_hp, player):
        """
        FILL MATRIX WHERE SHIP IS AT AND ITS HP

        value WILL DEPEND ON ENEMY, IF DOCKED OR NOT
        """
        for ship in player.all_ships():
            if ship.docking_status.value == 0:  ## UNDOCKED
                value = Matrix_val.ENEMY_SHIP.value
            else:
                value = Matrix_val.ENEMY_SHIP_DOCKED.value

            matrix[round(ship.y)][round(ship.x)] = value
            matrix_hp[round(ship.y)][round(ship.x)] = ship.health

        return matrix, matrix_hp

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
        self.batch = 300
        self.epoch = 1
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

            ## FROM CAPSTONE
            ## CREATE MODEL
            # model = Sequential()
            # model.add(Dense(300,input_dim=88,activation='tanh',kernel_regularizer=regularizers.l2(0.01)))
            # model.add(Dense(150,activation='tanh'))
            # model.add(Dense(3,activation='softmax'))
            #
            # ## FOR BINARY CLASSIFIER
            # #model.compile(loss='binary_crossentropy',optimizer='adam',metrics=['accuracy'])
            # #model.compile(loss='mean_squared_error',optimizer='adam',metrics=['accuracy'])
            # #model.compile(loss='categorical_crossentropy',optimizer='adam',metrics=['accuracy'])
            # #model.compile(loss='categorical_crossentropy',optimizer='adamax',metrics=['accuracy'])
            # #model.compile(loss='categorical_crossentropy',optimizer='nadam',metrics=['accuracy'])
            # #model.compile(loss='categorical_crossentropy',optimizer='rmsprop',metrics=['accuracy'])
            # #model.compile(loss='categorical_crossentropy',optimizer='adagrad',metrics=['accuracy'])
            # #model.compile(loss='categorical_crossentropy',optimizer='adadelta',metrics=['accuracy'])
            # #model.compile(loss='categorical_crossentropy',optimizer='tfoptimizer',metrics=['accuracy'])
            #
            # opt = optimizers.SGD(lr=0.001,momentum=0.9,decay=1e-6,nesterov=True)
            # model.compile(loss='categorical_crossentropy',optimizer=opt,metrics=['accuracy'])
            #
            # return model


            ## NOT THAT SIMPLE
            ## CREATE MODEL
            # model = Sequential()
            # # ## INPUT: 100x100 IMAGES WITH 3 CHANNELS -> (100, 100, 3) TENSORS.
            # # ## THIS APPLIES 32 CONVOLUTION FILTERS OF SIZE 3x3 EACH
            # model.add(Conv2D(32, (3, 3), activation='relu', input_shape=(y, x, z)))
            # model.add(Conv2D(32, (3, 3), activation='relu'))
            # model.add(MaxPooling2D(pool_size=(2, 2)))
            # model.add(Dropout(0.25))
            # model.add(Conv2D(64, (3, 3), activation='relu'))
            # model.add(Conv2D(64, (3, 3), activation='relu'))
            # model.add(MaxPooling2D(pool_size=(2, 2)))
            # model.add(Dropout(0.25))
            # model.add(Flatten())
            # model.add(Dense(50, activation='relu'))
            # model.add(Dropout(0.5))
            # model.add(Dense(num_classes, activation='softmax'))
            # sgd = SGD(lr=0.01, decay=1e-6, momentum=0.9, nesterov=True)
            # model.compile(loss='categorical_crossentropy', optimizer=sgd)


            ## SIMPLIER THAN ABOVE
            model = Sequential()
            # ## INPUT: 100x100 IMAGES WITH 3 CHANNELS -> (100, 100, 3) TENSORS.
            # ## THIS APPLIES 32 CONVOLUTION FILTERS OF SIZE 3x3 EACH
            model.add(Conv2D(32, (3, 3), activation='relu', input_shape=(y, x, z)))
            model.add(MaxPooling2D(pool_size=(2, 2)))
            model.add(Conv2D(64, (3, 3), activation='relu'))
            model.add(MaxPooling2D(pool_size=(2, 2)))
            model.add(Flatten())
            model.add(Dense(50, activation='relu'))
            model.add(Dense(num_classes, activation='softmax'))
            #sgd = SGD(lr=0.01, decay=1e-6, momentum=0.9, nesterov=True)
            sgd = NeuralNet.get_sgd()
            model.compile(loss='categorical_crossentropy', optimizer=sgd)

            ## SIMPLE VERSION!
            ## CREATE MODEL
            # model = Sequential()
            # model.add(Dense(200, input_shape=(y, x, z), activation='relu', kernel_regularizer=regularizers.l2(0.01)))
            # model.add(Flatten())
            # model.add(Dense(100, activation='relu'))
            # model.add(Dense(50, activation='relu'))
            # model.add(Dense(num_classes, activation='softmax'))
            #
            # sgd = SGD(lr=0.01, decay=1e-6, momentum=0.9, nesterov=True)
            # model.compile(loss='categorical_crossentropy', optimizer=sgd)


        return model

    @staticmethod
    def get_sgd():
        return SGD(lr=0.01, decay=1e-6, momentum=0.9, nesterov=True)

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

        if myMap.myMap_prev is not None:
            ## GO THROUGH PREVIOUS SHIPS OF CURRENT PLAYER
            for ship_id, ship_data in myMap.myMap_prev.data[player_id].items():
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

                    ## GET MATRIX HP
                    ## +1 TO INCLUDE VALUE AT half_y
                    matrix_hp_current = matrix_hp[prev_y - half_y:prev_y + half_y + 1, \
                                                  prev_x - half_x:prev_x + half_x + 1]

                    ## CHECK IF SHIP EXIST BEFORE
                    ## PREVIOUS PREVIOUS LOCATION
                    ship_prev = myMap.myMap_prev.myMap_prev.data[player_id].get(ship_id)

                    matrix_prev_loc = np.zeros((myMatrix.input_matrix_y, myMatrix.input_matrix_x), dtype=np.float)
                    if ship_prev:  ## WILL BE NONE IF SHIP DIDNT EXIST PREVIOUSLY

                        ## GET PREVIOUS LOCATION OF THIS SHIP
                        prev_prev_x = ship_prev.get('x')
                        prev_prev_y = ship_prev.get('y')

                        prev_prev_y = round(prev_prev_y)
                        prev_prev_x = round(prev_prev_x)

                        row = half_y + (prev_prev_y - prev_y)
                        col = half_x + (prev_prev_x - prev_x)

                        ## PLACE A 1 TO REPRESENT PREVIOUS LOCATION
                        matrix_prev_loc[row][col] = Matrix_val.ALLY_SHIP.value


                    ## GET 3D ARRAY FOR TRAINING
                    x_train_data_current = NeuralNet.get_3D([matrix_current, matrix_hp_current, matrix_prev_loc])
                    x_train_data.append(x_train_data_current)


                    ## NEED TO GET y_train FOR THIS SHIP
                    y_train_current = np.zeros((15, 15), dtype=np.float)

                    now_ship = myMap.data[player_id].get(ship_id)

                    if now_ship: ## IF NONE, SHIP DIED
                        ## CURRENT SHIP POSITION
                        now_x = round(now_ship['x'])
                        now_y = round(now_ship['y'])

                        row = 7 + (now_y - prev_y)
                        col = 7 + (now_x - prev_x)

                        logging.info("testing!!1 with player id: {}".format(player_id))
                        logging.info("Current position x: {} y {}".format(now_x,now_y))
                        logging.info("Prev position x: {} y {}".format(prev_x, prev_y))
                        logging.info("position x: {} y {}".format(col, row))

                        y_train_current[row][col] = Matrix_val.ALLY_SHIP.value

                    y_train_current = np.ndarray.flatten(y_train_current)
                    y_train_data.append(y_train_current)

            ## GET 4D ARRAY FOR TRAINING
            x_train = NeuralNet.get_4D(x_train_data)
            y_train = NeuralNet.get_2D(y_train_data)



        ## TESTING ONLY
        # samples = 200
        # y = 27
        # x = 27
        # z = 3
        # num_classes = 225
        # x_train = np.random.random((samples, y, x, z))
        # y_train = keras.utils.to_categorical(np.random.randint(10, size=(samples, 1)), num_classes=num_classes)


        return x_train, y_train

    @staticmethod
    def get_predicting_data(player_id, myMap, myMatrix):
        """
        GET SHIPS THAT HAVE ENEMY ON SIGHT
        PREP DATA FOR INPUT TO MODEL
        """
        ship_ids = []
        train_data = []

        ## GO THROUGH SHIPS OF CURRENT PLAYER
        for ship_id, ship_data in myMap.data[player_id].items():
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
                ship_prev = myMap.myMap_prev.data[player_id].get(ship_id)

                matrix_prev_loc = np.zeros((myMatrix.input_matrix_y, myMatrix.input_matrix_x), dtype=np.float)
                if ship_prev:  ## WILL BE NONE IF SHIP DIDNT EXIST PREVIOUSLY
                    ## GET PREVIOUS LOCATION OF THIS SHIP
                    prev_x = ship_prev.get('x')
                    prev_y = ship_prev.get('y')

                    prev_y = round(prev_y)
                    prev_x = round(prev_x)

                    row = half_y + (prev_y - now_y)
                    col = half_x + (prev_x - now_x)

                    ## PLACE A 1 TO REPRESENT PREVIOUS LOCATION
                    matrix_prev_loc[row][col] = Matrix_val.ALLY_SHIP.value

                ## GET 3D ARRAY FOR TRAINING
                train_data_current = NeuralNet.get_3D([matrix_current,matrix_hp_current,matrix_prev_loc])
                train_data.append(train_data_current)

        ## GET 4D ARRAY FOR TRAINING
        x_test = NeuralNet.get_4D(train_data)


        # ## TESTING ONLY
        # samples = 200
        # y = 27
        # x = 27
        # z = 3
        # num_classes = 225
        # x_test = np.random.random((samples, y, x, z))
        # ship_ids = []  ## WILL CONTAIN SHIP IDS OF BEING PREDICTED

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
        for x in array_2d:
            logging.info("Shapes for 3d: {}".format(x.shape))
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
        for player_id, dict in predictions.items():

            ## LOOPING WILL BE VERY SLOW, USE MAP!!!!!!!!!!!!!!!!!!!!!!!!!!!

            ship_ids, data = dict

            for id, pred in zip(ship_ids,data):

                ## NO NEED TO RESHAPE. CAN JUST GET ARGMAX AND HAVE A DICTIONARY TO GET VALUES FASTER
                # ncols = 15
                # new = np.reshape(pred, (-1, ncols))  ## -1 TO AUTOMATICALLY CALCULATE #ROWS PER ncols GIVEN

                logging.info("Test!1 argmax: {} max: {}".format(np.argmax(pred),max(pred)))

                Predict.COORDS[1]


    def testing_time(self):
        """
        TESTING HOW LONG IT TAKES TO PREDICT/TRAIN A MODEL
        """
        samples = 200
        pred = 200
        """
        - YxX (1 for ships, -1 for enemy)
        - health of ships mentioned above
        - where YxX is base on entire map,
        - location of the planets on YxX map resolution
        - radius of planets
        - Planet ownership (1 yours, -1 enemy, 0.5 unowned?)
        - Num of our ships in YxX resolution
        - Total healths of above?
        - Num of enemy ships in YxX resolution
        - Total healths of above?
        """

        # GENERATE DUMMY DATA
        #x_train = np.random.random((samples, self.y, self.x, self.z))
        ## ABOVE IS SIMPLEST WAY OF GENERATING DxYxXxZ array
        ## BELOW IS STEPS TO COMBINE FROM 2D ARRAY
        ## c = np.dstack((a,b))  ## BECOMES YxXxZ, WHERE a AND b ARE 2D ARRAY
        ## d = np.stack((c1,c2))  ## BECOMES DxYxXxZ, WHERE c1 AND c2 ARE BUILT FROM ABOVE (3D ARRAY)
        x_train = np.stack([ np.dstack([np.random.random((self.y, self.x)) for i in range(self.z)]) for _ in range(samples) ])

        print(x_train.shape)
        y_train = keras.utils.to_categorical(np.random.randint(10, size=(samples, 1)), num_classes=self.num_classes)

        print(y_train.shape)
        x_test = np.random.random((pred, self.y, self.x, self.z))

        y_test = keras.utils.to_categorical(np.random.randint(10, size=(pred, 1)), num_classes=self.num_classes)

        start = time.clock()

        self.model.fit(x_train, y_train, batch_size=self.batch, epochs=1)

        print("Train elapse:", time.clock()-start)
        start = time.clock()

        score = self.model.evaluate(x_test, y_test, batch_size=self.batch)

        print("Evaluate elapse:", time.clock()-start)

        start = time.clock()
        predictions = self.model.predict(x_test)

        print("Predict elapse:", time.clock()-start)


    def numpy_test(self):

        start = time.clock()

        array = np.zeros((5,5), dtype=np.int)

        print("Init numpy elapse:", time.clock() - start)

        print(array)

        start = time.clock()

        new = array[:40,:40]  ## EVEN IF ARRAY IS SMALLER, WILL NOT ERROR

        print("elapse:", time.clock() - start)

        print(new)


class Predict():
    COORDS = {0:(0,0),
              1:(0,0),
              3:(0,0),}




# make_keras_picklable()
#
# samples = 200
# y = 42
# x = 42
# z = 4
# num_classes = 225
# x_train = np.random.random((samples, y, x, z))
# y_train = keras.utils.to_categorical(np.random.randint(10, size=(samples, 1)), num_classes=num_classes)
#
# a = NeuralNet()
# b = NeuralNet()
# a.model.fit(x_train, y_train, batch_size=a.batch, epochs=a.epoch,verbose=1)
# print(type(a.model))
# pick_a = pickle.dumps(a.model)
# pick_b = pickle.dumps(b.model)
# print(type(pick_a))
#
# unpick_a = pickle.loads(pick_a)
# unpick_a.fit(x_train, y_train, batch_size=300, epochs=1, verbose=1)
# print(type(unpick_a))
# unpick_b = pickle.loads(pick_b)
#
#
# def test_fit(x_train,y_train,batch_size,epochs,verbose):
#     unpick_a.fit(x_train, y_train, batch_size=300, epochs=1, verbose=1)
#
# args = (x_train,y_train,300,1,1)
# thread = Thread(target=test_fit,args=args)
# thread.start()
#
#
# args = (x_train,y_train,300,1,1)
# thread2 = Thread(target=test_fit,args=args)
# thread2.start()








## FOR TESTING ONLY
# a = NeuralNet()
# samples = 200
# y = 42
# x = 42
# z = 4
# num_classes = 225
# x_train = np.random.random((samples, y, x, z))
# y_train = keras.utils.to_categorical(np.random.randint(10, size=(samples, 1)), num_classes=num_classes)
# a.train_model(x_train,y_train)


# a = NeuralNet()
# a.testing_time()
#a.numpy_test()


# a1 = np.random.random((3,3))
# b1 = np.random.random((3,3))
# print(a1)
# print(b1)
# c1 = np.dstack((a1,b1))  ## BECOMES YxXxZ
# #c1 = a.get_3D([a1,b1])
# print(c1.shape)
# print(c1)
#
# a2 = np.random.random((3,3))
# b2 = np.random.random((3,3))
# print(a2)
# print(b2)
# c2 = np.dstack((a2,b2))
# #c2 = a.get_3D([a2,b2])
# print(c2.shape)
# print(c2)
#
#
# d = np.stack((c1,c2))  ## BECOMES DxYxXxZ
# #d = a.get_4D([c1,c2])
# print(d.shape)
# print(d)






# from multiprocessing import Process, freeze_support
# from keras.models import model_from_json
# from keras.models import Sequential
# from keras.layers import Dense, Dropout, Flatten
# from keras.layers import Conv2D, MaxPooling2D
# from keras.utils import np_utils
# from keras import optimizers
# from keras import regularizers
# from keras.optimizers import SGD
# import keras
#
# class NeuralNet():
#     def __init__(self):
#         self.y = 28
#         self.x = 28
#         self.z = 3
#         self.num_classes = 225
#         self.batch = 300
#         self.epoch = 1
#         self.model = self.neural_network_model(self.y,self.x,self.z,self.num_classes)
#
#     def neural_network_model(self,y,x,z,num_classes):
#         model = None
#         with graph.as_default():
#             model = Sequential()
#             model.add(Conv2D(32, (3, 3), activation='relu', input_shape=(y, x, z)))
#             model.add(Conv2D(32, (3, 3), activation='relu'))
#             model.add(MaxPooling2D(pool_size=(2, 2)))
#             model.add(Dropout(0.25))
#             model.add(Conv2D(64, (3, 3), activation='relu'))
#             model.add(Conv2D(64, (3, 3), activation='relu'))
#             model.add(MaxPooling2D(pool_size=(2, 2)))
#             model.add(Dropout(0.25))
#             model.add(Flatten())
#             model.add(Dense(50, activation='relu'))
#             model.add(Dropout(0.5))
#             model.add(Dense(num_classes, activation='softmax'))
#             sgd = SGD(lr=0.01, decay=1e-6, momentum=0.9, nesterov=True)
#             model.compile(loss='categorical_crossentropy', optimizer=sgd)
#
#         return model
#
# def save_model():
#     ## CREATE MODEL
#     NN = NeuralNet()
#     model_json = NN.model.to_json()
#     with open("test.json", "w") as json_file:
#         json_file.write(model_json)
#
#     ## Serialize weights to HDF5
#     NN.model.save_weights("test.h5")
#
# def get_data():
#     ## SAMPLE DATA
#     samples = 200
#     y = 28
#     x = 28
#     z = 3
#     num_classes = 225
#     x_train = np.random.random((samples, y, x, z))
#     y_train = keras.utils.to_categorical(np.random.randint(10, size=(samples, 1)), num_classes=num_classes)
#
#     return x_train, y_train
#
# def load_model():
#     json_file = open("test.json", "r")
#     loaded_model_json = json_file.read()
#     json_file.close()
#     model = model_from_json(loaded_model_json)
#     ## Load weights into new model
#     model.load_weights("test.h5")
#     sgd = SGD(lr=0.01, decay=1e-6, momentum=0.9, nesterov=True)
#     model.compile(loss='categorical_crossentropy', optimizer=sgd)
#
#     return model
#
# def spawn_predictors(p,x_train):
#     for id in [1,2,3,4,5,6,7]:
#         arguments = (x_train,)
#         p[id] = Process(target=predictor_handler, args=arguments)
#         p[id].start()
#         p[id].join()
#
# def predictor_handler(x_train):
#     start = time.clock()
#
#     model = load_model()
#     print("Loaded model")
#     predictions = model.predict(x_train)
#     print("Predictions done")
#
#     end = time.clock()
#     print("Predictions took {}".format(end - start))
#
#
# if __name__ == "__main__":
#     freeze_support()
#
#     save_model()
#     x_train, y_train = get_data()
#
#     start = time.clock()
#     model = load_model()
#     predictions = model.predict(x_train)
#     end = time.clock()
#     print("Predictions time (main process): ", end-start)
#
#     p = {}
#     start = time.clock()
#     spawn_predictors(p,x_train)
#     end = time.clock()
#     print("Predictions time (subprocess): ",end-start)




