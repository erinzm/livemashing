import sys
import time
import random

import logging

import click
import yaml

import pygame
import mido

from .util.midi import locate_launchkey
from .util import locate_config
from .controllers import Launchkey
from .ui import colors as clrs

@click.command()
@click.option('--config', 'config_path', default=locate_config())
def livemash(config_path):
	logging.basicConfig(level=logging.DEBUG)

	logging.info("Loading config from {}".format(config_path))
	with open(config_path) as f:
		config = yaml.safe_load(f) or {}
	logging.info("Successfully loaded config.")

	_backend = config.get('midi', {}).get('backend') or 'mido.backends.rtmidi'
	logging.info("Setting mido backend to {}".format(_backend))
	mido.set_backend(_backend)

	midi_ins = mido.get_input_names()
	logging.info("Found midi inputs: {}".format(midi_ins))

	launchkey_portnames = locate_launchkey(midi_ins)
	if not launchkey_portnames:
		logging.error("Launchkey not found!"); sys.exit()
	logging.info("Found Launchkey ports: {}".format(launchkey_portnames))

	logging.info("Opening Launchkey")
	launchkey = Launchkey(launchkey_portnames)
	launchkey.set_mode('extended')

	pygame.init()
	size = width, height = 640, 480
	screen = pygame.display.set_mode(size)

	while True:
	    # -- handle events
		for event in pygame.event.get():
			if event.type == pygame.QUIT: sys.exit()

		# -- draw
		screen.fill(clrs.navy)

		pygame.display.flip()
