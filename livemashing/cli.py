import sys
import time
import random
import importlib
import logging
from collections import defaultdict

import click
import yaml

import pygame
import mido

from .util import locate_config
from .controllers import CONTROLLERDB
from .ui import colors as clrs

@click.command()
@click.option('--config', 'config_path', default=locate_config())
def livemash(config_path):
	logging.basicConfig(level=logging.DEBUG)

	# -- load config
	logging.info("Attempting config load from `{}`...".format(config_path))
	with open(config_path) as f:
		config = yaml.safe_load(f) or {}
	logging.info("Successfully loaded config.")

	# -- midi startup, enumeration
	_backend = config.get('midi', {}).get('backend') or 'mido.backends.rtmidi'
	logging.info("Setting mido backend to `{}`".format(_backend))
	mido.set_backend(_backend)

	midi_ios = mido.get_ioport_names()
	logging.info("Found {} midi i/os:".format(len(midi_ios)))
	for m in midi_ios: logging.info("\t{}".format(m))

	# -- set up controllers
	controllers = []
	for ctrl_conf in config.get('controllers', []):
		shortname = next(iter(ctrl_conf))
		cclass = CONTROLLERDB[shortname]
		logging.info("Adding controller: {cclass.__module__}.{cclass.__name__}".format(cclass=cclass))

		portnames = cclass.locate(midi_ios)
		logging.debug("\tFound MIDI I/Os belonging to controller:")
		for p in portnames: logging.debug("\t\t{}".format(p))

		logging.debug("\t Instantiating controller")
		controller = cclass(portnames)

		logging.debug("\t Running startup config")
		if hasattr(controller, 'set_mode'):
			controller.set_mode(ctrl_conf['startup_mode'])

		layers_mod = getattr(__import__('livemashing.layers', fromlist=[shortname]), shortname)
		callbacks = defaultdict(lambda: [])
		for layername in ctrl_conf.get('layers', []):
			logging.debug("\t Attaching layer `{}`".format(layername))
			layer = layers_mod.LAYERS[layername](controller)
			for k, v in layer.callbacks().items():
				callbacks[k].append(v)

		# multi-callback dispatcher (ugly af)
		for n, functions in callbacks.items():
			controller._callbacks[n] = \
				lambda *args, functions=functions, **kwargs: \
					[f(*args, **kwargs) for f in functions]

		# controller._callbacks['slider_buttons'] = lambda *args: print('sb')
		# controller._callbacks['slider'] = lambda *args: print('s')

		controller._callbacks['slider_buttons'](None, None, None)

		controllers.append(controller)


	logging.info("Entering main loop")
	while True:
		time.sleep(0.5)
