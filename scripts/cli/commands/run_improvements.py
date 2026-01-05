# Helper functions to be inserted before render_dashboard

def clear_screen() -> None:
    """Clear the terminal screen using Rich console (optimized)."""
    console.clear()


def render_main_dashboard_with_layout(config: Dict, use_cache: bool = True, skip_port_checks: bool = False) -> Layout:
    """Render the main dashboard using Rich Layout for better organization.

    Optimized with caching and skip_port_checks for performance.

    Returns a Layout with:
    - Top: Service status table
    - Middle: Important URLs
    - Bottom: Menu options and shortcuts
    """
    # Get service health (with caching for performance)
    backend_health = get_service_health("Backend", config, use_cache=use_cache, skip_port_check=skip_port_checks)
    frontend_health = get_service_health("Frontend", config, use_cache=use_cache, skip_port_check=skip_port_checks)

    # Build service status table
    status_table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
    status_table.add_column("Servicio", style="bold", width=18)
    status_table.add_column("Estado", style="bold", width=12)
    status_table.add_column("PID", width=8)
    status_table.add_column("Puerto", width=8)
    status_table.add_column("CPU/Mem", width=15)
    status_table.add_column("Latencia", width=10)

    # Status icons helper
    def get_status_icon(status: str) -> str:
        icons = {"running": "🟢", "degraded": "🟡", "stopped": "🔴", "unavailable": "⚪"}
        return icons.get(status, "⚪")

    # Backend row
    backend_status = backend_health["status"]
    status_color = "green" if backend_status == "running" else ("yellow" if backend_status == "degraded" else "red" if backend_status == "stopped" else "yellow")
    cpu_mem = "N/A"
    if backend_health["cpu_percent"] is not None and backend_health["memory_mb"] is not None:
        cpu_mem = f"{backend_health['cpu_percent']:.1f}% / {backend_health['memory_mb']:.0f}MB"
    latency = f"{backend_health['latency_ms']:.0f}ms" if backend_health["latency_ms"] is not None else "N/A"

    status_table.add_row(
        "Backend",
        f"{get_status_icon(backend_status)} [{status_color}]{backend_status}[/{status_color}]",
        str(backend_health["pid"]) if backend_health["pid"] else "N/A",
        str(backend_health.get("port", 8000)),
        cpu_mem,
        latency
    )

    # Frontend row
    frontend_status = frontend_health["status"]
    status_color = "green" if frontend_status == "running" else ("yellow" if frontend_status == "degraded" else "red" if frontend_status == "stopped" else "yellow")
    cpu_mem = "N/A"
    if frontend_health["cpu_percent"] is not None and frontend_health["memory_mb"] is not None:
        cpu_mem = f"{frontend_health['cpu_percent']:.1f}% / {frontend_health['memory_mb']:.0f}MB"
    latency = f"{frontend_health['latency_ms']:.0f}ms" if frontend_health["latency_ms"] is not None else "N/A"

    status_table.add_row(
        "Frontend",
        f"{get_status_icon(frontend_status)} [{status_color}]{frontend_status}[/{status_color}]",
        str(frontend_health["pid"]) if frontend_health["pid"] else "N/A",
        str(frontend_health.get("port", 3000)),
        cpu_mem,
        latency
    )

    # Docker services (quick check, no blocking)
    pg_config = DEFAULT_CONFIG["docker"]["postgres"]
    pg_running = check_container_running(pg_config["container"])
    docker_status = "running" if pg_running else "stopped"
    status_color = "green" if docker_status == "running" else "red"
    status_table.add_row(
        "Docker (PostgreSQL)",
        f"{get_status_icon(docker_status)} [{status_color}]{docker_status}[/{status_color}]",
        "-",
        str(pg_config["port"]),
        "-",
        "N/A"
    )

    # Build URLs panel
    backend_config = config.get("backend", DEFAULT_CONFIG["backend"])
    frontend_config = config.get("frontend", DEFAULT_CONFIG["frontend"])

    urls_text = Text()
    urls_text.append("🌐 URLs Importantes:\n\n", style="bold cyan")
    urls_text.append(f"  Frontend:     ", style="dim")
    urls_text.append(f"{frontend_config.get('url', 'http://127.0.0.1:3000')}\n", style="bold blue")
    urls_text.append(f"  Backend API:  ", style="dim")
    urls_text.append(f"http://localhost:{backend_config.get('port', 8000)}\n", style="bold blue")
    urls_text.append(f"  API Docs:     ", style="dim")
    urls_text.append(f"http://localhost:{backend_config.get('port', 8000)}/docs\n", style="bold blue")
    urls_text.append(f"  pgAdmin:      ", style="dim")
    urls_text.append("http://localhost:8888\n", style="bold blue")

    # Create layout
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3)
    )

    layout["body"].split_row(
        Layout(name="status", ratio=2),
        Layout(name="urls", ratio=1)
    )

    # Header
    header_text = Text()
    header_text.append("╭", style="cyan")
    header_text.append("─" * 58, style="cyan")
    header_text.append("╮\n", style="cyan")
    header_text.append("│", style="cyan")
    header_text.append("  AiutoX ERP - Control Suite", style="bold cyan")
    header_text.append(" " * 28, style="cyan")
    header_text.append("│\n", style="cyan")
    header_text.append("╰", style="cyan")
    header_text.append("─" * 58, style="cyan")
    header_text.append("╯", style="cyan")
    layout["header"].update(Panel(header_text, border_style="cyan", box=None))

    # Status panel
    layout["status"].update(Panel(status_table, title="[bold cyan]Estado de Servicios[/bold cyan]", border_style="cyan"))

    # URLs panel
    layout["urls"].update(Panel(urls_text, title="[bold cyan]URLs[/bold cyan]", border_style="cyan"))

    # Footer (will be updated by menu)
    footer_text = Text()
    footer_text.append("[dim]💡 Presiona 'Q' o '15' y Enter para salir, Ctrl+C para salir inmediatamente[/dim]", style="dim")
    layout["footer"].update(Panel(footer_text, border_style="dim", box=None))

    return layout


def show_nano_style_viewer(content: Text, title: str, shortcuts: Dict[str, str] = None, refresh_rate: float = 5.0) -> None:
    """Display content in a nano-style viewer with shortcuts at the bottom.

    Optimized with controlled refresh rate to avoid CPU overload.

    Args:
        content: Text content to display
        title: Title for the viewer
        shortcuts: Dict of shortcut keys and descriptions (e.g., {"^X": "Salir", "^F": "Buscar"})
        refresh_rate: Maximum refresh rate per second (default 5.0 to avoid CPU overload)
    """
    if shortcuts is None:
        shortcuts = {"^X": "Salir", "^O": "Continuar"}

    # Build shortcuts bar (like nano) - optimized rendering
    shortcuts_text = Text()
    for key, desc in shortcuts.items():
        shortcuts_text.append(f" {key} ", style="bold white on blue")
        shortcuts_text.append(f"{desc}  ", style="white")

    # Create layout
    layout = Layout()
    layout.split_column(
        Layout(name="content", ratio=10),
        Layout(name="shortcuts", size=1)
    )

    # Content panel
    content_panel = Panel(
        content,
        title=f"[bold cyan]{title}[/bold cyan]",
        border_style="cyan",
        padding=(0, 1)
    )
    layout["content"].update(content_panel)

    # Shortcuts bar (nano style)
    shortcuts_panel = Panel(
        shortcuts_text,
        border_style="blue",
        box=None
    )
    layout["shortcuts"].update(shortcuts_panel)

    console.print(layout)


















