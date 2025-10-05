from rich.layout import Layout
from rich.panel import Panel
from rich.console import Console

console = Console()

# 1. Create a Layout object
layout = Layout(name="root")

# 2. Divide the layout vertically (top/bottom)
layout.split_column(
    Layout(name="header", size=3), # Fixed height of 3 rows
    Layout(name="body")
)

# 3. Divide the 'body' horizontally (left/right)
layout["body"].split_row(
    Layout(name="left", ratio=1), # Ratio 1 means they split the space equally
    Layout(name="right", ratio=1)
)

# 4. Populate the sections with Panels (or any other renderable)
layout["header"].update(Panel("[bold yellow]🚀 AI Operation Status[/bold yellow]", border_style="yellow"))
layout["left"].update(Panel("Tasks: [green]Running[/green]\nLog Count: 42"))
layout["right"].update(Panel("CPU Load: 75%\nMemory: 12GB"))

console.print(layout)