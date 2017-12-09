from .. import Layer

class MasterVolLayer(Layer):
	def __init__(self, controller):
		self.muted = False
		self.vol = 1.0

		super().__init__(controller)

	def callbacks(self):
		return dict(slider_buttons=self.slider_buttons,
					sliders=self.sliders)

	def slider_buttons(self, btn, state, msg):
		if btn == 8 and state == 'up':
			self.muted = not self.muted
			self.controller.set_muteled(self.muted)

	def sliders(self, slider, val, msg):
		if slider == 8:
			self.vol = val/127.0
