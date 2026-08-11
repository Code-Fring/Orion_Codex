"""Orion Codex Terminal UI - Full TUI application."""

import json
from datetime import datetime
from pathlib import Path

from backend.core.providers.factory import ProviderFactory
from backend.core.providers.interfaces import ChatMessage
from backend.core.providers.registry import provider_registry
from backend.memory.store import memory_store
from rich.markdown import Markdown
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    RichLog,
    Static,
    TabbedContent,
    TabPane,
    Tree,
)


class ChatMessageWidget(Static):
    """Widget to display a chat message with markdown rendering."""

    def __init__(self, role: str, content: str, timestamp: str = None, **kwargs):
        super().__init__(**kwargs)
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now().strftime("%H:%M:%S")

    def compose(self) -> ComposeResult:
        role_style = "bold cyan" if self.role == "user" else "bold green"
        role_label = "You" if self.role == "user" else "Orion"

        with Container(classes="message-container"):
            with Horizontal(classes="message-header"):
                yield Label(
                    f"[{role_style}]{role_label}[/{role_style}]", classes="role-label"
                )
                yield Label(f"[dim]{self.timestamp}[/dim]", classes="timestamp")

            # Render markdown content
            if self.role == "assistant":
                yield Static(
                    Markdown(self.content),
                    classes="message-content markdown",
                    markup=False,
                )
            else:
                yield Label(
                    self.content, classes="message-content user-content", markup=False
                )


class StatusBar(Static):
    """Status bar showing provider, model, workspace, tokens, cost."""

    provider_name = reactive("mock")
    model_name = reactive("mock-model")
    workspace_path = reactive(str(Path.cwd()))
    token_usage = reactive({"prompt": 0, "completion": 0, "total": 0})
    session_cost = reactive(0.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.update_display()

    def watch_provider_name(self, _: str) -> None:
        self.update_display()

    def watch_model_name(self, _: str) -> None:
        self.update_display()

    def watch_workspace_path(self, _: str) -> None:
        self.update_display()

    def watch_token_usage(self, _: dict) -> None:
        self.update_display()

    def watch_session_cost(self, _: float) -> None:
        self.update_display()

    def update_display(self) -> None:
        ws_name = Path(self.workspace_path).name or "~"
        tokens = self.token_usage
        self.update(
            f"[bold]Provider:[/bold] {self.provider_name}  "
            f"[bold]Model:[/bold] {self.model_name}  "
            f"[bold]Workspace:[/bold] {ws_name}  "
            f"[bold]Tokens:[/bold] {tokens['total']} (in:{tokens['prompt']} out:{tokens['completion']})  "
            f"[bold]Cost:[/bold] ${self.session_cost:.4f}"
        )


class FileTreeWidget(Tree):
    """File tree widget for workspace navigation."""

    def __init__(self, root_path: Path, **kwargs):
        super().__init__("Workspace", **kwargs)
        self.root_path = root_path
        self.show_root = True
        self.guide_depth = 3

    def on_mount(self) -> None:
        self.load_directory(self.root, self.root_path)

    def load_directory(self, tree_node: Tree, path: Path) -> None:
        try:
            items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
            for item in items:
                if item.name.startswith("."):
                    continue
                if item.is_dir():
                    node = tree_node.add(
                        item.name + "/", data={"path": item, "is_dir": True}
                    )
                    node.expand()
                else:
                    tree_node.add_leaf(item.name, data={"path": item, "is_dir": False})
        except PermissionError:
            pass

    def on_tree_node_expanded(self, event: Tree.NodeExpanded) -> None:
        node = event.node
        if node.data and node.data.get("is_dir") and not node.children:
            self.load_directory(node, node.data["path"])

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        if event.node.data and not event.node.data.get("is_dir"):
            self.post_message(FileSelected(event.node.data["path"]))


class FileSelected(Message):
    """Message when a file is selected in the tree."""

    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path


class CommandPalette(Static):
    """Command palette for quick actions."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.visible = False
        self.commands = [
            ("New Chat", "new_chat", "Ctrl+N"),
            ("Open File", "open_file", "Ctrl+O"),
            ("Run Command", "run_command", "Ctrl+R"),
            ("Settings", "settings", "Ctrl+,"),
            ("Help", "help", "F1"),
            ("Exit", "exit", "Ctrl+Q"),
        ]

    def compose(self) -> ComposeResult:
        with Container(classes="command-palette-container", id="command-palette"):
            yield Label("[bold]Command Palette[/bold]", classes="palette-title")
            for name, cmd, shortcut in self.commands:
                with Horizontal(classes="palette-item"):
                    yield Label(name, classes="palette-name")
                    yield Label(f"[dim]{shortcut}[/dim]", classes="palette-shortcut")

    def show(self) -> None:
        self.visible = True
        self.display = True

    def hide(self) -> None:
        self.visible = False
        self.display = False


class DebugConsole(RichLog):
    """Debug console for logging."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.highlight = True
        self.markup = True
        self.wrap = True
        self.max_lines = 1000


class OrionApp(App):
    """Main Orion Codex TUI Application."""

    CSS = """
    Screen {
        layout: vertical;
        background: $surface;
    }
    
    #main-container {
        layout: horizontal;
        height: 1fr;
    }
    
    #sidebar {
        width: 30;
        height: 1fr;
        border-right: solid $primary;
        background: $surface-darken-1;
    }
    
    #main-content {
        width: 1fr;
        height: 1fr;
        layout: vertical;
    }
    
    #chat-area {
        height: 1fr;
        overflow-y: auto;
        padding: 1;
    }
    
    #input-area {
        height: auto;
        min-height: 3;
        border-top: solid $primary;
        padding: 1;
    }
    
    #status-bar {
        height: 1;
        background: $primary;
        color: $text;
        padding: 0 1;
        dock: bottom;
    }
    
    .message-container {
        margin: 1 0;
        padding: 1;
        border: solid $primary;
        border-title-align: left;
    }
    
    .message-header {
        height: 1;
    }
    
    .role-label {
        width: auto;
    }
    
    .timestamp {
        width: auto;
        text-align: right;
    }
    
    .message-content {
        margin-top: 1;
    }
    
    .user-content {
        color: $text;
    }
    
    .markdown {
        width: 100%;
    }
    
    #command-palette {
        display: none;
        layer: dialog;
        offset: 10 25;
        width: 50%;
        height: auto;
        background: $surface;
        border: solid $primary;
        padding: 1;
    }
    
    .command-palette-container {
        width: 100%;
    }
    
    .palette-title {
        width: 100%;
        text-align: center;
        margin-bottom: 1;
    }
    
    .palette-item {
        width: 100%;
        height: 1;
        padding: 0 1;
    }
    
    .palette-item:hover {
        background: $primary;
        color: $text;
    }
    
    .palette-name {
        width: 1fr;
    }
    
    .palette-shortcut {
        width: auto;
        text-align: right;
    }
    
    #debug-console {
        height: 20;
        border-top: solid $warning;
        background: $surface-darken-2;
    }
    
    TabbedContent {
        height: 1fr;
    }
    
    TabPane {
        padding: 1;
    }
    
    DataTable {
        height: 1fr;
    }
    
    Input {
        width: 100%;
    }
    
    #file-tree {
        height: 1fr;
        padding: 1;
    }
    
    #providers-table {
        height: 1fr;
    }
    
    #models-table {
        height: 1fr;
    }
    
    .sidebar-title {
        text-style: bold;
        padding: 1;
        border-bottom: solid $primary;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+n", "new_chat", "New Chat"),
        Binding("ctrl+o", "open_file", "Open File"),
        Binding("ctrl+r", "run_command", "Run Command"),
        Binding("ctrl+comma", "settings", "Settings"),
        Binding("f1", "help", "Help"),
        Binding("ctrl+d", "toggle_debug", "Debug Console"),
        Binding("ctrl+p", "command_palette", "Command Palette"),
        Binding("ctrl+l", "clear_chat", "Clear Chat"),
        Binding("tab", "focus_next", "Next Panel"),
        Binding("shift+tab", "focus_previous", "Previous Panel"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.provider = None
        self.current_model = "mock-model"
        self.messages: list[ChatMessage] = []
        self.chat_history: list[dict] = []
        self.workspace_path = Path.cwd()
        self.token_usage = {"prompt": 0, "completion": 0, "total": 0}
        self.session_cost = 0.0
        self.debug_visible = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True, name="Orion Codex", icon="🤖")

        with Container(id="main-container"):
            # Sidebar
            with Container(id="sidebar"):
                yield Label("[bold]WORKSPACE[/bold]", classes="sidebar-title")
                yield FileTreeWidget(self.workspace_path, id="file-tree")

                with TabbedContent():
                    with TabPane("Providers", id="providers-tab"):
                        yield Label("[bold]Providers[/bold]", classes="sidebar-title")
                        yield DataTable(id="providers-table")

                    with TabPane("Models", id="models-tab"):
                        yield Label("[bold]Models[/bold]", classes="sidebar-title")
                        yield DataTable(id="models-table")

                    with TabPane("Memory", id="memory-tab"):
                        yield Label(
                            "[bold]Project Memory[/bold]", classes="sidebar-title"
                        )
                        yield RichLog(id="memory-log", highlight=True, markup=True)

            # Main content
            with Container(id="main-content"):
                # Chat area
                with ScrollableContainer(id="chat-area"):
                    yield Static("", id="chat-messages")

                # Input area
                with Container(id="input-area"):
                    yield Input(
                        placeholder="Ask Orion anything... (Ctrl+Enter to send, Ctrl+P for palette)",
                        id="chat-input",
                    )

                # Debug console (hidden by default)
                debug_console = DebugConsole(id="debug-console")
                debug_console.display = False
                yield debug_console

        # Status bar
        yield StatusBar(id="status-bar")

        # Command palette
        yield CommandPalette(id="command-palette")

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the app."""
        self.title = "Orion Codex"
        self.sub_title = "Terminal-first AI Coding Agent"

        # Load providers
        await self.load_providers()

        # Load providers table
        await self.update_providers_table()

        # Load models table
        await self.update_models_table()

        # Load memory
        await self.load_memory()

        # Focus input
        self.query_one("#chat-input", Input).focus()

        # Log startup
        self.log_debug("Orion Codex TUI started")
        self.log_debug(f"Workspace: {self.workspace_path}")

    async def load_providers(self) -> None:
        """Load providers from config."""
        config_path = Path.home() / ".orion" / "providers.json"
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text())
                for provider_config in config.get("providers", []):
                    ptype = provider_config.get("type")
                    api_key = provider_config.get("api_key")
                    base_url = provider_config.get("base_url")
                    if ptype and api_key:
                        config_dict = {"api_key": api_key}
                        if base_url:
                            config_dict["base_url"] = base_url
                        provider = await ProviderFactory.create_provider(
                            ptype, config_dict, validate=False
                        )
                        if provider:
                            self.log_debug(f"Loaded provider: {provider.provider_name}")
            except Exception as e:
                self.log_debug(f"Error loading providers: {e}")

        # Get first provider
        providers = provider_registry.get_chat_providers()
        if providers:
            self.provider = providers[0]
            self.current_model = (
                "mock-model" if self.provider.provider_name == "mock" else "default"
            )
            self.query_one(
                "#status-bar", StatusBar
            ).provider_name = self.provider.provider_name
            self.query_one("#status-bar", StatusBar).model_name = self.current_model

    async def update_providers_table(self) -> None:
        """Update providers table."""
        table = self.query_one("#providers-table", DataTable)
        table.add_columns("Provider", "Type", "Status")

        providers = provider_registry.list_all_providers()
        for p in providers:
            table.add_row(p.provider_name, type(p).__name__, "Connected")

    async def update_models_table(self) -> None:
        """Update models table."""
        table = self.query_one("#models-table", DataTable)
        table.add_columns("Model", "Provider", "Context", "Capabilities")

        if self.provider:
            try:
                models = await self.provider.list_models()
                for model in models:
                    caps = ", ".join([c.value for c in model.capabilities])
                    table.add_row(
                        model.id, model.provider, str(model.context_window), caps
                    )
            except Exception as e:
                self.log_debug(f"Error loading models: {e}")
                table.add_row("Error loading models", "", "", "")

    async def load_memory(self) -> None:
        """Load project memory."""
        log = self.query_one("#memory-log", RichLog)
        try:
            memories = await memory_store.get_recent(limit=20)
            for mem in memories:
                log.write(
                    f"[dim]{mem.timestamp.strftime('%H:%M:%S')}[/dim] [bold]{mem.type}[/bold]: {mem.content[:100]}..."
                )
        except Exception as e:
            self.log_debug(f"Error loading memory: {e}")

    def log_debug(self, message: str) -> None:
        """Log to debug console."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        console = self.query_one("#debug-console", DebugConsole)
        console.write(f"[dim]{timestamp}[/dim] {message}")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle chat input submission."""
        if event.input.id == "chat-input":
            user_message = event.value.strip()
            if not user_message:
                return

            event.input.value = ""

            await self.send_message(user_message)

    async def send_message(self, content: str) -> None:
        """Send a message and get response."""
        if not self.provider:
            self.log_debug("No provider available")
            return

        # Add user message to chat
        user_msg = ChatMessage(role="user", content=content)
        self.messages.append(user_msg)
        self.chat_history.append(
            {
                "role": "user",
                "content": content,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Display user message
        chat_area = self.query_one("#chat-area", ScrollableContainer)
        chat_messages = self.query_one("#chat-messages", Static)

        # Create message widget
        msg_widget = ChatMessageWidget("user", content)
        await chat_messages.mount(msg_widget)
        chat_area.scroll_end(animate=False)

        # Show thinking indicator
        self.log_debug(f"Sending message to {self.provider.provider_name}")

        # Get AI response
        try:
            ai_content = ""

            # Stream response
            self.log_debug("Starting stream...")
            async for chunk in self.provider.chat_stream(
                self.messages, self.current_model, stream=True
            ):
                ai_content += chunk
                # Update the last message widget with streaming content
                # For simplicity, we'll collect and show at the end

            # Add AI message
            ai_msg = ChatMessage(role="assistant", content=ai_content)
            self.messages.append(ai_msg)
            self.chat_history.append(
                {
                    "role": "assistant",
                    "content": ai_content,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            # Display AI message
            ai_widget = ChatMessageWidget("assistant", ai_content)
            await chat_messages.mount(ai_widget)
            chat_area.scroll_end(animate=False)

            # Update token usage (mock for now)
            self.token_usage["prompt"] += len(content.split())
            self.token_usage["completion"] += len(ai_content.split())
            self.token_usage["total"] = (
                self.token_usage["prompt"] + self.token_usage["completion"]
            )
            self.session_cost += 0.0001  # Mock cost

            status_bar = self.query_one("#status-bar", StatusBar)
            status_bar.token_usage = self.token_usage
            status_bar.session_cost = self.session_cost

            self.log_debug(f"Response received: {len(ai_content)} chars")

            # Save to memory
            await memory_store.add(
                content=f"User: {content}\nAssistant: {ai_content}",
                type="chat",
                metadata={"model": self.current_model},
            )

        except Exception as e:
            self.log_debug(f"Error getting response: {e}")
            error_widget = ChatMessageWidget("assistant", f"[red]Error: {e}[/red]")
            await chat_messages.mount(error_widget)
            chat_area.scroll_end(animate=False)

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

    def action_new_chat(self) -> None:
        """Start a new chat session."""
        self.messages = []
        chat_messages = self.query_one("#chat-messages", Static)
        chat_messages.remove_children()
        self.log_debug("New chat started")

    def action_clear_chat(self) -> None:
        """Clear chat history."""
        self.action_new_chat()

    def action_toggle_debug(self) -> None:
        """Toggle debug console visibility."""
        self.debug_visible = not self.debug_visible
        debug_console = self.query_one("#debug-console", DebugConsole)
        debug_console.display = self.debug_visible
        self.log_debug(f"Debug console {'shown' if self.debug_visible else 'hidden'}")

    def action_command_palette(self) -> None:
        """Show command palette."""
        palette = self.query_one("#command-palette", CommandPalette)
        if palette.visible:
            palette.hide()
        else:
            palette.show()

    def action_open_file(self) -> None:
        """Open file dialog."""
        self.log_debug("Open file - not implemented yet")

    def action_run_command(self) -> None:
        """Run command dialog."""
        self.log_debug("Run command - not implemented yet")

    def action_settings(self) -> None:
        """Open settings."""
        self.log_debug("Settings - not implemented yet")

    def action_help(self) -> None:
        """Show help."""
        self.log_debug("Help - not implemented yet")

    def on_file_selected(self, event: FileSelected) -> None:
        """Handle file selection."""
        self.log_debug(f"File selected: {event.path}")
        # TODO: Open file in editor

    async def on_key(self, event: events.Key) -> None:
        """Handle key events."""
        if event.key == "ctrl+enter":
            input_widget = self.query_one("#chat-input", Input)
            if input_widget.value.strip():
                await self.send_message(input_widget.value.strip())
                input_widget.value = ""

    def on_unmount(self) -> None:
        """Cleanup on exit."""
        # Save session synchronously to avoid DOM access issues
        self._save_session_sync()

    def _save_session_sync(self) -> None:
        """Save session to disk synchronously."""
        try:
            session_data = {
                "timestamp": datetime.now().isoformat(),
                "workspace": str(self.workspace_path),
                "provider": self.provider.provider_name if self.provider else "none",
                "model": self.current_model,
                "messages": self.chat_history,
                "token_usage": self.token_usage,
                "cost": self.session_cost,
            }

            session_dir = Path.home() / ".orion" / "sessions"
            session_dir.mkdir(parents=True, exist_ok=True)

            session_file = (
                session_dir / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            session_file.write_text(json.dumps(session_data, indent=2))
        except Exception:
            pass  # Ignore errors on exit

    async def save_session(self) -> None:
        """Save session to disk (async version for manual saves)."""
        self._save_session_sync()


def run_tui():
    """Run the TUI application."""
    app = OrionApp()
    app.run()


if __name__ == "__main__":
    run_tui()
