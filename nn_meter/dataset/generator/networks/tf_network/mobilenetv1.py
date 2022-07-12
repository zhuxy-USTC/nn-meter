# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
import tensorflow as tf
from .ops import *
from ..utils import  *

class MobileNetV1(object):
    def __init__(self, input, cfg, version = None, sample = False):
        ''' change channel number, kernel size
        '''
        self.input = input
        self.num_classes = cfg['n_classes']

        # fixed block channels and kernel size
        self.bcs = [32, 64, 128, 128, 256, 256, 512, 512, 512, 512, 512, 512, 1024, 1024]
        self.bks = [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3]

        # sampling block channels and kernel size
        self.cs = get_sampling_channels(cfg['sample_space']['channel']['start'], cfg['sample_space']['channel']['end'], cfg['sample_space']['channel']['step'], len(self.bcs))
        self.ks = get_sampling_ks(cfg['sample_space']['kernelsize'], len(self.bks))

        if sample == True:
            if len(self.cs) < 13:
                self.cs.append([1 for j in range(len(self.cs))])
            if len(self.ks) < 13:
                self.ks.append([3 for j in range(len(self.ks))] )
            self.ncs = [int(self.bcs[index] * self.cs[index]) for index in range(len(self.bcs))]
            self.nks = self.ks
        else:
            self.ncs = self.bcs
            self.nks = self.bks

        self.config = {}
        self.sconfig = '_'.join([str(x) for x in self.nks]) + '-' + '_'.join([str(x) for x in self.ncs])

        # build MobileNetV1 model
        self.out = self.build()

    def add_to_log(self, op, cin, cout, ks, stride, layername, inputh, inputw):
        self.config[layername] = {
            'op': op,
            'cin': cin,
            'cout': cout,
            'ks': ks,
            'stride': stride,
            'inputh': inputh,
            'inputw': inputw
        }

    def build(self):
        ''' build MobileNetV1 model according to model config
        '''
        x = conv2d(self.input, self.ncs[0], self.nks[0], opname='conv1', stride=2, padding='SAME')
        x = batch_norm(x, opname = 'conv1.bn')
        x = activation(x, 'relu', opname = 'conv1.relu')
        self.add_to_log('conv-bn-relu', 3, self.ncs[0], self.nks[0], 2, 'layer1', self.input.shape.as_list()[1], self.input.shape.as_list()[2])

        r = [1, 2, 2, 6, 2]
        s = [1, 2, 2, 2, 2]
        layer_count = 2
        for index in range(len(r)):
            stride = s[index]
            layers = r[index]
            for j in range(layers):
                (h, w) = x.shape.as_list()[1:3]
                sr = stride if j == 0 else 1
                x = depthwise_conv2d(x, self.nks[layer_count - 2], sr, opname='dwconv' + str(layer_count) + '.1')
                x = batch_norm(x, opname='dwconv' + str(layer_count) + '.1.bn')
                x = activation(x, 'relu', opname='dwconv' + str(layer_count) + '.1.relu')
                self.add_to_log('dwconv-bn-relu', self.ncs[layer_count - 2], self.ncs[layer_count - 2], self.nks[layer_count - 2], sr, 'layer' + str(layer_count) + '.1', h, w)

                (h, w) = x.shape.as_list()[1:3]
                x = conv2d(x, self.ncs[layer_count - 1], 1, opname='conv' + str(layer_count) + '.2', stride = 1)
                x = batch_norm(x, opname='conv' + str(layer_count) + '.2.bn')
                x = activation(x, 'relu', opname='conv' + str(layer_count) + '.2.relu')
                self.add_to_log('conv-bn-relu', self.ncs[layer_count - 2], self.ncs[layer_count - 1], 1, 1, 'layer' + str(layer_count) + '.2', h, w)
                layer_count += 1

        x = tf.reduce_mean(x, axis=[1, 2], keepdims=True)
        x = flatten(x)
        self.add_to_log('global-pool', self.ncs[layer_count - 2], self.ncs[layer_count - 2], None, None, 'layer' + str(layer_count + 1), 1, 1)

        x = fc_layer(x, self.num_classes, opname='fc3')
        self.add_to_log('fc', self.ncs[layer_count - 2], self.num_classes, None, None, 'layer' + str(layer_count + 2), None, None)

        return x
