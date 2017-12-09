import logging; logger = logging.getLogger('ctrllr.launchkey')

import re
from functools import partial

import mido
from mido import Message

SWITCH_MODE = {
	'extended': Message('note_on', note=12, velocity=127, channel=15),
	'basic': Message('note_on', note=12, velocity=0, channel=15),
}

SUBMODE_NOTE_MAP = {13: 'knobs', 14: 'sliders', 15: 'drumpads'}
def vel_to_mode(v):
	return {0: 'basic', 127: 'extended'}[v]
def bool_to_val(b):
	assert type(b) is bool
	return 127 if b else 0
def val_to_bst(v):
	return {127:'down', 0:'up'}[v]

RESET_DRUMPADLEDS = Message('control_change', control=0, value=0)
DRUMPADS = {
	'basic': [40, 41, 42, 43,    48, 49, 50, 51,
			  36, 37, 38, 39,    44, 45, 46, 47,             104, 105],
	'extended': [96,  97,  98,  99,    100, 101, 102, 103,
				 112, 113, 114, 115,   116, 117, 118, 119,   104, 120],
}
DRUMPAD_CHANNEL = {'basic': 9, 'extended': 15}

KNOBS = [21, 22, 23, 24, 25, 26, 27, 28]
SLIDERS = [41, 42, 43, 44, 45, 46, 47, 48, 7]
SBUTTONS = [51, 52, 53, 54, 55, 56, 57, 58, 59]

TRANSPORT = {112: 'rev', 113: 'fwd', 114: 'stop', 115: 'play', 116: 'loop', 117: 'rec',
				102: 'trackdown', 103: 'trackup'}

class Launchkey(object):
	@staticmethod
	def locate(devices):
		launchkey = sorted([d for d in devices
			if re.search(r'Launchkey( MK2)?', d)],
			key=lambda x: re.search(r'MIDI (\d)+', x).group(1))

		if len(launchkey) > 0:
			return tuple(launchkey)
		else:
			return None


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
		self.submodes = {'sliders': 'basic', 'knobs': 'basic', 'drumpads': 'basic'}

		# set up default empty user callbacks
		self._callbacks = dict(keyboard=lambda msg: None,
			drumpad=lambda drumpad, msg: None,
			sliders=lambda slider, value, msg: None,
			slider_buttons=lambda btn, state, msg: None,
			knobs=lambda knob, value, msg: None,
			transport=lambda btn, state, msg: None)

	def set_mode(self, mode):
		self.ports['incontrol'].send(SWITCH_MODE[mode])
		logger.debug("Sent mode switch cmd ({} -> {})".format(self.mode, mode))

	def reset_drumpadleds(self):
		logger.debug("Resetting drumpad LEDs")
		self.ports['incontrol'].send(RESET_DRUMPADLEDS)

	def set_muteled(self, on):
		self.ports['incontrol'].send(Message('control_change', channel=15,
			control=59, value=bool_to_val(on)))

	def set_drumpadled(self, led, color, flashcolor=None, pulsing=False):
		logger.debug("Setting LED {} to {}".format(led, color))

		if not color:
			color = 0

		submode = self.submodes['drumpads']

		def send_ledctrl(submode, channel, idx, val):
			if submode == 'basic' and idx in [16, 17]:
				self.ports['incontrol'].send(Message('control_change', channel=channel,
					control=DRUMPADS[submode][idx], value=val))

			self.ports['incontrol'].send(Message('note_on', channel=channel,
				note=DRUMPADS[submode][idx], velocity=val))

		if pulsing:
			assert not flashcolor
			send_ledctrl(submode, 2, led, color)

			return

		send_ledctrl(submode, 15, led, color)

		if flashcolor:
			assert not pulsing
			send_ledctrl(submode, 1, led, flashcolor)

	def rx(self, port, msg):
		# logger.debug('[{}] {}'.format(port, msg))

		if port == 'incontrol':
			self.incontrol_rx_state(msg)

		if any([self.rx_drumpads(port, msg),
			self.rx_knobs(port, msg),
			self.rx_sliders(port, msg),
			self.rx_transport(port, msg)]):
			return

		if port == 'midi':
			# fall through; if nothing handled it before it's just plain old keyboard stuff
			self._callbacks['keyboard'](msg)


	def rx_drumpads(self, port, msg):
		submode = self.submodes['drumpads']

		if msg.type == 'control_change' and submode == 'basic' \
				and msg.control in DRUMPADS[submode] and msg.channel == 0:
			dp = DRUMPADS[submode].index(msg.control)
			m = Message({127: 'note_on', 0: 'note_off'}[msg.value],
				note=DRUMPADS['extended'][dp],
				velocity=msg.value, channel=15) # normalize to extended format
			self._callbacks['drumpad'](dp, m)

			return True

		if not msg.type in ['note_on', 'note_off']:
			return False

		if msg.note in DRUMPADS[submode] and msg.channel == DRUMPAD_CHANNEL[submode]:
			dp = DRUMPADS[submode].index(msg.note)
			self._callbacks['drumpad'](dp, msg)
			return True

		return False

	def rx_knobs(self, port, msg):
		if msg.type == 'control_change' and msg.control in KNOBS:
			kidx = KNOBS.index(msg.control)
			self._callbacks['knobs'](kidx, msg.value, msg)

			return True

		return False

	def rx_sliders(self, port, msg):
		if msg.type == 'control_change':
			if msg.control in SLIDERS:
				sidx = SLIDERS.index(msg.control)
				self._callbacks['sliders'](sidx, msg.value, msg)

				return True
			elif msg.control in SBUTTONS:
				bidx = SBUTTONS.index(msg.control)
				state = val_to_bst(msg.value)
				self._callbacks['slider_buttons'](bidx, state, msg)

				return True

		return False

	def rx_transport(self, port, msg):
		if msg.type == 'control_change' and msg.control in TRANSPORT.keys():
			btn = TRANSPORT[msg.control]
			state = val_to_bst(msg.value)
			self._callbacks['transport'](btn, state, msg)

			return True

		return False

	def incontrol_rx_state(self, msg):
		if msg.type == 'note_on' and msg.channel == 15:
			if msg.note == 12:
				self.mode = vel_to_mode(msg.velocity)
				self.submodes = dict.fromkeys(self.submodes, self.mode)

				return True

			if msg.note in SUBMODE_NOTE_MAP.keys():
				submode = SUBMODE_NOTE_MAP[msg.note]
				self.submodes[submode] = vel_to_mode(msg.velocity)

				return True

		return False

	def __repr__(self):
		return '<Launchkey mode: {self.mode}, submodes: {self.submodes}>'.format(self=self)
