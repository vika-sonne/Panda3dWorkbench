
# python imports
from typing import Iterable, Iterator, Optional, List, Tuple, NamedTuple, Callable
import math
import random
from os import path
from sys import path as search_paths

# Panda3D imports
from panda3d.core import (Mat4, Vec2, Vec3, Vec4, Point3, Quat, Geom, GeomNode, Texture, TextureStage, TransparencyAttrib,
	GeomVertexWriter, GeomTristrips, GeomVertexRewriter, GeomVertexData, GeomVertexFormat,
	CollisionNode, CollisionTube, TransformState, NodePath, PNMImage, ShaderTerrainMesh, Shader, AmbientLight,
	TextNode, WindowProperties, PandaSystem, LineSegs)
from direct.gui.OnscreenText import OnscreenText

# Workbench imports
module_path = path.dirname(path.abspath(__file__))
search_paths.insert(0, path.abspath(path.join(module_path, '../lib')))
from TextureProps import TextureProps


class P3dBottleBase(NodePath):

	def __init__(self, bottle_len: float, neck_len: float, neck_narrow_len: float,
			bottle_radius: float, neck_radius: float, tex: TextureProps, num_side_slices = 15):
		super().__init__('Bottle Holder')

		self.bottle_radius, self.neck_radius = bottle_radius, neck_radius
		self.bottle_len, self.neck_len, self.neck_narrow_len = bottle_len, neck_len, neck_narrow_len
		self.num_side_slices = num_side_slices

		self.body_np = NodePath('Body')
		self.collision_np = self.attach_new_node(CollisionNode('Collision'))
		self.bodydata = GeomVertexData('body vertices',
									   GeomVertexFormat.getV3n3t2(),
									   Geom.UHStatic)
		self.collision_np.show()
		self.collision_np.reparent_to(self)
		self.body_np.reparent_to(self)

		self.texture_props = tex
		self.ts = TextureStage('ts')
		self.texture = base.loader.loadTexture(self.texture_props.path)
		self.body_np.set_texture(self.ts, self.texture)
		self.texture_props.set_texture_props(self.texture, self.body_np, self.ts)
		# self.body_np.set_tex_scale(self.ts, 1, 3.3)

		self.position = Vec3(0, 0, 0) # сurrent point on the axis of symmetry
		self.texture_v_coord = 0

		self.draw()

	def draw(self):
		self.draw_piece(0, .0)
		self.draw_piece(self.bottle_radius, self.bottle_len - self.neck_len - self.neck_narrow_len)
		self.draw_piece(self.bottle_radius, self.neck_narrow_len)
		self.draw_piece(self.neck_radius, self.neck_len)
		self.draw_piece(self.neck_radius, 0)
		self.draw_piece(0, .0)

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

	def draw_piece(self, radius: float, len: float) -> None:
		'''draws piece of the bottle as cylinder
		This draws a ring of vertices and connects the rings with triangles to from the bottle piece.
		'''

		# print(f'draw_piece: {radius=} {len=} {num_side_slices=}')
		vdata = self.bodydata
		circle_geom = Geom(vdata)
		vert_writer = GeomVertexWriter(vdata, "vertex")
		normal_writer = GeomVertexWriter(vdata, "normal")
		tex_rewriter = GeomVertexRewriter(vdata, "texcoord")
		start_row = vdata.get_num_rows() # index of first vertex of current drawing piece
		vert_writer.set_row(start_row)
		normal_writer.set_row(start_row)
		tex_rewriter.set_row(start_row)
		tex_v_coord = self.texture_v_coord # get total length to current piece
		pos = self.position
		num_side_slices = self.num_side_slices
		slice_angle = 2 * math.pi / num_side_slices

		# add circle
		curr_angle, perp1, perp2 = 0, Vec3.right(), Vec3.forward()
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
			# print(f'{i + start_row} {vert_pos}')
			normal_writer.add_data3f(normal)
			vert_writer.add_data3f(vert_pos)
			tex_rewriter.add_data2f(i / num_side_slices, tex_v_coord)
			curr_angle += slice_angle

		self.texture_v_coord += len
		self.position.z += len

		if start_row:
			# Use Tristrips geom to draw cylinder side slices. One slice vertex order:
			# 0 2 # second circle # self.bodydata vertex indexes: 2, 3
			# 1 3 # first circle  # self.bodydata vertex indexes: 0, 1
			# Example self.bodydata vertex indexes for num_side_slices = 4:
			# 4 5 6 7 # second circle
			# 0 1 2 3 # first circle
			lines = GeomTristrips(Geom.UHStatic)
			# start_row: index of first vertex of first circle # doubles the last vertex to fix UV seam
			for i in range(start_row - num_side_slices - 1, start_row + 1):
				# print(f'add vertex: {i} {i + num_side_slices}')
				lines.add_vertex(i + num_side_slices) # second circle
				lines.add_vertex(i) # first circle
			lines.close_primitive()
			# lines.decompose()
			circle_geom.add_primitive(lines)
			circle_geom_node = GeomNode("Debug")
			circle_geom_node.add_geom(circle_geom)
			self.body_np.attach_new_node(circle_geom_node)


if __name__ == "__main__":
	from direct.showbase.ShowBase import ShowBase
	from os import uname
	from RadioButtons import RadioButtons

	MODULE_PATH = path.dirname(path.abspath(__file__))
	TEXTURES_PATH = path.join(MODULE_PATH, 'textures/')

	global demo_bottle, distance
	base, demo_bottle, distance = ShowBase(), None, 0

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
		camera.set_pos(Vec3.forward() * (get_distance(bounds.get_radius()) + distance))
		camera.look_at(bounds.get_center())


	class BottleGost:

		@classmethod
		def draw_axes(cls):
			'draws axis with meter'

			def draw_axis(axis: Vec3, division_len, count = 10):
				lines = LineSegs()
				for i in range(0, count, 2):
					lines.move_to(axis * i * division_len)
					lines.draw_to(axis * i * division_len + axis * division_len)
				lines.set_thickness(1)
				base.render.attach_new_node(lines.create())

			draw_axis(Vec3.up(), .1) # z
			draw_axis(Vec3.right(), .1) # x

		@classmethod
		def place_bottle(cls, bottle: NodePath):
			global demo_bottle
			demo_bottle = bottle # save bottle NodePath
			bottle.reparent_to(base.render)
			look_camera_at_entire_object(bottle)
			cls.draw_axes()

		@classmethod
		def type_iii_500(cls, tex_props: TextureProps):
			'bottle type III, 500 ml, GOST 10117-91, draw 3, page 3'
			cls.place_bottle(P3dBottleBase(.28, .074, .02, .0345, .015, tex_props))

		@classmethod
		def type_xa(cls, tex_props: TextureProps):
			'bottle type Xa, 500 ml, GOST 10117-91, draw 9a, page 5'
			cls.place_bottle(P3dBottleBase(.23, .02, .085, .036, .013, tex_props))


	class Vodka:

		@classmethod
		def Stolichnaya(cls):
			BottleGost.type_iii_500(TextureProps(TEXTURES_PATH+'vodka.stolichnaya.png',
				anisotropic_degree=8, scale=(1, 3.3), transparency=TransparencyAttrib.MAlpha))

		@classmethod
		def Limonnaya(cls):
			BottleGost.type_iii_500(TextureProps(TEXTURES_PATH+'vodka.limonnaya.png',
				anisotropic_degree=8, scale=(1, 3.3), transparency=TransparencyAttrib.MAlpha))

		@classmethod
		def Zubrovka(cls):
			BottleGost.type_iii_500(TextureProps(TEXTURES_PATH+'vodka.zubrovka.png',
				anisotropic_degree=8, scale=(1, 3.3), transparency=TransparencyAttrib.MAlpha))

		@classmethod
		def Pertsovka(cls):
			BottleGost.type_iii_500(TextureProps(TEXTURES_PATH+'vodka.pertsovka.png',
				anisotropic_degree=8, scale=(1, 3.3), transparency=TransparencyAttrib.MAlpha))


	class Beer:

		@classmethod
		def Zhiguli_Minsk(cls):
			BottleGost.type_xa(TextureProps(TEXTURES_PATH+'beer.zhiguli.minsk.png',
				anisotropic_degree=8, scale=(1, 3.3), transparency=TransparencyAttrib.MAlpha))

		@classmethod
		def Zhiguli_Chernihiv(cls):
			BottleGost.type_xa(TextureProps(TEXTURES_PATH+'beer.zhiguli.chernihiv.png',
				anisotropic_degree=8, scale=(1, 3.3), transparency=TransparencyAttrib.MAlpha))


	class BigBottle:

		def bottle(tex_props: TextureProps):
			# draw bottle
			BottleGost.place_bottle(P3dBottleBase(.51, .1, .05, .15, .025, tex_props))

		@classmethod
		def Alcohol(cls):
			cls.bottle(TextureProps(TEXTURES_PATH+'big.alcohol.png',
				anisotropic_degree=8, transparency=TransparencyAttrib.MAlpha))

		@classmethod
		def Formalin(cls):
			cls.bottle(TextureProps(TEXTURES_PATH+'big.formalin.png',
				anisotropic_degree=8, transparency=TransparencyAttrib.MAlpha))


	def show_menu():
		global demo_menu
		demo_text = list((
			OnscreenText(' Panda3D workbench: bottle ', scale=.05, pos=(0, .95), fg=(.75, .75, .55, .75), bg=(.5, .5, .5, .5), align=TextNode.ACenter),
			OnscreenText('Press <Esc> to show menu, use arrows keys and <Enter> or mouse, <r> - reset view, <F5> - reload model', scale=.04, fg=(.75, .75, .55, .75), pos=(0, .9), align=TextNode.ACenter),
		))
		try:
			selected_index = demo_selected_index
		except Exception as e:
			selected_index = 0
		demo_menu = RadioButtons(base, (
			('Vodka Stolichnaya', Vodka.Stolichnaya),
			('Vodka Limonnaya', Vodka.Limonnaya),
			('Vodka Zubrovka', Vodka.Zubrovka),
			('Vodka Pertsovka', Vodka.Pertsovka),
			('Beer Zhiguli Minsk', Beer.Zhiguli_Minsk),
			('Beer Zhiguli Chernihiv', Beer.Zhiguli_Chernihiv),
			('Big Alcohol', BigBottle.Alcohol),
			('Big Formalin', BigBottle.Formalin),
		), selected_index = selected_index)

	def clear_scene():
		base.render.get_children().detach()
		base.camera.reparent_to(base.render)
		base.set_scene_graph_analyzer_meter(False)

	def btn_escape():
		global demo_menu, demo_running, demo_selected_index
		try:
			if demo_menu.get_selected_index() < 0:
				demo_selected_index = demo_menu.selected_index
				demo_menu, demo_running = None, False
				clear_scene()
				# base.set_background_color(0.5, 0.5, 0.5, 1)
				show_menu()
		except:
			pass

	def btn_left():
		if demo_bottle:
			demo_bottle.set_h(demo_bottle.get_h() + 5)
			look_camera_at_entire_object(demo_bottle)

	def btn_right():
		if demo_bottle:
			demo_bottle.set_h(demo_bottle.get_h() - 5)
			look_camera_at_entire_object(demo_bottle)

	def btn_up():
		if demo_bottle:
			demo_bottle.set_p(demo_bottle.get_p() + 5)
			look_camera_at_entire_object(demo_bottle)

	def btn_down():
		if demo_bottle:
			demo_bottle.set_p(demo_bottle.get_p() - 5)
			look_camera_at_entire_object(demo_bottle)

	def btn_plus():
		if demo_bottle:
			global distance
			if distance >= .5:
				distance -= .5
				look_camera_at_entire_object(demo_bottle)

	def btn_minus():
		if demo_bottle:
			global distance
			distance += .5
			look_camera_at_entire_object(demo_bottle)

	def btn_reset():
		# reset visual positions
		if demo_bottle:
			global distance
			distance = 0
			demo_bottle.set_pos(0, 0, 0)
			demo_bottle.set_hpr(0, 0, 0)
			base.camera.set_pos(0, 0, 0)
			base.camera.set_hpr(0, 0, 0)
			look_camera_at_entire_object(demo_bottle)

	def btn_reload():
		if demo_bottle and demo_menu.selected_callback:
			base.loader.unload_texture(demo_bottle.texture)
			demo_bottle.texture = demo_bottle.ts = None
			hpr = demo_bottle.get_hpr()
			clear_scene()
			demo_menu.selected_callback()
			demo_bottle.set_hpr(hpr)


	base.accept('escape', btn_escape)
	base.accept('r', btn_reset)
	base.accept('f5', btn_reload)
	base.accept('arrow_left', btn_left)
	base.accept('arrow_left-repeat', btn_left)
	base.accept('arrow_right', btn_right)
	base.accept('arrow_right-repeat', btn_right)
	base.accept('arrow_up', btn_up)
	base.accept('arrow_up-repeat', btn_up)
	base.accept('arrow_down', btn_down)
	base.accept('arrow_down-repeat', btn_down)
	base.accept('+', btn_plus)
	base.accept('+-repeat', btn_plus)
	base.accept('-', btn_minus)
	base.accept('--repeat', btn_minus)

	show_menu()
	base.camLens.set_near(.1)
	base.run()
