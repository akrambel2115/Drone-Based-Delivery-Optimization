"""Drone delivery benchmark data generator."""

from data_generator.config_loader import load_spec
from data_generator.instance_builder import build_instance

__all__ = ["build_instance", "load_spec"]
