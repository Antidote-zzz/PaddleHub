#   Copyright (c) 2019  PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import collections
import time
import multiprocessing

import numpy as np
import paddle.fluid as fluid

from paddlehub.finetune.task import Task

__all__ = ['append_mlp_classifier']


def append_mlp_classifier(feature, label, num_classes=2, hidden_units=None):
    """
    Append a multi-layer perceptron classifier for binary classification base
    on input feature
    """
    cls_feats = fluid.layers.dropout(
        x=feature, dropout_prob=0.1, dropout_implementation="upscale_in_train")

    # append fully connected layer according to hidden_units
    if hidden_units is not None:
        for n_hidden in hidden_units:
            cls_feats = fluid.layers.fc(input=cls_feats, size=n_hidden)

    logits = fluid.layers.fc(
        input=cls_feats,
        size=num_classes,
        param_attr=fluid.ParamAttr(
            name="cls_out_w",
            initializer=fluid.initializer.TruncatedNormal(scale=0.02)),
        bias_attr=fluid.ParamAttr(
            name="cls_out_b", initializer=fluid.initializer.Constant(0.)))

    ce_loss, probs = fluid.layers.softmax_with_cross_entropy(
        logits=logits, label=label, return_softmax=True)
    loss = fluid.layers.mean(x=ce_loss)

    num_example = fluid.layers.create_tensor(dtype='int64')
    accuracy = fluid.layers.accuracy(
        input=probs, label=label, total=num_example)

    graph_var_dict = {
        "loss": loss,
        "probs": probs,
        "accuracy": accuracy,
        "num_example": num_example
    }

    task = Task("text_classification", graph_var_dict,
                fluid.default_main_program(), fluid.default_startup_program())

    return task


def append_mlp_multi_classifier(feature,
                                label,
                                num_classes,
                                hidden_units=None,
                                act=None):
    pass


def append_sequence_labeler(feature, labels, seq_len, num_classes=None):
    logits = fluid.layers.fc(
        input=feature,
        size=num_classes,
        num_flatten_dims=2,
        param_attr=fluid.ParamAttr(
            name="cls_seq_label_out_w",
            initializer=fluid.initializer.TruncatedNormal(scale=0.02)),
        bias_attr=fluid.ParamAttr(
            name="cls_seq_label_out_b",
            initializer=fluid.initializer.Constant(0.)))

    ret_labels = fluid.layers.reshape(x=labels, shape=[-1, 1])
    ret_infers = fluid.layers.reshape(
        x=fluid.layers.argmax(logits, axis=2), shape=[-1, 1])

    labels = fluid.layers.flatten(labels, axis=2)
    ce_loss, probs = fluid.layers.softmax_with_cross_entropy(
        logits=fluid.layers.flatten(logits, axis=2),
        label=labels,
        return_softmax=True)
    loss = fluid.layers.mean(x=ce_loss)
    # accuracy = fluid.layers.accuracy(
    #     input=probs, label=labels, total=num_example)

    graph_var_dict = {
        "loss": loss,
        "probs": probs,
        "labels": ret_labels,
        "infers": ret_infers,
        "seq_len": seq_len
    }

    task = Task("sequence_labeling", graph_var_dict,
                fluid.default_main_program(), fluid.default_startup_program())

    return task