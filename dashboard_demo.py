"""
Material Design 3 Dashboard Demo
- Navigation Drawer
- Cards with dynamic theming
- FAB (Floating Action Button)
- M3 Dynamic Color Theme
"""

import customtkinter as ctk
from typing import Callable, Optional
import colorsys

# === M3 Dynamic Color System ===
class M3DynamicTheme:
    """Material Design 3 Dynamic Color Theme Generator"""

    def __init__(self, seed_color: str = "#6750A4"):
        self.seed = seed_color
        self.generate_palette()

    def hex_to_hsl(self, hex_color: str) -> tuple:
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) / 255 for i in (0, 2, 4))
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        return (h * 360, s * 100, l * 100)

    def hsl_to_hex(self, h: float, s: float, l: float) -> str:
        r, g, b = colorsys.hls_to_rgb(h / 360, l / 100, s / 100)
        return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

    def generate_palette(self):
        h, s, l = self.hex_to_hsl(self.seed)

        # Primary tones
        self.primary = self.seed
        self.primary_container = self.hsl_to_hex(h, s * 0.8, 90)
        self.on_primary = "#FFFFFF"
        self.on_primary_container = self.hsl_to_hex(h, s, 10)

        # Secondary (shifted hue)
        h2 = (h + 30) % 360
        self.secondary = self.hsl_to_hex(h2, s * 0.6, 40)
        self.secondary_container = self.hsl_to_hex(h2, s * 0.5, 90)
        self.on_secondary = "#FFFFFF"
        self.on_secondary_container = self.hsl_to_hex(h2, s * 0.6, 10)

        # Tertiary (complementary)
        h3 = (h + 60) % 360
        self.tertiary = self.hsl_to_hex(h3, s * 0.7, 40)
        self.tertiary_container = self.hsl_to_hex(h3, s * 0.5, 90)

        # Surface tones
        self.surface = "#FEFBFF"
        self.surface_variant = self.hsl_to_hex(h, s * 0.3, 95)
        self.surface_container = self.hsl_to_hex(h, s * 0.2, 92)
        self.surface_container_high = self.hsl_to_hex(h, s * 0.2, 88)
        self.on_surface = "#1C1B1F"
        self.on_surface_variant = "#49454F"

        # Outline
        self.outline = self.hsl_to_hex(h, s * 0.2, 50)
        self.outline_variant = self.hsl_to_hex(h, s * 0.2, 80)

        # Error
        self.error = "#B3261E"
        self.error_container = "#F9DEDC"

        # Background
        self.background = "#FEFBFF"
        self.on_background = "#1C1B1F"


# === M3 Components ===

class M3NavigationDrawer(ctk.CTkFrame):
    """Material Design 3 Navigation Drawer"""

    def __init__(self, master, theme: M3DynamicTheme, items: list, **kwargs):
        super().__init__(master, fg_color=theme.surface, corner_radius=0, **kwargs)
        self.theme = theme
        self.items = items
        self.selected_index = 0
        self.buttons = []

        # Header
        header = ctk.CTkLabel(
            self,
            text="Daihon Rakku",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=theme.on_surface
        )
        header.pack(pady=(24, 16), padx=16, anchor="w")

        # Divider
        divider = ctk.CTkFrame(self, height=1, fg_color=theme.outline_variant)
        divider.pack(fill="x", padx=12, pady=(0, 8))

        # Navigation items
        for i, item in enumerate(items):
            btn = self._create_nav_item(item, i)
            self.buttons.append(btn)

    def _create_nav_item(self, item: dict, index: int) -> ctk.CTkButton:
        is_selected = index == self.selected_index

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="x", padx=12, pady=2)

        btn = ctk.CTkButton(
            container,
            text=f"  {item.get('icon', '')}  {item['label']}",
            font=ctk.CTkFont(size=14),
            fg_color=self.theme.secondary_container if is_selected else "transparent",
            text_color=self.theme.on_secondary_container if is_selected else self.theme.on_surface_variant,
            hover_color=self.theme.surface_container_high,
            anchor="w",
            height=56,
            corner_radius=28,
            command=lambda idx=index: self._on_select(idx)
        )
        btn.pack(fill="x")
        return btn

    def _on_select(self, index: int):
        # Reset previous
        if self.selected_index < len(self.buttons):
            self.buttons[self.selected_index].configure(
                fg_color="transparent",
                text_color=self.theme.on_surface_variant
            )

        # Set new
        self.selected_index = index
        self.buttons[index].configure(
            fg_color=self.theme.secondary_container,
            text_color=self.theme.on_secondary_container
        )

        # Callback
        if self.items[index].get("command"):
            self.items[index]["command"]()


class M3Card(ctk.CTkFrame):
    """Material Design 3 Card Component"""

    def __init__(
        self,
        master,
        theme: M3DynamicTheme,
        variant: str = "elevated",  # elevated, filled, outlined
        **kwargs
    ):
        self.theme = theme

        if variant == "elevated":
            fg_color = theme.surface
            border_width = 0
        elif variant == "filled":
            fg_color = theme.surface_container_high
            border_width = 0
        else:  # outlined
            fg_color = theme.surface
            border_width = 1

        super().__init__(
            master,
            fg_color=fg_color,
            corner_radius=12,
            border_width=border_width,
            border_color=theme.outline_variant if variant == "outlined" else None,
            **kwargs
        )


class M3FAB(ctk.CTkButton):
    """Material Design 3 Floating Action Button"""

    def __init__(
        self,
        master,
        theme: M3DynamicTheme,
        icon: str = "+",
        size: str = "regular",  # small, regular, large
        variant: str = "primary",  # primary, secondary, tertiary, surface
        command: Optional[Callable] = None,
        **kwargs
    ):
        sizes = {
            "small": {"width": 40, "height": 40, "font_size": 20, "corner": 12},
            "regular": {"width": 56, "height": 56, "font_size": 24, "corner": 16},
            "large": {"width": 96, "height": 96, "font_size": 36, "corner": 28}
        }

        colors = {
            "primary": (theme.primary_container, theme.on_primary_container),
            "secondary": (theme.secondary_container, theme.on_secondary_container),
            "tertiary": (theme.tertiary_container, theme.on_surface),
            "surface": (theme.surface_container_high, theme.primary)
        }

        s = sizes.get(size, sizes["regular"])
        fg, text = colors.get(variant, colors["primary"])

        super().__init__(
            master,
            text=icon,
            font=ctk.CTkFont(size=s["font_size"], weight="bold"),
            width=s["width"],
            height=s["height"],
            corner_radius=s["corner"],
            fg_color=fg,
            text_color=text,
            hover_color=theme.primary_container,
            command=command,
            **kwargs
        )


class M3TopAppBar(ctk.CTkFrame):
    """Material Design 3 Top App Bar"""

    def __init__(
        self,
        master,
        theme: M3DynamicTheme,
        title: str = "",
        **kwargs
    ):
        super().__init__(master, fg_color=theme.surface, height=64, corner_radius=0, **kwargs)
        self.theme = theme

        # Menu button
        self.menu_btn = ctk.CTkButton(
            self,
            text="☰",
            font=ctk.CTkFont(size=24),
            width=48,
            height=48,
            fg_color="transparent",
            text_color=theme.on_surface,
            hover_color=theme.surface_container
        )
        self.menu_btn.pack(side="left", padx=4, pady=8)

        # Title
        self.title_label = ctk.CTkLabel(
            self,
            text=title,
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=theme.on_surface
        )
        self.title_label.pack(side="left", padx=16)

        # Actions
        self.actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.actions_frame.pack(side="right", padx=8)


class M3Chip(ctk.CTkButton):
    """Material Design 3 Chip"""

    def __init__(
        self,
        master,
        theme: M3DynamicTheme,
        text: str,
        selected: bool = False,
        **kwargs
    ):
        super().__init__(
            master,
            text=text,
            font=ctk.CTkFont(size=13),
            height=32,
            corner_radius=8,
            fg_color=theme.secondary_container if selected else "transparent",
            text_color=theme.on_secondary_container if selected else theme.on_surface_variant,
            border_width=1,
            border_color=theme.outline if not selected else "transparent",
            hover_color=theme.surface_container_high,
            **kwargs
        )


# === Dashboard Application ===

class M3Dashboard(ctk.CTk):
    """Material Design 3 Dashboard Demo"""

    def __init__(self):
        super().__init__()

        self.title("M3 Dashboard - Daihon Rakku")
        self.geometry("1280x800")

        # Initialize dynamic theme
        self.theme = M3DynamicTheme("#7C3AED")  # Purple seed
        self.configure(fg_color=self.theme.background)

        self._create_layout()

    def _create_layout(self):
        # Main container
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True)

        # Navigation Drawer
        nav_items = [
            {"icon": "🏠", "label": "ダッシュボード", "command": lambda: self._show_page("dashboard")},
            {"icon": "📝", "label": "脚本生成", "command": lambda: self._show_page("generate")},
            {"icon": "👤", "label": "キャラクター", "command": lambda: self._show_page("characters")},
            {"icon": "⚙️", "label": "設定", "command": lambda: self._show_page("settings")},
            {"icon": "📊", "label": "統計", "command": lambda: self._show_page("stats")},
        ]

        self.nav_drawer = M3NavigationDrawer(
            self.main_container,
            self.theme,
            nav_items,
            width=280
        )
        self.nav_drawer.pack(side="left", fill="y")

        # Content area
        self.content_area = ctk.CTkFrame(
            self.main_container,
            fg_color=self.theme.surface_variant,
            corner_radius=0
        )
        self.content_area.pack(side="left", fill="both", expand=True)

        # Top App Bar
        self.top_bar = M3TopAppBar(
            self.content_area,
            self.theme,
            title="ダッシュボード"
        )
        self.top_bar.pack(fill="x")

        # Scrollable content
        self.scroll_frame = ctk.CTkScrollableFrame(
            self.content_area,
            fg_color="transparent"
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=24, pady=16)

        # Create dashboard content
        self._create_dashboard_content()

        # FAB
        self.fab = M3FAB(
            self.content_area,
            self.theme,
            icon="+",
            size="large",
            variant="primary",
            command=self._on_fab_click
        )
        self.fab.place(relx=0.95, rely=0.95, anchor="se")

    def _create_dashboard_content(self):
        # Stats row
        stats_row = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        stats_row.pack(fill="x", pady=(0, 16))

        stats = [
            ("生成回数", "127", "📝"),
            ("キャラ数", "24", "👤"),
            ("総シーン", "512", "🎬"),
            ("API使用量", "$12.50", "💰")
        ]

        for title, value, icon in stats:
            card = M3Card(stats_row, self.theme, variant="elevated")
            card.pack(side="left", fill="both", expand=True, padx=8)

            icon_label = ctk.CTkLabel(
                card, text=icon, font=ctk.CTkFont(size=32)
            )
            icon_label.pack(pady=(16, 8))

            value_label = ctk.CTkLabel(
                card,
                text=value,
                font=ctk.CTkFont(size=28, weight="bold"),
                text_color=self.theme.primary
            )
            value_label.pack()

            title_label = ctk.CTkLabel(
                card,
                text=title,
                font=ctk.CTkFont(size=14),
                text_color=self.theme.on_surface_variant
            )
            title_label.pack(pady=(4, 16))

        # Recent activity section
        section_label = ctk.CTkLabel(
            self.scroll_frame,
            text="最近のアクティビティ",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.theme.on_surface,
            anchor="w"
        )
        section_label.pack(fill="x", pady=(16, 8))

        # Activity cards
        activities = [
            ("フリーレンNTRシナリオ生成", "10分前", "完了", "#4CAF50"),
            ("キャラ分析: 伊地知虹夏", "1時間前", "完了", "#4CAF50"),
            ("推しの子 シーン12生成中", "実行中", "進行中", "#FF9800"),
        ]

        for title, time, status, color in activities:
            card = M3Card(self.scroll_frame, self.theme, variant="outlined")
            card.pack(fill="x", pady=4)

            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=12)

            title_label = ctk.CTkLabel(
                row,
                text=title,
                font=ctk.CTkFont(size=15),
                text_color=self.theme.on_surface,
                anchor="w"
            )
            title_label.pack(side="left")

            status_chip = ctk.CTkLabel(
                row,
                text=status,
                font=ctk.CTkFont(size=12),
                text_color=color,
                fg_color=self.theme.surface_container,
                corner_radius=8,
                padx=8,
                pady=4
            )
            status_chip.pack(side="right")

            time_label = ctk.CTkLabel(
                row,
                text=time,
                font=ctk.CTkFont(size=12),
                text_color=self.theme.on_surface_variant
            )
            time_label.pack(side="right", padx=16)

        # Theme selector section
        section_label2 = ctk.CTkLabel(
            self.scroll_frame,
            text="テーマカラー",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.theme.on_surface,
            anchor="w"
        )
        section_label2.pack(fill="x", pady=(24, 8))

        colors_row = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        colors_row.pack(fill="x", pady=8)

        theme_colors = [
            ("#6750A4", "Purple"),
            ("#006A6A", "Teal"),
            ("#7C5800", "Gold"),
            ("#BA1A1A", "Red"),
            ("#006E1C", "Green"),
            ("#005AC1", "Blue"),
        ]

        for color, name in theme_colors:
            btn = ctk.CTkButton(
                colors_row,
                text="",
                width=48,
                height=48,
                corner_radius=24,
                fg_color=color,
                hover_color=color,
                command=lambda c=color: self._change_theme(c)
            )
            btn.pack(side="left", padx=4)

    def _show_page(self, page: str):
        self.top_bar.title_label.configure(
            text={
                "dashboard": "ダッシュボード",
                "generate": "脚本生成",
                "characters": "キャラクター",
                "settings": "設定",
                "stats": "統計"
            }.get(page, page)
        )

    def _change_theme(self, color: str):
        self.theme = M3DynamicTheme(color)
        # In a real app, you'd update all components here
        self.configure(fg_color=self.theme.background)
        self.content_area.configure(fg_color=self.theme.surface_variant)
        print(f"Theme changed to {color}")

    def _on_fab_click(self):
        print("FAB clicked - Start new generation")


if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    app = M3Dashboard()
    app.mainloop()
