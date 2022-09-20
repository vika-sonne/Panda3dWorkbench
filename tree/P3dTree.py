'''
Created on 11.12.2010
Based on Kwasi Mensah's (kmensah@andrew.cmu.edu)
"The Fractal Plants Sample Program" from 8/05/2005
@author: Praios (Jan Brohl)
@license: BSD-license
Quat-patch and improved drawBody by Craig Macomber

Copyright (c) 2012, Jan Brohl
All rights reserved.

Redistribution and use in source and binary forms,
with or without modification,
are permitted provided that the following conditions are met:

	Redistributions of source code must retain the above copyright notice,
	this list of conditions and the following disclaimer.

	Redistributions in binary form must reproduce the above copyright notice,
	this list of conditions and the following disclaimer in the documentation
	and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE
GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''

# python imports
from typing import Iterable, Iterator, Optional, List, Tuple, NamedTuple, Callable
import math
import random
from os import path
from sys import path as search_paths

# Panda3D imports
from panda3d.core import (Mat4, Vec2, Vec3, Vec4, Point3, Quat, Geom, GeomNode, Texture, TextureStage,
	GeomVertexWriter, GeomTristrips, GeomVertexRewriter, GeomVertexData, GeomVertexFormat,
	CollisionNode, CollisionTube, TransformState, NodePath, PNMImage, ShaderTerrainMesh, Shader, AmbientLight,
	TextNode, WindowProperties, PandaSystem)
from direct.gui.OnscreenText import OnscreenText

# Workbench imports
from FractalBase import FractalBase
module_path = path.dirname(path.abspath(__file__))
search_paths.insert(0, path.abspath(path.join(module_path, '../lib')))
from TextureProps import TextureProps


class FractalTree(NodePath, FractalBase):
	'''
	Base class for fractal trees
	'''

	def __init__(self, bark_texture, leaf_np, root: FractalBase.BranchProps):
		super().__init__('Tree Holder')
		FractalBase.__init__(self, root)
		self.num_primitives = 0
		self.leaf_np = leaf_np
		self.bark_texture = bark_texture
		self.bodies_np = NodePath('Bodies')
		self.leaves_np = NodePath('Leaves')
		self.collision_np = self.attach_new_node(CollisionNode('Collision'))
		self.bodydata = GeomVertexData('body vertices',
									   GeomVertexFormat.getV3n3t2(),
									   Geom.UHStatic)
		self.collision_np.show()
		self.bark_ts = TextureStage('bark_ts')
		self.bodies_np.set_texture(self.bark_ts, bark_texture)
		self.collision_np.reparent_to(self)
		self.bodies_np.reparent_to(self)
		self.leaves_np.reparent_to(self)

	def get_static(self) -> NodePath:
		'makes a flattened version of the tree for faster rendering'
		np = NodePath(self.node().copySubgraph())
		np.flattenStrong()
		return np

	def make_collision(self, pos: Vec3, new_pos: Vec3, radius: float) -> None:
		'''
		make a collision tube for the given stem-parameters
		'''
		tube = CollisionTube(Point3(pos), Point3(new_pos), radius)
		self.collision_np.node().addSolid(tube)

	def draw_branch(self, props: FractalBase.BranchProps, num_side_slices = 12) -> None:
		'''draws the body of the tree as cylinder
		This draws a ring of vertices and connects the rings with triangles to from the body.

		props -:- should have child branches
		'''

		if not props.branches:
			return

		# print(f'draw_branch: {props}')
		def add_branch(branch_props, child_branch_props):
			vdata = self.bodydata
			circle_geom = Geom(vdata)
			vert_writer = GeomVertexWriter(vdata, "vertex")
			normal_writer = GeomVertexWriter(vdata, "normal")
			tex_rewriter = GeomVertexRewriter(vdata, "texcoord")
			start_row = vdata.get_num_rows() # index of first vertex of current drawing branch
			vert_writer.set_row(start_row)
			normal_writer.set_row(start_row)
			tex_rewriter.set_row(start_row)
			tex_v_coord = props.total_length # get total length from root to current branch
			slice_angle = 2 * math.pi / num_side_slices

			def add_circle(props: FractalBase.BranchProps, radius = None):
				'adds cylinder circle'
				curr_angle, perp1, perp2 = 0, props.direction.get_right(), props.direction.get_forward()
				pos, radius = props.pos, props.radius if radius is None else radius
				# print(f'{pos=}')
				# add cylinder side circle slice by slice
				# face side vertex order is left to right ->
				# Example for branch{pos=(0, 0, 0) radius=1} num_side_slices = 4:
				# vertexes positions: (1, 0, 0), (0, 1, 0), (-1, 0, 0), (0, -1, 0)
				# texture UV coords:  (0, 0),    (0.25, 0), (0.5, 0),   (0.75, 0)
				for i in range(num_side_slices + 1): # doubles the last vertex to fix UV seam
					# add vertex, normal & texture coord
					normal = perp1 * math.cos(curr_angle) + perp2 * math.sin(curr_angle)
					vert_pos = pos + normal * radius
					# print(f'{i} {vert_pos}')
					normal_writer.add_data3f(normal)
					vert_writer.add_data3f(vert_pos)
					tex_rewriter.add_data2f(i / num_side_slices, tex_v_coord)
					curr_angle += slice_angle

			# add first circle of cylinder
			add_circle(branch_props)
			# add second circle of cylinder
			tex_v_coord += branch_props.length
			add_circle(child_branch_props)

			# Use Tristrips geom to draw cylinder side slices. One slice vertex order:
			# 0 2 # second circle # self.bodydata vertex indexes: 2, 3
			# 1 3 # first circle  # self.bodydata vertex indexes: 0, 1
			# Example self.bodydata vertex indexes for num_side_slices = 4:
			# 4 5 6 7 # second circle
			# 0 1 2 3 # first circle
			lines = GeomTristrips(Geom.UHStatic)
			# start_row: index of first vertex of first circle # doubles the last vertex to fix UV seam
			for i in range(start_row, start_row + num_side_slices + 2):
				lines.add_vertex(i + num_side_slices) # second circle
				lines.add_vertex(i) # first circle
			lines.close_primitive()
			# lines.decompose()
			circle_geom.add_primitive(lines)
			circle_geom_node = GeomNode("Debug")
			circle_geom_node.add_geom(circle_geom)
			self.num_primitives += num_side_slices * 2
			self.bodies_np.attach_new_node(circle_geom_node)

		child_max_radius, child_max_angle = max(props.branches, key=lambda br: br.radius), max((math.fabs(br.direction.get_angle()) for br in props.branches))
		if child_max_angle > 65:
			# print(f'{child_max_angle=}')
			child_branch_props = props.create_next(props.length + child_max_radius.radius, props.length + child_max_radius.radius, child_max_radius.radius)
			add_branch(props, child_branch_props)
			child_branch_props2 = child_branch_props.create_next(child_branch_props.radius, child_branch_props.radius, 0)
			add_branch(child_branch_props, child_branch_props2)
			# print('MIDDLE')
			# middle_branch_props = FractalBase.BranchProps(
			# 	props.pos,
			# 	props.direction,
			# 	props.length - child_branch_props.radius, props.radius, props.branches, props.total_length, props.branch_length
			# )
			# middle_branch_props2 = FractalBase.BranchProps(
			# 	middle_branch_props.next_pos(0),
			# 	middle_branch_props.direction,
			# 	middle_branch_props.radius, 0, middle_branch_props.branches, props.total_length, props.branch_length
			# )
			# add_branch(middle_branch_props, middle_branch_props2)
			# add_branch(middle_branch_props2, child_branch_props)
		else:
			add_branch(props, child_max_radius)

	def draw_leaf(self, pos=Vec3(0, 0, 0), quat=None, scale=0.125):
		'''
		draws leafs when we reach an end
		'''
		# use the vectors that describe the direction the branch grows to make
		# the right rotation matrix
		new_cs = Mat4()
		quat.extract_to_matrix(new_cs)
		axis_adj = Mat4.scale_mat(scale) * new_cs * Mat4.translate_mat(pos)
		leaf_np = NodePath("leaf")
		self.leaf_np.instance_to(leaf_np)
		leaf_np.reparent_to(self.leaves_np)
		leaf_np.set_transform(TransformState.make_mat(axis_adj))

	def grow(self, refresh_leaves=False, leaves_scale=1, scale=1.125):
		'''
		grows the tree for num steps
		'''
		self.set_scale(self, scale)
		# self.leaf_np.setScale(self.leaf_np, leaves_scale / scale)
		if refresh_leaves:
			# remove old generated leaves
			for c in self.leaves_np.get_children():
				c.remove_node()
		for prop in super().grow():
			self.draw_branch(prop)
		if refresh_leaves:
			for prop in self.iter_ends(self.root):
				if not prop.branches:
					# no children branches # place leaf
					self.draw_leaf(prop.pos, prop.direction, leaves_scale)

	def get_next_branches_count(self, branch: FractalBase.BranchProps) -> int:
		if branch.length < self.branch_min_len or branch.total_length > 35:
			# stop grow this branch
			return 0
		if random.random() < .3:
			# continue one branch
			return 1
		# split to multiple branchs
		if random.random() < .8:
			return 2
		return 3


class DefaultTree(FractalTree):

	BARK_TEXTURE = TextureProps('models/barkTexture.jpg', Vec2(2, .25), Texture.FTLinearMipmapLinear, Texture.WM_mirror, None, 16)
	LEAF_MODEL_PATH = 'models/shrubbery'
	LEAF_TEXTURE_PATH = 'models/material-10-cl.png'

	def __init__(self):
		# set bark texture
		bark_texture = base.loader.loadTexture(self.BARK_TEXTURE.path)
		self.BARK_TEXTURE.set_texture_props(bark_texture)
		# set leaf texture
		leaf_np = base.loader.loadModel(self.LEAF_MODEL_PATH)
		leaf_np.clear_model_nodes()
		leaf_np.flatten_strong()
		leafTexture = base.loader.loadTexture(self.LEAF_TEXTURE_PATH)
		leafTexture.set_minfilter(Texture.FTLinearMipmapLinear)
		leaf_np.set_texture(leafTexture, 1)
		super().__init__(bark_texture, leaf_np,
			FractalBase.BranchProps(Vec3(0, 0, 0), Quat(), 5, 1, []))
		self.set_tex_scale(self.bark_ts, *(
			self.BARK_TEXTURE.scale.x * random.uniform(.5, 1.5), self.BARK_TEXTURE.scale.y * random.uniform(.5, 1.5))
		)


if __name__ == "__main__":
	from direct.showbase.ShowBase import ShowBase
	from direct.gui.DirectRadioButton import DirectRadioButton
	from os import uname
	from RadioButtons import RadioButtons

	global demo_running
	base, demo_running = ShowBase(), True

	props = WindowProperties()
	props.set_title(f'Panda3D Workbench - (P3D {PandaSystem.get_version_string()} on {uname().sysname} {uname().release} {uname().machine})')
	base.win.request_properties(props)


	def look_camera_at_entire_object(np: NodePath, camera=base.cam, lense=base.camLens):

		def get_distance(radius) -> float:
			if lense:
				fov = lense.get_fov()
				return radius / math.tan(math.radians(min(fov[0], fov[1]) / 2.))
			return 50.

		bounds = np.get_bounds()
		camera.set_pos(Vec3.forward() * get_distance(bounds.get_radius()))
		camera.look_at(bounds.get_center())

	def forest():
		global demo_running
		demo_running = True
		terrain_size, terrain_pos = Vec3(512, 512, 10), Vec2(-256, -256)
		trees_count = 100

		def create_tree():
			count = 10
			t = DefaultTree()
			for _ in range(count):
				if _ == count - 1:
					t.grow(True, leaves_scale=random.uniform(.1, .15))
				else:
					t.grow()
			return t

		def forest_task(task):
			'place tree at terrain'
			global demo_running
			nonlocal count, text, text2
			if count < trees_count and demo_running:
				if not text:
					text = OnscreenText('FOREST GENERATION', scale=.1, fg=(.6, .5, .2, 1), bg=(0, 0, 0, .5), shadow=(0.5,0.5,0.5,1), frame=(0.05,0.05,0.05,1))
				if not text2:
					text2 = OnscreenText(f'{count}', pos=(0, -.15), scale=.05, fg=(.6, .5, .2, 1), bg=(0, 0, 0, .5), shadow=(0.5,0.5,0.5,1), frame=(0.05,0.05,0.05,1))
				else:
					text2.setText(f'{count}')
				t = create_tree()
				x, y, z = random.uniform(terrain_pos.x, terrain_pos.x + terrain_size.x), random.uniform(terrain_pos.y, terrain_pos.y + terrain_size.y), Vec4()
				peeker.fetch_pixel(z, int(x) - int(terrain_pos.x), int(y) - int(terrain_pos.y))
				t.set_pos(x, y, z.x * terrain_size.z)
				t.set_scale(random.uniform(.25, 1))
				t = t.get_static()
				t.reparent_to(base.render)
				count += 1
				# base.screenshot()
			else:
				text.cleanup()
				text2.cleanup()
				return task.done # stop forest task
			return task.cont

		def setup_terrain():
			heightfield_img = PNMImage(int(terrain_size.x), int(terrain_size.y), 1, 65535)
			heightfield_img.fill(0, 0, 0)
			heightfield_img.perlin_noise_fill(.075, .075, 32, 25)
			highfield_tex = Texture()
			highfield_tex.load(heightfield_img)
			terrain_node = ShaderTerrainMesh()
			terrain_node.heightfield = highfield_tex
			terrain_node.target_triangle_width = 6.0
			terrain_node.generate()
			terrain_np = base.render.attach_new_node(terrain_node)
			terrain_np.set_scale(terrain_size.x, terrain_size.y, terrain_size.z)
			terrain_np.set_pos(terrain_pos.x, terrain_pos.y, 0)
			terrain_np.set_shader(Shader.load(Shader.SL_GLSL, vertex='terrain/terrain.vert.glsl', fragment='terrain/terrain.frag.glsl'))
			ts = TextureStage('map_texture')
			terrain_texture = base.loader.load_texture('terrain/texture.grass.jpg')
			terrain_texture.set_minfilter(Texture.FTLinearMipmapLinear)
			terrain_texture.set_anisotropic_degree(16)
			terrain_np.set_texture(ts, terrain_texture)
			terrain_np.set_shader_input('texture_factor', Vec2(20, 20))
			return terrain_np

		base.cam.set_pos(-15, -250, 10)
		base.cam.set_hpr(0, -5, 0)
		base.set_scene_graph_analyzer_meter(True)
		base.set_background_color(0.3, 0.53, 0.93, 1)
		light = AmbientLight('ambientLight')
		ambient_light_np = base.render.attach_new_node(light)
		base.render.set_light(ambient_light_np)
		light.set_color(Vec4(0.85, 0.85, 0.9, 1))
		count, text, text2 = 0, None, None
		terrain_np = setup_terrain()
		peeker = terrain_np.node().heightfield.peek()
		base.taskMgr.add(forest_task, "forestTask") # start forest task

	def tree():
		base.cam.set_pos(0, -500, 120)
		t = DefaultTree()
		t.reparent_to(base.render)
		base.cam.look_at(t)
		for _ in range(10):
			t.grow()
		look_camera_at_entire_object(t)

	def branch():
		base.cam.set_pos(0, -50, 7)
		t = DefaultTree()
		t.reparent_to(base.render)
		# t.setTexScale(t.bark_ts, 2, .25)
		# t.setTexOffset(t.bark_ts, 2, 2)
		# add branches
		t.root.add_branch(Quat(), 5, 1)
		print(f'{len(t.root.branches)=}')
		q = Quat()
		q.setHpr(Vec3(0, 80, 80))
		t.root.branches[0].add_branch(q, 5, 1)
		t.root.branches[0].branches[0].add_branch(Quat(), 5, 1)
		# draw branches
		t.draw_branch(t.root)
		t.draw_branch(t.root.branches[0])
		t.draw_branch(t.root.branches[0].branches[0])
		look_camera_at_entire_object(t)

	def grow_animation():
		global demo_running
		demo_running = True
		counts, grow_step_time = 10, .25
		count, last_timestamp = 0, 0
		# base.cam.set_pos(50, -200, 10)
		#  create tree
		t = DefaultTree()
		t.reparent_to(base.render)

		def grow(task):
			global demo_running
			nonlocal count, last_timestamp
			if task.time > last_timestamp:
				print(f'Grow times: {count}')
				t.grow(True, leaves_scale=count / 70) # grow tree for one fractal step
				look_camera_at_entire_object(t)
				last_timestamp = task.time + grow_step_time
				if count == counts:
					return task.done # stop grow task
				count += 1
			return task.cont if demo_running else task.done

		base.taskMgr.add(grow, "growTask") # start grow task


	def show_menu():
		global demo_menu
		demo_text = list((
			OnscreenText(' Panda3D workbench: tree ', scale=.05, pos=(0, .95), fg=(.75, .75, .55, .75), bg=(.5, .5, .5, .5), align=TextNode.ACenter),
			OnscreenText('Press <Esc> to show menu, use arrows keys and <Enter> or mouse', scale=.04, fg=(.75, .75, .55, .75), pos=(0, .9), align=TextNode.ACenter),
		))
		demo_menu = RadioButtons(base, (
			('Forest', forest),
			('Grow anomation', grow_animation),
			('Tree', tree),
			('Branch', branch))
		)

	def btn_escape():
		global demo_menu, demo_running
		try:
			if demo_menu.get_selected_index() < 0:
				demo_menu, demo_running = None, False
				base.render.get_children().detach()
				base.camera.reparent_to(base.render)
				base.set_background_color(0.5, 0.5, 0.5, 1)
				base.set_scene_graph_analyzer_meter(False)
				show_menu()
		except:
			pass

	base.accept('escape', btn_escape)

	show_menu()

	base.run()
