import logging; logger = logging.getLogger('ctrllr.launchkey')

from functools import partial

import mido
from mido import Message

SWITCH_MODE = {
	'extended': Message('note_on', note=12, velocity=127, channel=15),
	'basic': Message('note_on', note=12, velocity=0, channel=15),
}

SUBMODE_NOTE_MAP = {13: 'pots', 14: 'sliders', 15: 'drumpads'}
def vel_to_mode(v):
	return {0: 'basic', 127: 'extended'}[v]

class Launchkey(object):
	def __init__(self, ports):
		# check if we were passed pre-opened mido ports or just portnames
		if all([type(p) is str for p in ports]):
			logger.debug("Launchkey.__init__ provided with str portnames; opening them")
			_ports = [mido.open_ioport(p) for p in ports]
			self.ports = dict(midi=_ports[0], incontrol=_ports[1])
		else:
			self.ports = dict(midi=ports[0], incontrol=ports[1])

		self.ports['midi'].input.callback = partial(self.rx, 'midi')
		self.ports['incontrol'].input.callback = partial(self.rx, 'incontrol')

		# force the controller to basic mode
		self.mode = None
		self.setMode('basic')
		self.submodes = {'sliders': 'basic', 'pots': 'basic', 'drumpads': 'basic'}

	def setMode(self, mode):
		self.ports['incontrol'].send(SWITCH_MODE[mode])
		logger.debug("Sent mode switch cmd ({} -> {})".format(self.mode, mode))

	def rx(self, port, msg):
		# logger.debug('[{}] {}'.format(port, msg))

		# dispatch messages
		if port == 'incontrol':
			self.incontrol_rx(msg)
		if port == 'midi':
			##
			# temporary test code; replace with real layer hooks later
			if msg.type == 'note_on':
				if msg.note == 48:
					self.setMode('basic')
				elif msg.note == 49:
					self.setMode('extended')

	def incontrol_rx(self, msg):
		if msg.type == 'note_on' and msg.channel == 15:
			if msg.note == 12:
				self.mode = vel_to_mode(msg.velocity)
				self.submodes = dict.fromkeys(self.submodes, self.mode)

			if msg.note in SUBMODE_NOTE_MAP.keys():
				submode = SUBMODE_NOTE_MAP[msg.note]
				self.submodes[submode] = vel_to_mode(msg.velocity)

			print(self.mode, self.submodes)

	def __repr__(self):
		return '<Launchkey mode: {self.mode}, ports: {self.ports}>'.format(self=self)
