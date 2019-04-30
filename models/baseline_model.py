# encoding: utf-8
"""
@author:  liaoxingyu
@contact: xyliao1993@qq.com
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import itertools

import torch.nn.functional as F
from torch import nn

from .resnet import ResNet


def weights_init_kaiming(m):
    classname = m.__class__.__name__
    if classname.find('Linear') != -1:
        nn.init.kaiming_normal_(m.weight, a=0, mode='fan_out')
        nn.init.constant_(m.bias, 0.0)
    elif classname.find('Conv') != -1:
        nn.init.kaiming_normal_(m.weight, a=0, mode='fan_in')
        if m.bias is not None:
            nn.init.constant_(m.bias, 0.0)
    elif classname.find('BatchNorm') != -1:
        if m.affine:
            nn.init.normal_(m.weight, 1.0, 0.02)
            nn.init.constant_(m.bias, 0.0)


def weights_init_classifier(m):
    classname = m.__class__.__name__
    if classname.find('Linear') != -1:
        nn.init.normal_(m.weight, std=0.001)
        nn.init.constant_(m.bias, 0.0)


class ResNetBuilder(nn.Module):
    in_planes = 2048

    def __init__(self, num_classes=None, last_stride=1, eval_norm=1, model_path=None):
        super().__init__()
        self.base = ResNet(last_stride)
        self.eval_norm = eval_norm
        if self.eval_norm == 1:
            print('Eval normalize before feature!!')
        else:
            print('Without eval normalize before feature!!')
        if model_path is not None:
            print('Use pretrained model initialize!!')
            self.base.load_param(model_path)
        else:
            print('Use kaiming initialize!!')
            self.base.apply(weights_init_kaiming)
            # raise ValueError('ResNet Builder must input a pretrained model path')

        self.num_classes = num_classes
        if num_classes is not None:
            self.bottleneck = nn.Sequential(
                nn.Linear(self.in_planes, 512),
                nn.BatchNorm1d(512),
                nn.LeakyReLU(0.1),
                nn.Dropout(p=0.5)
            )
            self.bottleneck.apply(weights_init_kaiming)
            self.classifier = nn.Linear(512, self.num_classes)
            self.classifier.apply(weights_init_classifier)

    def forward(self, x):
        global_feat = self.base(x)
        global_feat = F.avg_pool2d(global_feat, global_feat.shape[2:])  # (b, 2048, 1, 1)
        global_feat = global_feat.view(global_feat.shape[0], -1)
        if self.training and self.num_classes is not None:
            feat = self.bottleneck(global_feat)
            cls_score = self.classifier(feat)
            return cls_score, global_feat
        else:
            if self.eval_norm == 1:
                global_feat = F.normalize(global_feat)  # normalize feat to unit vector
            return global_feat

    def get_optim_policy(self):
        base_param_group = self.base.parameters()
        if self.num_classes is not None:
            add_param_group = itertools.chain(self.bottleneck.parameters(), self.classifier.parameters())
            return [
                {'params': base_param_group},
                {'params': add_param_group}
            ]
        else:
            return [
                {'params': base_param_group}
            ]


if __name__ == '__main__':
    net = ResNetBuilder(None)
    net.cuda()
    import torch as th
    x = th.ones(2, 3, 256, 128).cuda()
    y = net(x)
    from IPython import embed
    embed()
