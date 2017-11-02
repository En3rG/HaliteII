from keras.models import Sequential
from keras.layers import Dense, Dropout, Flatten
from keras.layers import Conv2D, MaxPooling2D
from keras.models import model_from_json
from keras.utils import np_utils
from keras import optimizers
from keras import regularizers
from keras.optimizers import SGD
import numpy as np
import keras
import logging
import time


class NeuralNet():
    def __init__(self,game):
        #self.model = self.neural_network_model()
        self.models = self.set_models(game)

    def set_models(self,game):
        ## Just an example
        models = {}

        for player in game.map.all_players():
            player_id = str(player.id)
            if game.map.my_id != player_id:
                models[player_id] = [0]

        return models

    def neural_network_model(self,Y,X,Z,num_classes):
        ## FROM CAPSTONE
        ## create model
        # model = Sequential()
        # model.add(Dense(300,input_dim=88,activation='tanh',kernel_regularizer=regularizers.l2(0.01)))
        # model.add(Dense(150,activation='tanh'))
        # model.add(Dense(3,activation='softmax'))
        #
        # ## for binary classifier
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


        ## Create Model
        model = Sequential()

        # input: 100x100 images with 3 channels -> (100, 100, 3) tensors.
        # this applies 32 convolution filters of size 3x3 each.
        #model.add(Conv2D(32, (3, 3), activation='relu', input_shape=(Y, X, Z)))
        model.add(Dense(200, input_shape=(Y, X, Z), activation='relu', kernel_regularizer=regularizers.l2(0.01)))


        # model.add(Conv2D(32, (3, 3), activation='relu'))
        # model.add(MaxPooling2D(pool_size=(2, 2)))
        # model.add(Dropout(0.25))
        # model.add(Conv2D(64, (3, 3), activation='relu'))
        # model.add(Conv2D(64, (3, 3), activation='relu'))
        # model.add(MaxPooling2D(pool_size=(2, 2)))
        # model.add(Dropout(0.25))

        model.add(Flatten())
        model.add(Dense(100, activation='relu'))
        model.add(Dense(50, activation='relu'))
        # model.add(Dropout(0.5))
        model.add(Dense(num_classes, activation='softmax'))

        sgd = SGD(lr=0.01, decay=1e-6, momentum=0.9, nesterov=True)
        model.compile(loss='categorical_crossentropy', optimizer=sgd)

        return model




    def testing():
        samples = 300
        pred = 300
        Y = 28     ## Its surrounding where it can go to
        X = 28
        Z = 10
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
        batch = 300
        num_classes = 225  ## 15x15

        # Generate dummy data
        x_train = np.random.random((samples, Y, X, Z))
        print(x_train.shape)
        y_train = keras.utils.to_categorical(np.random.randint(10, size=(samples, 1)), num_classes=num_classes)
        print(y_train.shape)
        x_test = np.random.random((pred, Y, X, Z))
        y_test = keras.utils.to_categorical(np.random.randint(10, size=(pred, 1)), num_classes=num_classes)


        model = neural_network_model(Y,X,Z,num_classes)


        start = time.clock()

        model.fit(x_train, y_train, batch_size=batch, epochs=1)

        print("elapse:", time.clock()-start)
        start = time.clock()

        score = model.evaluate(x_test, y_test, batch_size=batch)


        print("elapse:", time.clock()-start)


        start = time.clock()

        model.predict(x_test)


        print("elapse:", time.clock()-start)


