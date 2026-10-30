"""Local, CPU-first training for NyayaLens classifiers."""

from .dataset import DatasetBundle, DatasetLabel, TrainingExample, load_lexglue_unfair_tos
from .model import UnfairToSClassifier, train_baseline

__all__ = [
    "DatasetBundle",
    "DatasetLabel",
    "TrainingExample",
    "UnfairToSClassifier",
    "load_lexglue_unfair_tos",
    "train_baseline",
]
