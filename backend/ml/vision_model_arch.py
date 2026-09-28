"""
PlantPathologyNet — MobileNetV2 backbone fine-tuned for leaf disease diagnosis.
Trained on the open-source PlantDoc dataset when available.
"""
from __future__ import annotations

import torch
import torch.nn as nn
from torchvision import models


class ResidualBlock(nn.Module):
    """Kept for backward compatibility with older custom-CNN checkpoints."""

    def __init__(self, channels: int):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(channels)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(channels)

    def forward(self, x):
        residual = x
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += residual
        return self.relu(out)


class PlantPathologyNet(nn.Module):
    """
    Transfer-learning vision classifier for plant leaf pathology.
    Uses ImageNet-pretrained MobileNetV2 with a custom disease head.
    """

    def __init__(self, num_classes: int = 31, pretrained: bool = True):
        super().__init__()
        self.num_classes = num_classes
        weights = models.MobileNet_V2_Weights.IMAGENET1K_V1 if pretrained else None
        try:
            backbone = models.mobilenet_v2(weights=weights)
        except Exception:
            backbone = models.mobilenet_v2(weights=None)

        in_features = backbone.classifier[1].in_features
        backbone.classifier = nn.Sequential(
            nn.Dropout(p=0.3),
            nn.Linear(in_features, num_classes),
        )
        self.backbone = backbone

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.backbone(x)
