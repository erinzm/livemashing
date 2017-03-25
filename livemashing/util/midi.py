import re

def locate_launchkey(devices):
	launchkey = sorted([d for d in devices
		if re.search(r'Launchkey( MK2)?', d)],
		key=lambda x: re.search(r'MIDI (\d)+', x).group(1))
	return tuple(launchkey)
