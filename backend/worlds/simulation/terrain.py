import math

from worlds.simulation.contracts import CURRENT_RULES_VERSION


def terrain_height(x, y, seed=42, rules_version=CURRENT_RULES_VERSION):
	phase = (seed % 997) / 997
	hills = 3 * math.sin(x / 70 + phase) * math.cos(y / 90) + 2 * math.sin((x + y) / 130)

	if rules_version == 1:
		lake = 18 * math.exp(-((x - 110) ** 2 + (y - 80) ** 2) / 10000)

		return 8 + hills - lake

	stream_x = 29 + 8 * math.sin(y / 45 + phase)
	stream = 13 * math.exp(-(((x - stream_x) / 8) ** 2))
	lake = 19 * math.exp(-(((x - 65) / 32) ** 2) - ((y - 48) / 30) ** 2)
	pond = 13 * math.exp(-(((x + 76) / 24) ** 2) - ((y - 42) / 22) ** 2)
	peaks = 38 * math.exp(-(((x + 115) / 65) ** 2) - ((y - 160) / 70) ** 2) + 55 * math.exp(
		-(((x - 170) / 85) ** 2) - ((y - 200) / 75) ** 2
	)
	peaks += 24 * math.exp(-(((x + 180) / 90) ** 2) - ((y + 130) / 90) ** 2)
	facets = 1 + 0.15 * math.sin(x / 14 + phase) * math.cos(y / 17)

	return 8 + hills + peaks * facets - max(stream, lake, pond)


def terrain_resolution(config):
	return 64 if config.rules_version == 1 else 128


def terrain_grid(config):
	resolution = terrain_resolution(config)
	half = config.size / 2

	return [
		[
			terrain_height(
				-half + x * config.size / resolution,
				-half + y * config.size / resolution,
				config.seed,
				config.rules_version,
			)
			for x in range(resolution + 1)
		]
		for y in range(resolution + 1)
	]


def surface_height(x, y, config):

	resolution = terrain_resolution(config)
	spacing = config.size / resolution
	u = max(0, min(resolution - 0.000001, (x / config.size + 0.5) * resolution))
	v = max(0, min(resolution - 0.000001, (y / config.size + 0.5) * resolution))
	column, row = math.floor(u), math.floor(v)
	fx, fy = u - column, v - row
	x0, y0 = -config.size / 2 + column * spacing, -config.size / 2 + row * spacing
	a, b, c, d = [
		terrain_height(xx, yy, config.seed, config.rules_version)
		for xx, yy in ((x0, y0), (x0 + spacing, y0), (x0, y0 + spacing), (x0 + spacing, y0 + spacing))
	]

	return a + (b - a) * fx + (c - a) * fy if fx + fy <= 1 else d + (c - d) * (1 - fx) + (b - d) * (1 - fy)
