from rich.text import Text
from rich.table import Table
from rich.panel import Panel

from textual.app import App, log
# from textual.widgets import ScrollView
from sge_monitor_tui_scrollview import ScrollView

from sge_monitor import get_job_lines, AnsiCommands


class SimpleApp(App):

    async def on_mount(self) -> None:
        self.body = body = ScrollView()
        await self.view.dock(body, edge="bottom")

        async def get_jobs2() -> None:
            lines = get_job_lines()

            self.table = table = Table(box=None, show_header=False, expand=True)
            table.add_column('j1', justify="left")
            table.add_column('j2', justify="right")

            for line in lines:
                l1, l2 = [l for l in line.split('     ') if l]
                table.add_row(Text.from_ansi(l1), Text.from_ansi(l2))

            # for i in range(100):
            #     table.add_row(f"{i=}", "2")
            
            self.prev_y = body.y
            await body.update(table)
            body.y = self.prev_y

        await self.call_later(get_jobs2)

        body.set_timer(0.05, get_jobs2)
        body.set_interval(2, get_jobs2)


    async def on_load(self) -> None:
        await self.bind("q", "quit")
        await self.bind("b", "scroll_bottom")
        await self.bind("0", "scroll_top")
        
    async def action_scroll_bottom(self):
        self.body.y += 2000

    async def action_scroll_top(self):
        self.body.y = 0


SimpleApp.run(log="textual.log")