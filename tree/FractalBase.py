
# python imports
from typing import Iterable, Iterator, Optional, List, Tuple, NamedTuple
import random

# Panda3D imports
from panda3d.core import Vec3, Quat


class FractalBase:
	'''
	Base class for fractal fugures
	'''

	class BranchProps(NamedTuple):
		pos: Vec3
		direction: Quat
		length: float
		radius: float
		branches: Iterable['BranchProps']
		total_length: float = 0
		branches_count: int = 0

		def __str__(self):
			return f'{{({self.pos.x:03.1f}, {self.pos.y:03.1f}, {self.pos.z:03.1f}) len: {self.length:03.2f} dir: ({self.direction.getHpr().x:03.0f}, {self.direction.getHpr().y:03.0f}, {self.direction.getHpr().z:03.0f}) radius: {self.radius:.2f} branches: {len(self.branches)} total: {self.total_length:.2f}  branch: {self.total_length:.2f}}}'

		def next_pos(self, length: Optional[float] = None) -> Vec3:
			return self.pos + self.direction.xform(Vec3(0, 0, self.length if length is None else length))

		def create_next(self, pos_length: float, length: float, radius: float) -> 'BranchProps':
			return FractalBase.BranchProps(
				self.next_pos(pos_length), self.direction, length, radius, [], self.total_length + pos_length, self.branches_count + 1
			)

		def add_branch(self, direction: Quat, length: float, radius: float) -> 'BranchProps':
			ret = FractalBase.BranchProps(
				self.next_pos(), direction, length, radius, [], self.total_length + self.length, self.branches_count + 1
			)
			self.branches.append(ret)
			return ret

	def __init__(self, root: BranchProps):
		self.branch_min_radius = .01
		self.branch_min_len, self.next_branch_radius_k = .2, (.3, .9)
		self.root = root
		self.ends: List[self.BranchProps] = []

	@classmethod
	def iter_ends(cls, root: BranchProps) -> Iterator[Tuple[BranchProps, float]]:
		# print(f'iter_ends: {root}')
		if not root.branches:
			# print(f'iter_ends yield: {root}')
			yield root
		else:
			for branch_ in root.branches:
				yield from cls.iter_ends(branch_)

	def get_next_ends(self) -> List[BranchProps]:
		'generate next grow-step parameters'

		def generate_next_branches(branch: self.BranchProps) -> Iterable[self.BranchProps]:
			'returns branches that has grown children branches'
			ret = []
			if (branches_count := self.get_next_branches_count(branch)):
				# print(f'get_next_branches_count: {branches_count}')
				# add branches # generate branches
				if branches_count == 1:
					# just continue branch # add one branch
					next_len = branch.length * random.uniform(.9, 1.05)
					q = Quat()
					q.set_hpr(Vec3(0, random.uniform(-180 / 5, 180 / 5), random.uniform(-180 / 5, 180 / 5)))
					next_direction = q * branch.direction
					branch.add_branch(next_direction, next_len, branch.radius)
				else:
					# add multiple branches # generate radiuses & directions
					next_radiuses = [ next_radius for next_radius in
						(self.next_branch_radius(branch) for _ in range(branches_count))
						if next_radius >= self.branch_min_radius
					]
					next_directions = list(map(Quat, (0,) * len(next_radiuses)))
					for q in next_directions:
						q.set_hpr(Vec3(0, random.uniform(-180 / 4, 180 / 4), random.uniform(-180 / 4, 180 / 4)))
						q = branch.direction * q
					next_lens = []
					for _ in range(len(next_radiuses)):
						next_lens.append(branch.length * random.uniform(.2, 1.5))
					# print(f'get_next_branches_count: {next_radiuses=} {next_directions=} {next_lens=}')
					# add branches
					for next_radius, next_direction, next_len in zip(next_radiuses, next_directions, next_lens):
						# add branch
						branch.add_branch(next_direction, next_len, next_radius)
				ret.append(branch)
			else:
				# print(f'get_next_branches_count: 0')
				pass
			return ret

		ret = []
		for branch in self.iter_ends(self.root):
			ret += generate_next_branches(branch)
		return ret

	def grow(self) -> Iterable[BranchProps]:
		'''grows the tree
		Returns list of branches that has grown children branches
		'''
		return self.get_next_ends()

	# parameterized branch split callbacks

	def get_next_branches_count(self, branch: BranchProps) -> int:
		if branch.length < self.branch_min_len:
			# stop grow this branch
			return 0
		if random.random() >= .7:
			# split to multiple branchs
			return 2
		# continue one branch
		return 1

	def next_branch_radius(self, branch: BranchProps) -> float:
		return branch.radius * random.uniform(.3, .9)


if __name__ == "__main__":
	q = Quat()
	q.setHpr(Vec3(0, 0, 0))
	f = FractalBase(FractalBase.BranchProps(Vec3(0, 0, 0), q, 1, .1, []))
	f.grow()
	f.grow()
	f.grow()
