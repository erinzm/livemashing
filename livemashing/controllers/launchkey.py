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
def bool_to_val(b):
	assert type(b) is bool
	return 127 if b else 0

RESET_DRUMPADLEDS = Message('control_change', control=0, value=0)
DRUMPADS = {
	'basic': [40, 41, 42, 43,    48, 49, 50, 51,
			  36, 37, 38, 39,    44, 45, 46, 47],
	'extended': [96,  97,  98,  99,    100, 101, 102, 103,
				 112, 113, 114, 115,   116, 117, 118, 119],
}
DRUMPAD_CHANNEL = {'basic': 9, 'extended': 15}

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
		self.set_mode('basic')
		self.submodes = {'sliders': 'basic', 'pots': 'basic', 'drumpads': 'basic'}

	def set_mode(self, mode):
		self.ports['incontrol'].send(SWITCH_MODE[mode])
		logger.debug("Sent mode switch cmd ({} -> {})".format(self.mode, mode))

	def reset_drumpadleds(self):
		logger.debug("Resetting drumpad LEDs")
		self.ports['incontrol'].send(RESET_DRUMPADLEDS)

	def set_muteled(self, on):
		self.ports['incontrol'].send(Message('control_change', channel=15,
			control=59, value=bool_to_val(on)))

	def set_drumpadled(self, led, color):
		if not color:
			color = 0

		submode = self.submodes['drumpads']

		self.ports['incontrol'].send(Message('note_on', channel=15,
			note=DRUMPADS[submode][led], velocity=color))

	def rx(self, port, msg):
		# logger.debug('[{}] {}'.format(port, msg))

		if port == 'incontrol':
			self.incontrol_rx_state(msg)

		self.rx_drumpads(port, msg)

		if port == 'midi':
			##
			# temporary test code; replace with real layer hooks later
			if msg.type == 'note_on' and msg.channel==0:
				if msg.note == 48:
					self.set_mode('basic')
				elif msg.note == 49:
					self.set_mode('extended')

	def rx_drumpads(self, port, msg):
		submode = self.submodes['drumpads']

		if msg.note in DRUMPADS[submode] and msg.channel == DRUMPAD_CHANNEL[submode]:
			dp = DRUMPADS[submode].index(msg.note)
			print(msg, dp)
			self.set_drumpadled(dp, msg.velocity)

	def incontrol_rx_state(self, msg):
		if msg.type == 'note_on' and msg.channel == 15:
			if msg.note == 12:
				self.mode = vel_to_mode(msg.velocity)
				self.submodes = dict.fromkeys(self.submodes, self.mode)

			if msg.note in SUBMODE_NOTE_MAP.keys():
				submode = SUBMODE_NOTE_MAP[msg.note]
				self.submodes[submode] = vel_to_mode(msg.velocity)

	def __repr__(self):
		return '<Launchkey mode: {self.mode}, submodes: {self.submodes}>'.format(self=self)
