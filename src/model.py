import numpy as np
import time

from sklearn import metrics
from sklearn import svm

#To open tensorboard fun the following in terminal at project root directory
#tensorboard --logdir='logs/fit/'

#Data preprocessing
import pickle
import cv2
import imutils
import random
import matplotlib.pyplot as plt

# Disables warning, doesn't enable AVX/FMA
import datetime, os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

#The dataset used in this assignment is a benchmark dataset to use 
import tensorflow as tf
from tensorflow import keras
from keras.callbacks import TensorBoard
from keras.models import Sequential
from keras.layers import Conv2D, GlobalAvgPool2D, MaxPool2D, Flatten, Dense

#GLOBALE VALUES
EPOCHS = 7
IMG_SIZE = 64
USE_COLOR = True
WITH_SYNTHETIC = False
CHANNELS = 3 if USE_COLOR else 1
COLOR_STATE = 'color' if USE_COLOR else 'gray'

NAME = "model_{}_{}".format(IMG_SIZE, COLOR_STATE)

CATEGORIES = [
    'dyed-lifted-polyps', 
    'dyed-resection-margins', 
    'esophagitis', 
    'normal-cecum', 
    'normal-pylorus', 
    'normal-z-line',
    'polyps', 
    'ulcerative-colitis'
]

SYTHETIC_CATEGORIES = [
    'dyed-lifted-polyps', 
    'dyed-resection-margins', 
    'esophagitis', 
    'normal-cecum'
]

'''
Looks trough the image for a green box, if found it will create a black box over
that hids what ever is inside the box. This is a precorsen to make sure the model
learns just to look inside the box for information.
'''
def remove_green_box(img_file, img_path, img):
    out_file = img_file if USE_COLOR else cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)

    hsv = cv2.cvtColor(img_file, cv2.COLOR_BGR2HSV)

    lower_green = np.array([17,163,134])
    upper_green = np.array([105, 240, 197])

    mask = cv2.inRange (hsv, lower_green, upper_green)
    green_content = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]

    if len(green_content) > 0:
        green_area = max(green_content, key = cv2.contourArea)
        (xg,yg,wg,hg) = cv2.boundingRect(green_area)

        if hg*wg > 35000 and xg < 50 and yg > 200:
            v1 = xg+wg if wg < 250 else 209+38
            v2 = yg+hg if hg < 200 else 168+384
            yg = yg if yg > 350 else 384
            cv2.rectangle(out_file,(xg,yg),(v1, v2),(0,0,0), cv2.FILLED)

    return out_file

''' 
Genaerate trainingdata by moving in to the different directories, using the name on the directories as labels for the data. 
The data from the images are together withe the labels added into an array. 
At the end, the data is suffeld in order to make sure that alle the calssifications are moved around. 
'''
def create_training_data(): 
    training_data = []   
    for category in CATEGORIES:
        path = os.path.join('data/', category)
        class_num = CATEGORIES.index(category)

        print('Building training data for ' + str(category))
        for img in os.listdir(path):
            try:                
                img_path = os.path.join(path,img)
                img_file = cv2.imread(img_path) 
                out_file = remove_green_box(img_file, img_path, img)
                img_array = cv2.resize(out_file, (IMG_SIZE, IMG_SIZE))
                training_data.append([img_array, class_num])    

            except Exception as e:
                print(e)
                pass
            
    random.shuffle(training_data)
    return training_data


def create_syntetic_training_data(): 
    (X, y) = ([], [])
    training_data = []   

    try:
        pickle_in = open("loaded_data/synthetic_X_"+str(IMG_SIZE)+"_"+str(COLOR_STATE)+".pickle","rb")
        X = pickle.load(pickle_in)

        pickle_in = open("loaded_data/synthetic_y_"+str(IMG_SIZE)+"_"+str(COLOR_STATE)+".pickle","rb")
        y = pickle.load(pickle_in)

    except Exception as e:
        print('Error: '+ str(e))
            
        for category in SYTHETIC_CATEGORIES:
            path = os.path.join('syntetic/', category)
            class_num = SYTHETIC_CATEGORIES.index(category)

            print('Building training data for ' + str(category))
            for img in os.listdir(path):
                try:                
                    img_path = os.path.join(path,img)
                    img_file = cv2.imread(img_path) if USE_COLOR else cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                    loc_y = 60
                    loc_x = 150
                    h=360
                    w=360
                    crop = img_file[loc_y:loc_y+h, loc_x:loc_x+w]
                    #cv2.imshow('Image', crop)
                    #cv2.waitKey(0) 
                    img_array = cv2.resize(crop, (IMG_SIZE, IMG_SIZE))
                    training_data.append([img_array, class_num])    

                except Exception as e:
                    print(e)
                
        random.shuffle(training_data)

        for feature, label in training_data:
            X.append(feature)
            y.append(label)

        X = np.array(X).reshape(-1, IMG_SIZE, IMG_SIZE, CHANNELS)        
        
        create_file('synthetic_y', y)
        create_file('synthetic_X', X)
    return (X,y)

def create_test_data_for_syntetic(): 
    (X, y) = ([], [])
    training_data = []   
            
    for category in SYTHETIC_CATEGORIES:
        path = os.path.join('syntetic/', category)
        class_num = SYTHETIC_CATEGORIES.index(category)

        print('Building training data for ' + str(category))
        for img in os.listdir(path):
            try:                
                img_path = os.path.join(path,img)
                out_file = cv2.imread(img_path) if USE_COLOR else cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                img_array = cv2.resize(out_file, (IMG_SIZE, IMG_SIZE))
                training_data.append([img_array, class_num])    

            except Exception as e:
                print(e)
            
    random.shuffle(training_data)

    for feature, label in training_data:
        X.append(feature)
        y.append(label)

    X = np.array(X).reshape(-1, IMG_SIZE, IMG_SIZE, CHANNELS)        
    X = (X-127.0)/127.0
    
    return (X,y)

# Creates an pickle fil. This can directly be implemented into the model for quicker training
def create_file(name, data):
    directory = 'loaded_data/'
    if not os.path.exists(directory):
        os.makedirs(directory)

    pickle_out = open(directory+name+"_"+str(IMG_SIZE)+"_"+COLOR_STATE+".pickle","wb")
    pickle.dump(data, pickle_out)
    pickle_out.close()

''' 
This function attemts to load the pickle files into memory.
If the two pickle files do not exist, the function will then 
use the two privious functions to create the training data and 
save them into files.
'''
def create_features_and_labels():
    (X, y) = ([], [])

    try:
        pickle_in = open("loaded_data/X_"+str(IMG_SIZE)+"_"+str(COLOR_STATE)+".pickle","rb")
        X = pickle.load(pickle_in)

        pickle_in = open("loaded_data/y_"+str(IMG_SIZE)+"_"+str(COLOR_STATE)+".pickle","rb")
        y = pickle.load(pickle_in)

    except Exception as e:
        print('Error: '+ str(e))

        training_data = create_training_data()

        for feature, label in training_data:
            X.append(feature)
            y.append(label)

        X = np.array(X).reshape(-1, IMG_SIZE, IMG_SIZE, CHANNELS)        
        X = (X-127.0)/127.0
        #X = X / 255.0
        
        create_file('y', y)
        create_file('X', X)

    #Splits and sets aside data for validation of the models performasce
    return (X,y)


def split_into_train_and_test(X, y, trainging_size = 0.98):
    X_split = int(len(X)*trainging_size)
    X1 = X[0: X_split]
    X2 = X[X_split: ]

    y_split = int(len(y)*trainging_size)
    y1 = y[0: y_split]
    y2 = y[y_split: ]

    return (X1, y1), (X2, y2)

''' 
Builds a CNN model with two hidden layers. The model uses a softmax in order to determen which 
category is the most correct. 
'''
def build_model():
    return Sequential([
        Conv2D(64, (2, 2), activation='relu', input_shape=(IMG_SIZE, IMG_SIZE, CHANNELS)),
        MaxPool2D((2, 2)),
        Conv2D(128, (2, 2), activation='relu'),
        MaxPool2D((2, 2)),
        Conv2D(256, (2, 2), activation='relu'),
        MaxPool2D((2, 2)),
        Flatten(),
        Dense(units=128, activation='relu'),
        Dense(units=8, activation="softmax")
    ])

# Plots the distribution between accuracy and validation accuracy
def plot_history(history):
    plt.plot(history.history['accuracy'], label='accuracy')
    plt.plot(history.history['val_accuracy'], label = 'val_accuracy')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy')
    plt.ylim([0.5, 1])
    plt.legend(loc='lower right')
    plt.show()

#PipeLine for non-synthetic data
def run_model():
    #Creating model, data and splits training data from validation data
    (features, labels) = create_features_and_labels()
    (x_train, y_train), (x_test, y_test) = split_into_train_and_test(features, labels)
    model = build_model()

    log_dir="logs/fit/"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    #Generate log to Tensorbord
    log_dir = log_dir + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + NAME
    tensorboard = TensorBoard(log_dir=log_dir, histogram_freq=1)

    #Generate a trained model
    checkpoint_path = "training_checkpoints_CNN/"
    if not os.path.exists(checkpoint_path):
        os.makedirs(checkpoint_path)

    checkpoint_path = checkpoint_path+NAME+".h5"

    cp_callback = tf.keras.callbacks.ModelCheckpoint(
        filepath=checkpoint_path, 
        save_weights_only=True, 
        verbose=1, 
        monitor='val_loss')

    #Load the pretraind model if it exist
    try:
        model.load_weights(checkpoint_path)
    except Exception as e:
        print('Exception:' + str(e))

    model.compile(
        loss='sparse_categorical_crossentropy',
        optimizer='adam',
        metrics=['accuracy'])

    history = model.fit(
        x_train, 
        y_train, 
        batch_size=32, 
        epochs=EPOCHS, 
        validation_split=0.15,
        callbacks=[ cp_callback, tensorboard ]) 

    #Evaluate the models performance
    y_pred = model.predict(x_test)
    y_pred = np.argmax(y_pred, axis = 1)

    score = metrics.classification_report(y_test, y_pred)
    print(score)
    plot_history(history)
    

#PipeLine for synthetic data
def run_synthetic_model():
    (x_train, y_train) = create_syntetic_training_data()
    (x_test, y_test) = create_test_data_for_syntetic()

    model = build_model()

    #Generate log to Tensorbord
    log_dir="logs/fit/"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_dir = log_dir+ datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + NAME + "_sythetic"
    tensorboard = TensorBoard(log_dir=log_dir, histogram_freq=1)


    #Generate a trained model
    checkpoint_path = "training_checkpoints_CNN/"
    if not os.path.exists(checkpoint_path):
        os.makedirs(checkpoint_path)

    checkpoint_path = checkpoint_path+ NAME + "_sythetic.h5"

    cp_callback = tf.keras.callbacks.ModelCheckpoint(
        filepath=checkpoint_path, 
        save_weights_only=True, 
        verbose=1, 
        monitor='val_loss')

    #Load the pretraind model if it exist
    try:
        model.load_weights(checkpoint_path)
    except Exception as e:
        print('Exception:' + str(e))

    model.compile(
        loss='sparse_categorical_crossentropy',
        optimizer='adam',
        metrics=['accuracy'])

    history = model.fit(
        x_train, 
        y_train, 
        batch_size=32, 
        epochs=EPOCHS, 
        validation_split=0.15,
        callbacks=[ cp_callback, tensorboard ]) 

    #Evaluate the models performance
    y_pred = model.predict(x_test)
    y_pred = np.argmax(y_pred, axis = 1)

    score = metrics.classification_report(y_test, y_pred)
    print(score)

    plot_history(history)

    signle_pred_syntetic('esophagitis/esophagitis14.jpg')
    signle_pred_syntetic('dyed-resection-margins/dyed-resection-margins10.jpg')

def signle_pred(img):
    model = build_model()
    checkpoint_path = "training_checkpoints_CNN/"+NAME+".h5"

    try:
        model.load_weights(checkpoint_path)
    except Exception as e:
        print('Exception:' + str(e))

    img_path = os.path.join('data/', img)
    img_file = cv2.imread(img_path) 
    img_array = cv2.resize(img_file, (IMG_SIZE, IMG_SIZE))
    X = np.array(img_array).reshape(-1, IMG_SIZE, IMG_SIZE, CHANNELS)        
    X = (X-127.0)/127.0
    
    y_pred = model.predict(X)
    y_pred = np.argmax(y_pred, axis = 1)
    print(SYTHETIC_CATEGORIES[y_pred[0]])

def signle_pred_syntetic(img):
    model = build_model()
    checkpoint_path = "training_checkpoints_CNN/"+NAME+"_sythetic.h5"

    try:
        model.load_weights(checkpoint_path)
    except Exception as e:
        print('Exception:' + str(e))

    img_path = os.path.join('data/', img)
    img_file = cv2.imread(img_path) 
    img_array = cv2.resize(img_file, (IMG_SIZE, IMG_SIZE))
    X = np.array(img_array).reshape(-1, IMG_SIZE, IMG_SIZE, CHANNELS)        
    X = (X-127.0)/127.0
    
    y_pred = model.predict(X)
    y_pred = np.argmax(y_pred, axis = 1)
    print(SYTHETIC_CATEGORIES[y_pred[0]])

#Selects function to run
if WITH_SYNTHETIC:
    run_synthetic_model()
else:
    run_model()

