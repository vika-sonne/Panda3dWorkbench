#version 330

// This is the terrain fragment shader. There is a lot of code in here
// which is not necessary to render the terrain, but included for convenience -
// Like generating normals from the heightmap or a simple fog effect.

// Most of the time you want to adjust this shader to get your terrain the look
// you want. The vertex shader most likely will stay the same.

in vec2 terrain_uv;
in vec3 vtx_pos;
out vec4 color;

uniform struct {
  sampler2D data_texture;
  sampler2D heightfield;
  int view_index;
  int terrain_size;
  int chunk_size;
} ShaderTerrainMesh;

uniform sampler2D p3d_Texture0;
uniform vec2 texture_factor;

void main() {
  vec3 diffuse = texture(p3d_Texture0, terrain_uv * texture_factor).xyz;
  color = vec4(diffuse, 1.0);
}
