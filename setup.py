from setuptools import setup

setup(
	name='livemashing',
	author='Liam Marshall',
	author_email='limarshall@wisc.edu',
	version='0.1',
	license='GPLv3',

	packages=['livemashing'],
	install_requires=[
		'coloredlogs',
		'click',
		'PyYAML',

		'mido',
		'pygame'
	],

	entry_points='''
	[console_scripts]
	livemash=livemashing.cli:livemash
	'''
)
