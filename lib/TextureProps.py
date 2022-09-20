
# python imports
from typing import Optional, NamedTuple

# Panda3D imports
from panda3d.core import Vec2


class TextureProps(NamedTuple):
	path: str
	scale: Optional[Vec2] = None
	minfilter: Optional[int] = None # Texture.FTLinearMipmapLinear
	wrap_u: Optional[int] = None # Texture.WM_mirror
	wrap_v: Optional[int] = None # Texture.WM_mirror
	anisotropic_degree: Optional[float] = None # power of 2
	transparency: Optional[int] = None # TransparencyAttrib.MAlpha

	def set_texture_props(self, texture: 'Texture', np: Optional['NodePath'] = None, ts: Optional['TextureStage'] = None):
		if self.minfilter:
			texture.set_minfilter(self.minfilter)
		if self.wrap_u is not None:
			texture.set_wrap_u(self.wrap_u)
		if self.wrap_v is not None:
			texture.set_wrap_v(self.wrap_v)
		if self.anisotropic_degree is not None:
			texture.set_anisotropic_degree(self.anisotropic_degree)
		if np and ts and self.scale:
			np.set_tex_scale(ts, self.scale)
		if np and self.transparency:
			np.set_transparency(self.transparency)
