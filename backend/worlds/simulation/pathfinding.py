import heapq
import math

from panda3d.core import Quat, Vec3
from worlds.simulation.terrain import surface_height

GRID_SPACING = 1.0
OBSTACLE_BIN_SIZE = 4
MAX_SEARCH_NODES = 50000
MAX_WALK_SLOPE = 0.8
PATH_CLEARANCE = 0.25
SEGMENT_SPACING = 0.25
NEIGHBORS = ((-1, 0), (0, -1), (0, 1), (1, 0), (-1, -1), (-1, 1), (1, -1), (1, 1))


class PathNotFound(ValueError):
	pass


class RoutePlanner:
	def __init__(self, state, actor_id):
		self.state = state
		self.body = state.entity(actor_id)
		self.clearance = max(self.body.dimensions[:2]) / 2 + PATH_CLEARANCE
		self.limit = state.config.size / 2 - self.clearance
		self.heights = {}
		self.obstacles = {}
		excluded = {actor_id, *state.inhabitant(actor_id).held_ids}

		for entity in state.entities:
			if entity.id in excluded:
				continue

			rotation = Quat(*entity.rotation)
			axes = [
				rotation.xform(
					Vec3(*(size / 2 if index == axis else 0 for index, size in enumerate(entity.dimensions)))
				)
				for axis in range(3)
			]
			extents = [sum(abs(axis[index]) for axis in axes) for index in range(3)]
			low = tuple(center - extent for center, extent in zip(entity.position, extents, strict=True))
			high = tuple(center + extent for center, extent in zip(entity.position, extents, strict=True))

			for x in range(
				math.floor((low[0] - self.clearance) / OBSTACLE_BIN_SIZE),
				math.floor((high[0] + self.clearance) / OBSTACLE_BIN_SIZE) + 1,
			):
				for y in range(
					math.floor((low[1] - self.clearance) / OBSTACLE_BIN_SIZE),
					math.floor((high[1] + self.clearance) / OBSTACLE_BIN_SIZE) + 1,
				):
					self.obstacles.setdefault((x, y), []).append((low, high))

	def height(self, point):
		if point not in self.heights:
			self.heights[point] = surface_height(*point, self.state.config)

		return self.heights[point]

	def walkable(self, point, clearance=None):
		x, y = point
		clearance = self.clearance if clearance is None else clearance

		if abs(x) > self.limit or abs(y) > self.limit:
			return False

		ground = self.height(point)

		if ground < self.state.config.water_level - self.body.dimensions[2] / 4:
			return False

		for low, high in self.obstacles.get((math.floor(x / OBSTACLE_BIN_SIZE), math.floor(y / OBSTACLE_BIN_SIZE)), ()):
			if high[2] < ground + 0.15 or low[2] > ground + self.body.dimensions[2]:
				continue

			if low[0] - clearance <= x <= high[0] + clearance and low[1] - clearance <= y <= high[1] + clearance:
				return False

		return True

	def clear_segment(self, start, end, escaping=False):
		length = math.dist(start, end)
		steps = max(1, math.ceil(length / SEGMENT_SPACING))
		previous = start

		for index in range(1, steps + 1):
			point = tuple(a + (b - a) * index / steps for a, b in zip(start, end, strict=True))

			clearance = (
				min(self.clearance, max(self.body.dimensions[:2]) / 2 - 0.02 + math.dist(start, point))
				if escaping
				else self.clearance
			)

			if not self.walkable(point, clearance):
				return False

			if abs(self.height(point) - self.height(previous)) > MAX_WALK_SLOPE * math.dist(previous, point) + 1e-6:
				return False

			previous = point

		return True

	def route(self, destination):
		start, goal = self.body.position[:2], tuple(destination[:2])

		if not self.walkable(goal):
			raise PathNotFound('The destination is blocked, in deep water, or outside walking bounds.')

		if self.clear_segment(start, goal, escaping=True):
			return [self.surface_point(goal)]

		origin = tuple(round(value / GRID_SPACING) for value in start)
		frontier, costs, parents = [], {}, {}

		for dx in range(-1, 2):
			for dy in range(-1, 2):
				node = origin[0] + dx, origin[1] + dy
				point = self.grid_point(node)

				if self.walkable(point) and self.clear_segment(start, point, escaping=True):
					costs[node] = math.dist(start, point)
					parents[node] = None
					heapq.heappush(frontier, (costs[node] + math.dist(point, goal), costs[node], node))

		visited = 0

		while frontier and visited < MAX_SEARCH_NODES:
			_, cost, node = heapq.heappop(frontier)

			if cost != costs[node]:
				continue

			visited += 1
			point = self.grid_point(node)

			if math.dist(point, goal) <= GRID_SPACING * 2 and self.clear_segment(point, goal):
				points = [goal, point]

				while parents[node] is not None:
					node = parents[node]
					points.append(self.grid_point(node))

				points.append(start)

				return self.smooth(list(reversed(points)))

			for dx, dy in NEIGHBORS:
				neighbor = node[0] + dx, node[1] + dy
				target = self.grid_point(neighbor)

				if not self.walkable(target):
					continue

				if (
					dx
					and dy
					and (
						not self.walkable(self.grid_point((node[0] + dx, node[1])))
						or not self.walkable(self.grid_point((node[0], node[1] + dy)))
					)
				):
					continue

				if not self.clear_segment(point, target):
					continue

				next_cost = cost + math.dist(point, target)

				if next_cost >= costs.get(neighbor, math.inf):
					continue

				costs[neighbor], parents[neighbor] = next_cost, node
				heapq.heappush(frontier, (next_cost + math.dist(target, goal), next_cost, neighbor))

		raise PathNotFound('No walkable route was found within the navigation search budget.')

	def grid_point(self, node):
		return tuple(value * GRID_SPACING for value in node)

	def surface_point(self, point):
		return *point, self.height(point) + self.body.dimensions[2] / 2

	def smooth(self, points):
		result = []
		anchor = 0

		while anchor < len(points) - 1:
			end = len(points) - 1

			while end > anchor + 1 and not self.clear_segment(points[anchor], points[end], escaping=anchor == 0):
				end -= 1

			result.append(self.surface_point(points[end]))
			anchor = end

		return result
