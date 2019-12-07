import torch
import torch.nn as nn
import torch.nn.functional as F
from ..layers.conv_module import Separable_Conv, Convolutional


class Upsample(nn.Module):
    def __init__(self, scale_factor=1, mode='nearest'):
        super(Upsample, self).__init__()
        self.scale_factor = scale_factor
        self.mode = mode

    def forward(self, x):
        return F.interpolate(x, scale_factor=self.scale_factor, mode=self.mode)


class Route(nn.Module):
    def __init__(self):
        super(Route, self).__init__()

    def forward(self, x1, x2):
        """
        x1 means previous output; x2 means current output
        """
        out = torch.cat((x2, x1), dim=1)
        return out


class FPN_YOLOV3(nn.Module):
    """
    FPN for yolov3, and is different from original FPN or retinanet' FPN.
    """
    def __init__(self, fileters_in, fileters_out):
        super(FPN_YOLOV3, self).__init__()

        fi_0, fi_1, fi_2 = fileters_in
        fo_0, fo_1, fo_2 = fileters_out

        # large
        self.__conv_set_0 = nn.Sequential(
            Separable_Conv(filters_in=fi_0, filters_out=512, stride=1),
            Separable_Conv(filters_in=512, filters_out=1024, stride=1),
            Separable_Conv(filters_in=1024, filters_out=512, stride=1),
            Separable_Conv(filters_in=512, filters_out=1024, stride=1),
            Separable_Conv(filters_in=1024, filters_out=512, stride=1),
        )
        self.__conv0_0 = Separable_Conv(filters_in=512, filters_out=1024, stride=1)
        self.__conv0_1 = Convolutional(filters_in=1024, filters_out=fo_0, kernel_size=1,
                                       stride=1, pad=0)


        self.__conv0 = Separable_Conv(filters_in=512, filters_out=256, stride=1)
        self.__upsample0 = Upsample(scale_factor=2)
        self.__route0 = Route()

        # medium
        self.__conv_set_1 = nn.Sequential(
            Separable_Conv(filters_in=fi_1 + 256, filters_out=256, stride=1),
            Separable_Conv(filters_in=256, filters_out=512, stride=1),
            Separable_Conv(filters_in=512, filters_out=256, stride=1),
            Separable_Conv(filters_in=256, filters_out=512, stride=1),
            Separable_Conv(filters_in=512, filters_out=256, stride=1),
        )
        self.__conv1_0 = Separable_Conv(filters_in=256, filters_out=512, stride=1)
        self.__conv1_1 = Convolutional(filters_in=512, filters_out=fo_1, kernel_size=1,
                                       stride=1, pad=0)


        self.__conv1 = Separable_Conv(filters_in=256, filters_out=128, stride=1)
        self.__upsample1 = Upsample(scale_factor=2)
        self.__route1 = Route()

        # small
        self.__conv_set_2 = nn.Sequential(
            Separable_Conv(filters_in=fi_2 + 128, filters_out=128, stride=1),
            Separable_Conv(filters_in=128, filters_out=256, stride=1),
            Separable_Conv(filters_in=256, filters_out=128, stride=1),
            Separable_Conv(filters_in=128, filters_out=256, stride=1),
            Separable_Conv(filters_in=256, filters_out=128, stride=1),
        )
        self.__conv2_0 = Separable_Conv(filters_in=128, filters_out=256, stride=1)
        self.__conv2_1 = Convolutional(filters_in=256, filters_out=fo_2, kernel_size=1,
                                       stride=1, pad=0)

        self.__initialize_weights()


    def __initialize_weights(self):
        print("**" * 10, "Initing FPN_YOLOV3 weights", "**" * 10)

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                m.weight.data.normal_(0, 0.01)
                if m.bias is not None:
                    m.bias.data.zero_()

                print("initing {}".format(m))
            elif isinstance(m, nn.BatchNorm2d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()

                print("initing {}".format(m))
            elif isinstance(m, nn.Linear):
                m.weight.data.normal_(0, 0.01)
                m.bias.data.zero_()
                print("initing {}".format(m))


    def forward(self, x0, x1, x2):  # large, medium, small
        # large
        r0 = self.__conv_set_0(x0)
        out0 = self.__conv0_0(r0)
        out0 = self.__conv0_1(out0)

        # medium
        r1 = self.__conv0(r0)
        r1 = self.__upsample0(r1)
        x1 = self.__route0(x1, r1)
        r1 = self.__conv_set_1(x1)
        out1 = self.__conv1_0(r1)
        out1 = self.__conv1_1(out1)

        # small
        r2 = self.__conv1(r1)
        r2 = self.__upsample1(r2)
        x2 = self.__route1(x2, r2)
        r2 = self.__conv_set_2(x2)
        out2 = self.__conv2_0(r2)
        out2 = self.__conv2_1(out2)

        return out2, out1, out0  # small, medium, large