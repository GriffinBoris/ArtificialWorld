import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

FPS = 24
FRAMES = 48
SRGB_LINEAR_THRESHOLD = 0.04045


def material(name, color):
	channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
	linear = [
		channel / 12.92 if channel <= SRGB_LINEAR_THRESHOLD else ((channel + 0.055) / 1.055) ** 2.4
		for channel in channels
	]
	result = bpy.data.materials.new(name)
	result.diffuse_color = (*linear, 1)
	result.use_nodes = True
	shader = result.node_tree.nodes.get('Principled BSDF')
	shader.inputs['Base Color'].default_value = (*linear, 1)
	shader.inputs['Roughness'].default_value = 0.82

	return result


def empty(name, parent=None, location=(0, 0, 0)):
	result = bpy.data.objects.new(name, None)
	bpy.context.collection.objects.link(result)
	result.parent = parent
	result.location = location

	return result


def sphere(name, location, scale, surface, parent, *, smooth=False, ico=False):
	if ico:
		bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1)
	else:
		bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10)

	result = bpy.context.object
	result.name = name
	result.parent = parent
	result.location = location
	result.scale = scale
	result.data.materials.append(surface)

	for polygon in result.data.polygons:
		polygon.use_smooth = smooth

	return result


def cylinder(name, location, radius, depth, surface, *, parent, top_radius=None):
	bpy.ops.mesh.primitive_cone_add(
		vertices=8, radius1=radius, radius2=radius if top_radius is None else top_radius, depth=depth
	)
	result = bpy.context.object
	result.name = name
	result.parent = parent
	result.location = location
	result.data.materials.append(surface)

	return result


def branch(name, a, b, radius, surface, *, parent):
	start, end = (Vector(a), Vector(b))
	result = cylinder(
		name, (start + end) / 2, radius, (end - start).length, surface, top_radius=radius * 0.7, parent=parent
	)
	result.rotation_euler = (end - start).to_track_quat('Z', 'Y').to_euler()

	return result


def smile(parent, surface):
	curve = bpy.data.curves.new('Smile curve', type='CURVE')
	curve.dimensions = '3D'
	curve.bevel_depth = 0.014
	curve.bevel_resolution = 2
	spline = curve.splines.new('POLY')
	spline.points.add(8)

	for index, point in enumerate(spline.points):
		x = -0.085 + index * 0.17 / 8
		point.co = (x, -0.374, 1.305 - 0.028 * math.sin(math.pi * index / 8), 1)

	result = bpy.data.objects.new('Smile', curve)
	bpy.context.collection.objects.link(result)
	result.parent = parent
	result.data.materials.append(surface)
	bpy.ops.object.select_all(action='DESELECT')
	result.select_set(state=True)
	bpy.context.view_layer.objects.active = result
	bpy.ops.object.convert(target='MESH')


def animate(objects):
	for clip in ('Idle', 'Walk', 'Talk'):
		for name, obj in objects.items():
			base_position = obj.location.copy()
			base_scale = obj.scale.copy()
			obj.animation_data_create()
			obj.animation_data.action = None

			for frame in range(1, FRAMES + 2, 2):
				phase = (frame - 1) / FRAMES * math.tau
				obj.location = base_position
				obj.scale = base_scale
				obj.rotation_euler = (0, 0, 0)

				if name == 'Body':
					bounce = math.sin(phase * (4 if clip == 'Walk' else 1))
					obj.location.z += (0.035 if clip == 'Walk' else 0.012) * bounce
					obj.scale.z *= 1 + 0.025 * math.sin(phase)
					obj.scale.x *= 1 - 0.012 * math.sin(phase)

				if name in ('Leg_L', 'Leg_R') and clip == 'Walk':
					obj.rotation_euler.x = 0.65 * math.sin(phase * 2) * (1 if name == 'Leg_L' else -1)

				if name in ('Arm_L', 'Arm_R'):
					side = 1 if name == 'Arm_L' else -1
					obj.rotation_euler.x = (
						(-0.55 if clip == 'Walk' else 0.15) * math.sin(phase * (2 if clip == 'Walk' else 1)) * side
					)
					obj.rotation_euler.y = side * (0.12 + (0.45 + 0.2 * math.sin(phase * 2) if clip == 'Talk' else 0))

				if name == 'Head':
					obj.rotation_euler.y = math.sin(phase) * (0.08 if clip == 'Talk' else 0.02)
					obj.rotation_euler.z = math.sin(phase) * (0.07 if clip == 'Talk' else 0.015)

				if name.startswith('Eye'):
					obj.scale.z *= 0.12 if frame in (25, 27) else 1

				for property_name in ('location', 'rotation_euler', 'scale'):
					obj.keyframe_insert(data_path=property_name, frame=frame)

			action = obj.animation_data.action
			action.name = f'{clip}_{name}'
			track = obj.animation_data.nla_tracks.new()
			track.name = clip
			strip = track.strips.new(clip, 1, action)
			strip.action_slot = obj.animation_data.action_slot
			obj.animation_data.action = None
			track.mute = clip != 'Idle'
			obj.location = base_position
			obj.scale = base_scale
			obj.rotation_euler = (0, 0, 0)


def villager(surfaces):
	root = empty('Villager')
	body = empty('Body', root)
	sphere('Shirt', (0, 0, 0.79), (0.34, 0.25, 0.36), surfaces['shirt'], body, smooth=True)
	sphere('Collar', (0, -0.035, 1.04), (0.22, 0.19, 0.08), surfaces['cream'], body, smooth=True)
	head = empty('Head', body)
	sphere('Face', (0, 0, 1.37), (0.45, 0.37, 0.4), surfaces['skin'], head, smooth=True)

	for side in (-1, 1):
		sphere('Ear', (side * 0.44, 0, 1.37), (0.085, 0.07, 0.12), surfaces['skin'], head, smooth=True)
		sphere('Cheek', (side * 0.25, -0.319, 1.31), (0.082, 0.018, 0.042), surfaces['blush'], head, smooth=True)

	eyes = {}

	for side, suffix in ((-1, 'L'), (1, 'R')):
		eye = sphere(
			f'Eye_{suffix}', (side * 0.15, -0.347, 1.45), (0.041, 0.026, 0.059), surfaces['dark'], head, smooth=True
		)
		eyes[f'Eye_{suffix}'] = eye
		sphere('Eye sparkle', (-0.24, -0.94, 0.35), (0.24, 0.2, 0.24), surfaces['cream'], eye, smooth=True)

	smile(head, surfaces['dark'])
	cylinder('Hat brim', (0, 0, 1.69), 0.46, 0.055, surfaces['hat'], parent=head)
	sphere('Soft cap', (0, 0, 1.74), (0.35, 0.3, 0.18), surfaces['hat'], head, smooth=True)
	leaf = sphere('Hat leaf', (0.05, 0, 1.95), (0.07, 0.025, 0.17), surfaces['leaf'], head, smooth=True)
	leaf.rotation_euler.y = 0.55
	parts = {'Body': body, 'Head': head, **eyes}

	for side, suffix in ((-1, 'L'), (1, 'R')):
		arm = empty(f'Arm_{suffix}', body, (side * 0.3, 0, 1.0))
		sphere('Sleeve', (side * 0.035, 0, -0.1), (0.105, 0.13, 0.17), surfaces['shirt'], arm, smooth=True)
		sphere('Hand', (side * 0.04, -0.005, -0.29), (0.09, 0.1, 0.115), surfaces['skin'], arm, smooth=True)
		leg = empty(f'Leg_{suffix}', root, (side * 0.16, 0, 0.43))
		sphere('Trouser', (0, 0, -0.115), (0.12, 0.14, 0.22), surfaces['cream'], leg, smooth=True)
		sphere('Shoe', (0, -0.06, -0.34), (0.135, 0.19, 0.09), surfaces['shoe'], leg, smooth=True)
		parts[f'Arm_{suffix}'] = arm
		parts[f'Leg_{suffix}'] = leg

	animate(parts)

	return root


def tree(surfaces, pine=False):
	root = empty('Pine' if pine else 'Tree')
	cylinder('Trunk', (0, 0, 1.6), 0.22, 3.2, surfaces['wood'], top_radius=0.16, parent=root)

	if pine:
		for index in range(3):
			cylinder(
				'Pine crown',
				(0, 0, 2.2 + index * 0.8),
				1.3 - index * 0.27,
				1.8,
				surfaces['leaf' if index % 2 else 'leaf_light'],
				top_radius=0,
				parent=root,
			)
	else:
		for index, (x, y, z, size) in enumerate(
			((-0.65, 0, 3.15, 1.15), (0.65, 0.05, 3.3, 1.3), (0, 0.45, 3.4, 1.15), (0, -0.2, 4.05, 1.25))
		):
			sphere(
				'Rounded crown',
				(x, y, z),
				(size, size * 0.9, size * 0.85),
				surfaces['leaf' if index % 2 else 'leaf_light'],
				root,
				ico=True,
			)

	return root


def rock(surfaces):
	root = empty('Rock')

	for index, (location, scale) in enumerate(
		(
			((0, 0, 0.3), (0.75, 0.65, 0.6)),
			((0.65, 0.05, 0.17), (0.4, 0.42, 0.35)),
			((-0.35, 0.4, 0.15), (0.4, 0.35, 0.3)),
		)
	):
		piece = sphere('Stone', location, scale, surfaces['stone' if index % 2 else 'stone_light'], root, ico=True)
		piece.rotation_euler = (0.1 * index, 0.2, index * 0.7)

	return root


def bush(surfaces):
	root = empty('Berry bush')

	for x, y, z in ((-0.28, 0, 0.4), (0.3, 0.08, 0.45), (0, 0, 0.7)):
		sphere('Bush leaves', (x, y, z), (0.5, 0.45, 0.45), surfaces['leaf'], root, ico=True)

	for index in range(8):
		angle = index * math.tau / 8
		sphere(
			'Berry',
			(math.cos(angle) * 0.47, math.sin(angle) * 0.42, 0.55 + index % 3 * 0.14),
			(0.12, 0.12, 0.12),
			surfaces['berry'],
			root,
			smooth=True,
			ico=True,
		)

	return root


def reeds(surfaces):
	root = empty('Reeds')

	for index in range(7):
		angle = index * 2.4
		stem = cylinder(
			'Fiber leaf',
			(math.cos(angle) * 0.2, math.sin(angle) * 0.2, 0.35),
			0.035,
			0.7 + index % 3 * 0.15,
			surfaces['leaf_light'],
			top_radius=0,
			parent=root,
		)
		stem.rotation_euler = (math.sin(angle) * 0.3, math.cos(angle) * 0.3, 0)

	return root


def flowers(surfaces):
	root = empty('Wildflowers')

	for index in range(5):
		x, y = (math.cos(index * 2.4) * 0.3, math.sin(index * 2.4) * 0.3)
		stem_height = 0.16 + index % 3 * 0.07
		cylinder('Stem', (x, y, stem_height / 2), 0.012, stem_height, surfaces['leaf'], parent=root)

		for petal in range(5):
			angle = petal * math.tau / 5
			sphere(
				'Petal',
				(x + math.cos(angle) * 0.055, y + math.sin(angle) * 0.055, stem_height),
				(0.052, 0.045, 0.026),
				surfaces['pink' if index % 2 else 'cream'],
				root,
				ico=True,
			)

		sphere('Flower heart', (x, y, stem_height + 0.01), (0.035, 0.035, 0.025), surfaces['hat'], root, ico=True)

	return root


def fallen_branch(surfaces):
	root = empty('Branch')
	branch('Wood', (0, 0, 0), (0, 0, 1), 0.055, surfaces['wood'], parent=root)
	branch('Twig', (0, 0, 0.5), (0.28, 0, 0.85), 0.025, surfaces['wood'], parent=root)

	return root


def cloud(surfaces):
	root = empty('Cloud')
	pieces = []

	for location, scale in (
		((-1.7, 0, 0.7), (1.5, 1.1, 0.85)),
		((0, 0, 1.0), (2.0, 1.4, 1.1)),
		((1.7, 0.1, 0.8), (1.5, 1.1, 0.85)),
		((-0.6, 0, 1.8), (1.35, 1.1, 1.1)),
		((0.9, 0.1, 1.5), (1.4, 1, 0.95)),
	):
		pieces.append(sphere('Cloud puff', location, scale, surfaces['cloud'], root, smooth=True, ico=True))

	bpy.ops.object.select_all(action='DESELECT')

	for piece in pieces:
		piece.select_set(state=True)

	bpy.context.view_layer.objects.active = pieces[0]
	bpy.ops.object.join()

	return root


def seed(surfaces):
	root = empty('Seed')
	sphere('Seed body', (0, 0, 0.12), (0.13, 0.1, 0.12), surfaces['wood'], root, smooth=True, ico=True)
	sphere('Seed leaf', (0.04, 0, 0.25), (0.09, 0.025, 0.13), surfaces['leaf'], root, smooth=True, ico=True)

	return root


def sapling(surfaces):
	root = empty('Sapling')
	cylinder('Young stem', (0, 0, 0.32), 0.035, 0.64, surfaces['wood'], parent=root)

	for side in (-1, 1):
		leaf = sphere(
			'Young leaves',
			(side * 0.12, 0, 0.5),
			(0.19, 0.07, 0.09),
			surfaces['leaf_light'],
			root,
			smooth=True,
			ico=True,
		)
		leaf.rotation_euler.y = side * -0.5

	sphere('New leaf', (0, 0, 0.7), (0.1, 0.05, 0.16), surfaces['leaf'], root, smooth=True, ico=True)

	return root


def stump(surfaces):
	root = empty('Stump')
	cylinder('Bark', (0, 0, 0.2), 0.24, 0.4, surfaces['wood'], top_radius=0.2, parent=root)
	cylinder('Cut face', (0, 0, 0.405), 0.185, 0.012, surfaces['cream'], parent=root)
	cylinder('Growth ring', (0, 0, 0.413), 0.12, 0.007, surfaces['hat'], parent=root)

	return root


def export_asset(root, path):
	bpy.ops.object.select_all(action='DESELECT')
	root.select_set(state=True)

	for obj in root.children_recursive:
		obj.select_set(state=True)

	bpy.context.scene.frame_set(1)
	bpy.ops.export_scene.gltf(
		filepath=str(path),
		export_format='GLB',
		use_selection=True,
		export_animations=True,
		export_animation_mode='NLA_TRACKS',
		export_merge_animation='NLA_TRACK',
		export_yup=True,
	)


def portrait(root, path):
	bpy.context.scene.render.engine = 'CYCLES'
	bpy.context.scene.cycles.samples = 24
	bpy.context.scene.render.resolution_x = 256
	bpy.context.scene.render.resolution_y = 256
	bpy.context.scene.render.resolution_percentage = 100
	bpy.context.scene.render.film_transparent = True
	bpy.context.scene.world.color = (0.3, 0.3, 0.3)

	for other in bpy.context.scene.objects:
		other.hide_render = other != root and other not in root.children_recursive

	bpy.ops.object.camera_add(location=(2.6, -5.5, 2.7))
	camera = bpy.context.object
	camera.rotation_euler = (Vector((0, 0, 1.15)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
	camera.data.type = 'ORTHO'
	camera.data.ortho_scale = 2.4
	bpy.context.scene.camera = camera
	bpy.ops.object.light_add(type='AREA', location=(1, -3, 5))
	bpy.context.object.data.energy = 400
	bpy.context.object.data.shape = 'DISK'
	bpy.context.object.data.size = 4
	bpy.context.object.rotation_euler = (
		(Vector((0, 0, 1)) - bpy.context.object.location).to_track_quat('-Z', 'Y').to_euler()
	)
	bpy.context.scene.render.filepath = str(path)
	bpy.ops.render.render(write_still=True)


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('--output', type=Path, required=True)
	parser.add_argument('--source', type=Path, required=True)
	options = parser.parse_args(sys.argv[sys.argv.index('--') + 1 :])
	options.output.mkdir(parents=True, exist_ok=True)
	options.source.parent.mkdir(parents=True, exist_ok=True)
	bpy.ops.object.select_all(action='SELECT')
	bpy.ops.object.delete(use_global=False)
	bpy.context.scene.render.fps = FPS
	bpy.context.scene.frame_start = 1
	bpy.context.scene.frame_end = FRAMES + 1
	surfaces = {
		name: material(name, color)
		for name, color in {
			'skin': '#ffe0bc',
			'blush': '#f5a4a9',
			'dark': '#443547',
			'shirt': '#7ccab1',
			'cream': '#fff3d4',
			'shoe': '#b27b65',
			'hat': '#f4cc70',
			'wood': '#ad7851',
			'leaf': '#61b87b',
			'leaf_light': '#96d27f',
			'stone': '#899fb6',
			'stone_light': '#b3c2cc',
			'berry': '#ed7e95',
			'pink': '#e9a8d0',
			'cloud': '#fffdf6',
		}.items()
	}
	roots = {
		'villager': villager(surfaces),
		'tree': tree(surfaces),
		'pine': tree(surfaces, pine=True),
		'rock': rock(surfaces),
		'berry-bush': bush(surfaces),
		'reeds': reeds(surfaces),
		'flowers': flowers(surfaces),
		'branch': fallen_branch(surfaces),
		'cloud': cloud(surfaces),
		'seed': seed(surfaces),
		'sapling': sapling(surfaces),
		'stump': stump(surfaces),
	}

	for name, root in roots.items():
		export_asset(root, options.output / f'{name}.glb')

	portrait(roots['villager'], options.output / 'villager-portrait.png')

	for index, root in enumerate(roots.values()):
		root.location.x = index * 8

	for obj in bpy.context.scene.objects:
		obj.hide_render = False

	bpy.ops.wm.save_as_mainfile(filepath=str(options.source.resolve()))


if __name__ == '__main__':
	main()
