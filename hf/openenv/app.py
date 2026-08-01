"""Transport-neutral entry point for the PelicanCanvas environment.

The core reset/step/state contract lives in pelicanbench.environments. An OpenEnv
server adapter can import this module without changing benchmark semantics.
"""
from pelicanbench.canvas import CanvasEnvironment
from pelicanbench.environments import PelicanCanvasOpenEnv

environment = PelicanCanvasOpenEnv(CanvasEnvironment())
