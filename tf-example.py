"""
Example WeightNorm graph execution
"""
import os
import time
import numpy as np
import tensorflow as tf
from matplotlib import pyplot as plt
from tensorflow.keras.datasets.cifar10 import load_data
from tensorflow.keras.layers import WeightNorm


def regular_net(x, n_classes):
    with tf.variable_scope('Regular'):
        net = tf.layers.conv2d(x, 6, 5)
        net = tf.nn.relu(net)
        net = tf.layers.max_pooling2d(net, 2, 2)

        net = tf.layers.conv2d(net, 16, 5)
        net = tf.nn.relu(net)
        net = tf.layers.max_pooling2d(net, 2, 2)

        net = tf.layers.flatten(net)

        net = tf.layers.dense(net, 120)
        net = tf.nn.relu(net)

        net = tf.layers.dense(net, 84)
        net = tf.nn.relu(net)

        net = tf.layers.dense(net, n_classes)

    return net


def weightnorm_net(x, n_classes):
    with tf.variable_scope('WeightNorm'):
        net = WeightNorm(tf.layers.Conv2D(6, 5, activation='relu'),
                         input_shape=x.shape[1:])(x)

        net = tf.layers.MaxPooling2D(2, 2)(net)

        net = WeightNorm(tf.layers.Conv2D(16, 5, activation='relu'))(net)
        net = tf.layers.MaxPooling2D(2, 2)(net)

        net = tf.layers.Flatten()(net)
        net = WeightNorm(tf.layers.Dense(120, activation='relu'))(net)
        net = WeightNorm(tf.layers.Dense(84, activation='relu'))(net)
        net = WeightNorm(tf.layers.Dense(n_classes))(net)

    return net


def weightnorm_keras_net(x, n_classes):
    with tf.variable_scope('WeightNormKeras'):
        net = WeightNorm(tf.keras.layers.Conv2D(6, 5, activation='relu'),
                         input_shape=x.shape[1:])(x)

        net = tf.keras.layers.MaxPooling2D(2, 2)(net)

        net = WeightNorm(tf.keras.layers.Conv2D(16, 5, activation='relu'))(net)
        net = tf.keras.layers.MaxPooling2D(2, 2)(net)

        net = tf.keras.layers.Flatten()(net)
        net = WeightNorm(tf.keras.layers.Dense(120, activation='relu'))(net)
        net = WeightNorm(tf.keras.layers.Dense(84, activation='relu'))(net)
        net = WeightNorm(tf.keras.layers.Dense(n_classes))(net)

    return net


def train(x, y, num_epochs, batch_size, weightnorm=None):

    train_dataset = tf.data.Dataset.from_tensor_slices((x, y))
    train_dataset = train_dataset.shuffle(x.shape[0])
    train_dataset = train_dataset.repeat(num_epochs)
    train_dataset = train_dataset.batch(batch_size)
    iterator = train_dataset.make_initializable_iterator()

    inputs, labels = iterator.get_next()
    inputs = tf.map_fn(lambda frame: tf.image.per_image_standardization(frame),
                       inputs, dtype=tf.float32)

    if weightnorm is None:
        logits = regular_net(inputs, 10)
    elif weightnorm == 'tf':
        logits = weightnorm_net(inputs, 10)
    elif weightnorm == 'keras':
        logits = weightnorm_keras_net(inputs, 10)

    labels = tf.cast(labels, tf.int32)
    loss_op = tf.losses.sparse_softmax_cross_entropy(logits=logits, labels=labels)
    optimizer = tf.train.MomentumOptimizer(learning_rate=learning_rate, momentum=momentum)

    train_op = optimizer.minimize(loss_op)
    init = tf.global_variables_initializer()

    step = 0
    running_loss = 0
    running_loss_array = []

    with tf.Session() as sess:
        sess.run(init)
        sess.run(iterator.initializer)

        graph_path = os.path.join(os.getcwd(), 'train')
        tf.summary.FileWriter(graph_path, sess.graph)

        while True:
            try:
                _, loss = sess.run([train_op, loss_op])
                step += 1
                running_loss += (loss / batch_size)
                if step % 32 == (32 - 1):
                    print(step, running_loss)
                    running_loss_array.append(running_loss)
                    running_loss = 0.0

            except tf.errors.OutOfRangeError:
                return running_loss_array


if __name__ == "__main__":
    learning_rate = 0.001
    momentum = 0.9
    num_epochs = 3
    batch_size = 128
    n_classes = 10
    (train_x, train_y), (test_x, test_y) = load_data()

    train_x = train_x.astype(float)
    train_y = train_y.astype(float)

    # Regular Parameterization
    start = time.time()
    with tf.Graph().as_default():
        regular_loss = train(train_x, train_y, num_epochs, batch_size)
    regular_time = time.time() - start
    regular_loss = np.asarray(regular_loss)
    size = regular_loss.shape[0]
    plt.plot(np.linspace(0, size, size), regular_loss, color='blue', label='regular parameterization')

    # Layers Implementation
    start = time.time()
    with tf.Graph().as_default():
        weightnorm_loss = train(train_x, train_y, num_epochs, batch_size, weightnorm='tf')
    layers_time = time.time() - start
    weightnorm_loss = np.asarray(weightnorm_loss)
    plt.plot(np.linspace(0, weightnorm_loss.shape[0], weightnorm_loss.shape[0]), weightnorm_loss,
             color='green', label='weightnorm')

    # Keras Implementation
    start = time.time()
    with tf.Graph().as_default():
        weightnorm_keras_loss = train(train_x, train_y, num_epochs, batch_size, weightnorm='keras')
    keras_time = time.time() - start
    weightnorm_keras_loss = np.asarray(weightnorm_keras_loss)
    plt.plot(np.linspace(0, weightnorm_keras_loss.shape[0],
                         weightnorm_keras_loss.shape[0]), weightnorm_keras_loss,
             color='red', label='keras-weightnorm')

    plt.legend()
    plt.show()

    print('Regular Time: {0}'.format(regular_time))
    print('Layers Time: {0}'.format(layers_time))
    print('Keras Time: {0}'.format(keras_time))