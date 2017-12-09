class Layer(object):
	def callbacks(self):
		return {}
	def __init__(self, controller):
		self.controller = controller
