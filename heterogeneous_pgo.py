# -*- coding: utf-8 -*-
"""heterogeneous-pgo.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/13VY3pXT2Yt_ngM8lBQXAH8A2My8jEQOK
"""

import tensorflow as tf
from tensorflow import keras
import numpy as np
import matplotlib.pyplot as plt
import random
import sklearn

from keras.datasets.mnist import load_data
(X_train, y_train), (X_test, y_test) = load_data()
X_train, X_valid = X_train[10_000:], X_train[:10000]
y_train, y_valid = y_train[10_000:], y_train[:10000]

print(f"""X_train: {X_train.shape}, y_train: {y_train.shape},
X_valid: {X_valid.shape}, y_valid: {y_valid.shape},
X_test: {X_test.shape}, y_test: {y_test.shape} """)

X_train, X_valid, X_test = X_train/255.0, X_valid/255.0, X_test/255.0
X_train, X_valid, X_test = X_train.reshape((-1, 28, 28, 1)), X_valid.reshape((-1, 28, 28, 1)), X_test.reshape((-1, 28, 28, 1))

50000/256

x = []
y = []
count = 0
for i in range(195):
    x.append(X_train[count:count+256])
    y.append(y_train[count:count+256])
    count += 256

"""# Model"""

model = keras.models.Sequential([
    keras.layers.Conv2D(32, 4, activation = "relu", kernel_initializer = "he_normal", padding = "same", input_shape = [28, 28, 1]),
    keras.layers.Conv2D(64, 4, activation = "relu", kernel_initializer = "he_normal", padding = "same"),
    keras.layers.MaxPooling2D(2),
    keras.layers.Conv2D(128, 3, activation = "relu", kernel_initializer = "he_normal", padding = "same"),
    keras.layers.AveragePooling2D(2),
    keras.layers.Conv2D(128, 3, activation = "relu", kernel_initializer = "he_normal", padding = "same"),
    keras.layers.AveragePooling2D(2),
    keras.layers.GlobalAveragePooling2D(),
    keras.layers.Dropout(rate = 0.2),
    keras.layers.Dense(10, activation = "softmax", kernel_initializer = "glorot_normal")
])
model.summary()

def single_opt(model, epochs, optimizer, loss_fn, x, y, X_valid, y_valid, X_test, y_test):
    accuracies = []
    losses = []
    flag = False
    for epoch in range(epochs):
        print(f"Epoch {epoch + 1}/{epochs}")
        for x_, y_ in zip(x, y):
            with tf.GradientTape() as tape:
                logits = model(x_, training=True)
                loss = loss_fn(y_, logits)

            grads = tape.gradient(loss, model.trainable_weights)
            optimizer.apply_gradients(zip(grads, model.trainable_weights))

        loss, acc = model.evaluate(X_valid, y_valid, verbose=0)
        losses.append(loss)
        accuracies.append(acc*100)
        print(f'Loss: {loss}, Accuracy: {acc*100}')

    results = model.evaluate(X_test, y_test, verbose=1)

    print('Test loss:', results[0])
    print('Test accuracy:', results[1]*100)

    return model, losses, accuracies

"""## 1.1 SGD (lr = 0.009)"""

model_baseline = tf.keras.models.clone_model(model)
optimizer = tf.keras.optimizers.SGD(learning_rate = 0.009)
loss_fn = tf.keras.losses.SparseCategoricalCrossentropy()
model_baseline.compile(loss='sparse_categorical_crossentropy', metrics=['accuracy'])

model_sgd, losses_sgd, accuracies_sgd = single_opt(
    model_baseline, 20, optimizer, loss_fn, x, y, X_valid, y_valid, X_test, y_test
)
tf.keras.backend.clear_session()

"""## 1.2 SGD + Momentum with nesterov = True (0.9) (lr = 0.009)"""

model_baseline = tf.keras.models.clone_model(model)
optimizer = tf.keras.optimizers.SGD(learning_rate = 0.009, momentum = 0.9, nesterov = True)
loss_fn = tf.keras.losses.SparseCategoricalCrossentropy()
model_baseline.compile(loss='sparse_categorical_crossentropy', metrics=['accuracy'])

model_nag, losses_nag, accuracies_nag = single_opt(
    model_baseline, 20, optimizer, loss_fn, x, y, X_valid, y_valid, X_test, y_test
)
tf.keras.backend.clear_session()

"""## 1.3 RMSprop (lr = 0.009)"""

model_baseline = tf.keras.models.clone_model(model)
optimizer = tf.keras.optimizers.RMSprop(learning_rate = 0.009)
loss_fn = tf.keras.losses.SparseCategoricalCrossentropy()
model_baseline.compile(loss='sparse_categorical_crossentropy', metrics=['accuracy'])

model_rmsprop, losses_rmsprop, accuracies_rmsprop = single_opt(
    model_baseline, 20, optimizer, loss_fn, x, y, X_valid, y_valid, X_test, y_test
)
tf.keras.backend.clear_session()

"""## 1.4 Adagrad (lr = 0.009)"""

model_baseline = tf.keras.models.clone_model(model)
optimizer = tf.keras.optimizers.Adagrad(learning_rate = 0.009)
loss_fn = tf.keras.losses.SparseCategoricalCrossentropy()
model_baseline.compile(loss='sparse_categorical_crossentropy', metrics=['accuracy'])

model_adagrad, losses_adagrad, accuracies_adagrad = single_opt(
    model_baseline, 20, optimizer, loss_fn, x, y, X_valid, y_valid, X_test, y_test
)
tf.keras.backend.clear_session()

"""## 1.5 Adam (lr = 0.009)"""

model_baseline = tf.keras.models.clone_model(model)
optimizer = tf.keras.optimizers.Adam(learning_rate = 0.009)
loss_fn = tf.keras.losses.SparseCategoricalCrossentropy()
model_baseline.compile(loss='sparse_categorical_crossentropy', metrics=['accuracy'])

model_adam, losses_adam, accuracies_adam = single_opt(
    model_baseline, 20, optimizer, loss_fn, x, y, X_valid, y_valid, X_test, y_test
)
tf.keras.backend.clear_session()

"""# PGO"""

def pgo(model, epochs, optimizer1, optimizer2, loss_fn, x, y, X_valid, y_valid, X_test, y_test):
    iter_count = 0
    loss_list = []
    acc_list = []
    flag = False

    with tf.GradientTape() as tape:
        logits2 = model(x[0], training=True)
        loss2 = loss_fn(y[0], logits2)
    grads2 = tape.gradient(loss2, model.trainable_weights)
    for epoch in range(epochs):
        print(f'Epoch: {epoch + 1} / {epochs}')
        for x_, y_ in zip(x, y):
            if iter_count % 2 ==0:
                with tf.GradientTape() as tape:
                    logits1 = model(x_, training = True)
                    loss1 = loss_fn(y_, logits1)
                grads1 = tape.gradient(loss1, model.trainable_weights)
                guidance1 = [(1 - tf.exp(-tf.abs(i))) for i in grads1]

                weighted_guidance1 = [
                    grads_*guidance_ for grads_, guidance_ in zip(grads2,guidance1)
                ]

                optimizer1.apply_gradients(zip(grads1+weighted_guidance1, model.trainable_weights))


            else:
                with tf.GradientTape() as tape:
                    logits2 = model(x_, training = True)
                    loss2 = loss_fn(y_, logits2)
                grads2 = tape.gradient(loss2, model.trainable_weights)
                guidance2 = [(1 - tf.exp(-tf.abs(i))) for i in grads2]

                weighted_guidance2 = [
                    grads_*guidance_ for grads_, guidance_ in zip(grads1,guidance2)
                ]

                optimizer2.apply_gradients(zip(grads2+weighted_guidance2, model.trainable_weights))

            iter_count += 1

        loss, acc = model.evaluate(X_valid, y_valid, verbose = 0)
        loss_list.append(loss)
        acc_list.append(acc*100)
        print(f'Loss: {loss}, Accuracy: {acc}')

    print(f"""acc1: {model.evaluate(X_test, y_test, verbose=1)}""")

    return model, loss_list, acc_list

"""## PGO (Adam 0.009, SGD 0.005)"""

tf.keras.backend.clear_session()

model_pgo = tf.keras.models.clone_model(model)

optimizer1 = tf.keras.optimizers.Adam(learning_rate = 0.0045)
optimizer2 = tf.keras.optimizers.SGD(learning_rate = 0.0045)

loss_fn = tf.keras.losses.SparseCategoricalCrossentropy()

model_pgo.compile(loss='sparse_categorical_crossentropy', metrics=['accuracy'])

model_pgo, losses_pgo, accuracies_pgo = pgo(
    model_pgo, 20, optimizer1, optimizer2, loss_fn, x, y, X_valid, y_valid, X_test, y_test
)
tf.keras.backend.clear_session()

import matplotlib.pyplot as plt
epochs = range(1, len(accuracies_sgd) + 1)

plt.plot(epochs, accuracies_sgd, marker='x', linestyle='dashed', label='SGD')
plt.plot(epochs, accuracies_nag, marker='+', linestyle='dashed', label='NAG')
plt.plot(epochs, accuracies_rmsprop, marker='1', linestyle='dashed', label='RMSprop')
plt.plot(epochs, accuracies_adagrad, marker='2', linestyle='dashed', label='Adagrad')
plt.plot(epochs, accuracies_adam, marker='.', linestyle='dashed', label='Adam')
plt.plot(epochs, accuracies_pgo, marker='*', linestyle='dashed', label='Heterogeneous PGO')

plt.xlabel('Epochs')
plt.ylabel('Accuracy')

plt.grid(True, linestyle='--', alpha=0.6)
plt.legend(loc='best', fontsize=10)
tick_positions = [1, 5, 10, 15, 20]
plt.xticks(tick_positions)
plt.yticks(fontsize=10)
plt.tight_layout()

plt.legend()
plt.show()

epochs = range(1, len(accuracies_sgd) + 1)

plt.plot(epochs, losses_sgd, marker='x', linestyle='dashed', label='SGD')
plt.plot(epochs, losses_nag, marker='+', linestyle='dashed', label='NAG')
plt.plot(epochs, losses_rmsprop, marker='1', linestyle='dashed', label='RMSprop')
plt.plot(epochs, losses_adagrad, marker='2', linestyle='dashed', label='Adagrad')
plt.plot(epochs, losses_adam, marker='.', linestyle='dashed', label='Adam')
plt.plot(epochs, losses_pgo, marker='*', linestyle='dashed', label='Heterogenrous PGO')

plt.xlabel('Epochs')
plt.ylabel('Loss')

plt.grid(True, linestyle='--', alpha=0.6)
plt.legend(loc='best', fontsize=10)
tick_positions = [1, 5, 10, 15, 20]
plt.xticks(tick_positions)
plt.yticks(fontsize=10)
plt.tight_layout()

plt.legend()
plt.show()

losses = np.array([losses_sgd,
                  losses_nag,
                  losses_rmsprop,
                  losses_adagrad,
                  losses_adam,
                  losses_pgo])
np.save('losses_mnist.npy', losses)

accuracies = np.array([accuracies_sgd,
                  accuracies_nag,
                  accuracies_rmsprop,
                  accuracies_adagrad,
                  accuracies_adam,
                  accuracies_pgo])
np.save('accuracies_mnist.npy', accuracies)

