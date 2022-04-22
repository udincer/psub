from __future__ import annotations

from rich.console import RenderableType
from rich.style import StyleType


from textual import events
from textual.geometry import SpacingDimensions
from textual.layouts.grid import GridLayout
from textual.message import Message
from textual.messages import CursorMove
from textual.scrollbar import ScrollTo
from textual.geometry import clamp
from textual.view import View

from textual.widget import Widget

from textual.reactive import Reactive


class ScrollView(View):
    def __init__(
        self,
        contents: RenderableType | Widget | None = None,
        *,
        auto_width: bool = False,
        name: str | None = None,
        style: StyleType = "",
        fluid: bool = True,
        gutter: SpacingDimensions = (0, 0)
    ) -> None:
        from textual.views import WindowView

        self.fluid = fluid
        self.window = WindowView(
            "" if contents is None else contents, auto_width=auto_width, gutter=gutter
        )
        layout = GridLayout()
        layout.add_column("main")
        layout.add_row("main")
        layout.add_areas(
            content="main,main"
        )
        super().__init__(name=name, layout=layout)

    x: Reactive[float] = Reactive(0, repaint=False)
    y: Reactive[float] = Reactive(0, repaint=False)

    target_x: Reactive[float] = Reactive(0, repaint=False)
    target_y: Reactive[float] = Reactive(0, repaint=False)

    def validate_x(self, value: float) -> float:
        return clamp(value, 0, self.max_scroll_x)

    def validate_target_x(self, value: float) -> float:
        return clamp(value, 0, self.max_scroll_x)

    def validate_y(self, value: float) -> float:
        return clamp(value, 0, self.max_scroll_y)

    def validate_target_y(self, value: float) -> float:
        return clamp(value, 0, self.max_scroll_y)

    @property
    def max_scroll_y(self) -> float:
        return max(0, self.window.virtual_size.height - self.window.size.height)

    @property
    def max_scroll_x(self) -> float:
        return max(0, self.window.virtual_size.width - self.window.size.width)

    async def watch_x(self, new_value: float) -> None:
        self.window.scroll_x = round(new_value)

    async def watch_y(self, new_value: float) -> None:
        self.window.scroll_y = round(new_value)

    async def update(self, renderable: RenderableType, home: bool = True) -> None:
        if home:
            self.home()
        await self.window.update(renderable)

    async def on_mount(self, event: events.Mount) -> None:
        assert isinstance(self.layout, GridLayout)
        self.layout.place(
            content=self.window,
        )
        await self.layout.mount_all(self)

    def home(self) -> None:
        self.x = self.y = 0

    def scroll_up(self) -> None:
        self.y += 1.5

    def scroll_down(self) -> None:
        self.y -= 1.5

    def page_up(self) -> None:
        self.y -= self.size.height

    def page_down(self) -> None:
        self.y += self.size.height

    def page_left(self) -> None:
        self.x -= self.size.width

    def page_right(self) -> None:
        self.x += self.size.width

    def scroll_in_to_view(self, line: int) -> None:
        if line < self.y:
            self.y = line
        elif line >= self.y + self.size.height:
            self.y = line - self.size.height + 1

    def scroll_to_center(self, line: int) -> None:
        self.target_y = line - self.size.height // 2
        self.y = self.target_y

    async def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        self.scroll_up()

    async def on_mouse_scroll_down(self, event: events.MouseScrollUp) -> None:
        self.scroll_down()

    async def on_key(self, event: events.Key) -> None:
        await self.dispatch_key(event)

    async def key_down(self) -> None:
        self.y += 2

    async def key_up(self) -> None:
        self.y -= 2

    async def key_pagedown(self) -> None:
        self.y += self.size.height

    async def key_pageup(self) -> None:
        self.y -= self.size.height

    async def key_end(self) -> None:
        self.x = 0
        self.y = self.window.virtual_size.height - self.size.height

    async def key_home(self) -> None:
        self.x = 0
        self.y = 0

    async def handle_scroll_up(self) -> None:
        self.page_up()

    async def handle_scroll_down(self) -> None:
        self.page_down()

    async def handle_scroll_left(self) -> None:
        self.page_left()

    async def handle_scroll_right(self) -> None:
        self.page_right()

    async def handle_scroll_to(self, message: ScrollTo) -> None:
        if message.x is not None:
            self.x = message.x
        if message.y is not None:
            self.y = message.y

    async def handle_window_change(self, message: Message) -> None:

        message.stop()

        virtual_width, virtual_height = self.window.virtual_size
        width, height = self.size

        self.x = self.validate_x(self.x)
        self.y = self.validate_y(self.y)

        assert isinstance(self.layout, GridLayout)

    def handle_cursor_move(self, message: CursorMove) -> None:
        self.scroll_to_center(message.line)
        message.stop()