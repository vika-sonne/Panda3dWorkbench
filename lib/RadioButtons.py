
# python imports
from typing import Iterable, Optional, Tuple, Callable

# Panda3D imports
from direct.gui.DirectRadioButton import DirectRadioButton


class RadioButtons:

	def __init__(self, base: 'ShowBase', variants: Iterable[Tuple[str, Callable]],
			selected_index = 0) -> None:
		self.base = base
		self.ignore_selection = True
		self.variants = variants
		scale, radio_x, radio_y, radio_y_delta = 0.05, -0.5, 0.5, 0.2
		# create buttons
		self.buttons = list(
			DirectRadioButton(text=x[0], scale=scale,
				pos=(radio_x, 0, radio_y - i * radio_y_delta), command=self.selected_changed)
			for i, x in enumerate(self.variants)
		)
		for btn in self.buttons:
			btn.setOthers(self.buttons)
		# select button
		if 0 <= selected_index < len(variants):
			self.buttons[selected_index].check()
		else:
			self.buttons[0].check()
		# setup keyboard input
		self.base.accept('arrow_up', self.btn_up)
		self.base.accept('arrow_down', self.btn_down)
		self.base.accept('enter', self.btn_enter)
		self.ignore_selection = False
		# selected button info # info for user
		self.selected_index: Optional[int] = selected_index
		self.selected_callback: Optional[Callable] = None

	def cleanup(self):
		self.base.ignore('arrow_up')
		self.base.ignore('arrow_down')
		self.base.ignore('enter')
		for btn in self.buttons:
			btn.destroy()
		self.buttons = None

	def get_selected_index(self) -> int:
		try:
			return next(filter(lambda x: x[1]['indicatorValue'] == 1, enumerate(self.buttons)))[0]
		except:
			return -1

	def selected_changed(self):
		selected_index = self.get_selected_index()
		if selected_index >= 0 and not self.ignore_selection:
			self.variant_selected(selected_index)

	def btn_up(self):
		self.ignore_selection = True
		selected_index = self.get_selected_index()
		if selected_index > 0:
			self.buttons[selected_index - 1].check()
		self.ignore_selection = False

	def btn_down(self):
		self.ignore_selection = True
		selected_index = self.get_selected_index()
		if selected_index < len(self.buttons) - 1:
			self.buttons[selected_index + 1].check()
		self.ignore_selection = False

	def btn_enter(self):
		self.selected_changed()

	def variant_selected(self, variant: int):
		print(f'variant_selected: {variant} {self.variants[variant][0]}')
		self.cleanup()
		# save variant & call the callback
		self.selected_index = variant
		self.selected_callback = self.variants[variant][1]
		self.selected_callback()
