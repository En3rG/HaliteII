from keras.models import Sequential
from keras.layers import Dense, Dropout, Flatten
from keras.layers import Conv2D, MaxPooling2D
from keras.models import model_from_json
from keras.utils import np_utils
from keras import optimizers
from keras import regularizers
from keras.optimizers import SGD
import numpy as np
import logging
import time
import copy
import keras

# import sys
# stdout = sys.stdout
# sys.stdout = open('/dev/null', 'w')
# import keras
# sys.stdout = stdout

class MyMap():
    """
    CONVERT GAME_MAP TO DICTIONARY
    FOR EACH ACCESS OF PLAYER IDs OR SHIP IDs
    """
    def __init__(self,game_map):
        self.game_map = game_map
        self.data = self.get_data()

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
            player_id = str(player.id)
            data[player_id] = {}
            for ship in player.all_ships():
                ship_id = str(ship.id)
                data[player_id][ship_id] = {'x': ship.x, \
                                            'y': ship.y, \
                                            'health': ship.health, \
                                            'dock_status': ship.docking_status.value}

        return data

class MyMatrix():
    def __init__(self, game_map, myMap_prev):
        self.game_map = game_map
        self.myMap_prev = myMap_prev
        self.matrix = self.get_matrix()

    def get_matrix(self):
        """
        GET BASE MATRIX (WITH PLANETS INFO)
        GET MAP MATRIX PER PLAYER ID
        """
        final_matrix = {}
        matrix = np.zeros((self.game_map.height, self.game_map.width), dtype=np.float)
        matrix_hp = np.zeros((self.game_map.height, self.game_map.width), dtype=np.float)
        matrix, matrix_hp = self.fill_planets(matrix,matrix_hp)

        for player in self.game_map.all_players():
            if player.id == self.game_map.my_id:
                ## SKIPPING IF ITS ME
                continue

            matrix_temp = copy.deepcopy(matrix)
            matrix_hp_temp = copy.deepcopy(matrix_hp)

            value = 1
            matrix_temp, matrix_hp_temp = self.fill_ships(matrix_temp,matrix_hp_temp,player,value)

            for player_enemy in self.game_map.all_players():
                if player_enemy.id == player.id:
                    pass
                else:
                    value = -1
                    matrix_temp, matrix_hp_temp = self.fill_ships(matrix_temp, matrix_hp_temp, player, value)

            final_matrix[player.id] = (matrix_temp,matrix_hp_temp)

        return final_matrix

    def fill_planets(self,matrix,matrix_hp):
        """
        FILL MATRIX WITH 0.5 (NOT OWNED)
        -0.5 OWNED
        ENTIRE BOX OF PLANET, CAN CHANGE TO CIRCLE LATER

        FILL IN MATRIX_HP OF PLANETS HP
        """
        for planet in self.game_map.all_planets():
            value = 0.5 if planet.is_owned else -0.5

            ## INSTEAD OF FILLING JUST THE CENTER, FILL IN A BOX
            #matrix[round(planet.y)][round(planet.x)] = value
            matrix[round(planet.y)-round(planet.radius):round(planet.y)+round(planet.radius), \
                   round(planet.x)-round(planet.radius):round(planet.x)+round(planet.radius)] = value

            ## FILL IN MATRIX_HP WITH HP OF PLANET
            matrix_hp[round(planet.y) - round(planet.radius):round(planet.y) + round(planet.radius), \
                   round(planet.x) - round(planet.radius):round(planet.x) + round(planet.radius)] = planet.health

        return matrix, matrix_hp

    def fill_ships(self,matrix,matrix_hp,player,value):
        """
        FILL MATRIX WHERE SHIP IS AT AND ITS HP
        1 FOR PLAYERS SHIP AND -1 FOR ENEMY SHIPS
        """
        for ship in player.all_ships():
            matrix[round(ship.y)][round(ship.x)] = value
            matrix_hp[round(ship.y)][round(ship.x)] = ship.health

        return matrix, matrix_hp

class NeuralNet():
    def __init__(self):
        #self.model = [0]
        self.y = 42 ## 42
        self.x = 42 ## 42
        self.z = 4 ## 4   ## UNITS, HP, PREVIOUS LOCATION, DOCKING STATUS
        self.num_classes = 225 ## 15x15
        self.batch = 300
        self.epoch = 1
        self.model = self.neural_network_model(self.y,self.x,self.z,self.num_classes)

    def train_model(self, x_train, y_train):
        self.model.fit(x_train, y_train, batch_size=self.batch, epochs=self.epoch,verbose=False)

        return self.model

    def neural_network_model(self,y,x,z,num_classes):
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
        model = Sequential()
        # ## INPUT: 100x100 IMAGES WITH 3 CHANNELS -> (100, 100, 3) TENSORS.
        # ## THIS APPLIES 32 CONVOLUTION FILTERS OF SIZE 3x3 EACH
        model.add(Conv2D(32, (3, 3), activation='relu', input_shape=(y, x, z)))
        model.add(Conv2D(32, (3, 3), activation='relu'))
        model.add(MaxPooling2D(pool_size=(2, 2)))
        model.add(Dropout(0.25))
        model.add(Conv2D(64, (3, 3), activation='relu'))
        model.add(Conv2D(64, (3, 3), activation='relu'))
        model.add(MaxPooling2D(pool_size=(2, 2)))
        model.add(Dropout(0.25))
        model.add(Flatten())
        model.add(Dense(50, activation='relu'))
        model.add(Dropout(0.5))
        model.add(Dense(num_classes, activation='softmax'))
        sgd = SGD(lr=0.01, decay=1e-6, momentum=0.9, nesterov=True)
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

    def get_3D(self,array_2d):
        """
        TAKES A LIST OF 2D ARRAY WITH YxX
        RETURNS YxXxZ ARRAY
        """
        return np.dstack(array_2d)

    def get_4D(self,array_3d):
        """
        TAKES A LIST OF 3D ARRAY WITH YxXxZ
        RETURNS DxYxXxZ ARRAY
        """
        return np.stack(array_3d)



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
        self.model.predict(x_test)

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


#a.testing_time()
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

