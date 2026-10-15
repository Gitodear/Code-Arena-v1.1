import re
import pygame

KEYWORDS = {
    "def", "if", "elif", "else", "while", "for", "return", "True", "False", "None",
    "and", "or", "not", "in", "import", "from", "break", "continue", "pass", "class",
    "try", "except", "finally", "lambda", "is", "yield", "with", "as", "raise",
}

TOKEN_RE = re.compile(
    r"(?P<comment>#.*)"
    r"|(?P<string>'[^']*'|\"[^\"]*\")"
    r"|(?P<number>\b\d+\.?\d*\b)"
    r"|(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
    r"|(?P<op>[^\sA-Za-z0-9_]+)"
    r"|(?P<space>\s+)"
)

COLOR_DEFAULT = (212, 212, 212)
COLOR_KEYWORD = (197, 134, 192)
COLOR_STRING = (206, 145, 120)
COLOR_NUMBER = (181, 206, 168)
COLOR_COMMENT = (106, 153, 85)


def tokenize(line):
    tokens = []
    for m in TOKEN_RE.finditer(line):
        kind = m.lastgroup
        text = m.group()
        if kind == "comment":
            tokens.append((text, COLOR_COMMENT))
        elif kind == "string":
            tokens.append((text, COLOR_STRING))
        elif kind == "number":
            tokens.append((text, COLOR_NUMBER))
        elif kind == "name":
            color = COLOR_KEYWORD if text in KEYWORDS else COLOR_DEFAULT
            tokens.append((text, color))
        else:
            tokens.append((text, COLOR_DEFAULT))
    return tokens


class CodeEditor:
    def __init__(self, x, y, width, height, font, initial_code=""):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.lines = initial_code.split("\n") if initial_code else [""]
        self.active_line = 0
        self.col = 0
        self.line_height = 20
        self.gutter_width = 40
        self.scroll = 0
        self.cursor_blink = 0.0
        self.flash = 0.0  # brief pulse highlight on the active line while typing

    # ---- helpers ----
    def get_code(self):
        return "\n".join(self.lines)

    def _visible_lines(self):
        return max(1, (self.rect.height - 10) // self.line_height)

    def _ensure_visible(self):
        visible = self._visible_lines()
        if self.active_line < self.scroll:
            self.scroll = self.active_line
        elif self.active_line >= self.scroll + visible:
            self.scroll = self.active_line - visible + 1

    def _touch(self):
        self.flash = 1.0
        self.cursor_blink = 0.0

    def _clamp_col(self):
        self.col = max(0, min(self.col, len(self.lines[self.active_line])))

    def _insert(self, text):
        """Insert text (may contain newlines) at the cursor."""
        line = self.lines[self.active_line]
        before, after = line[:self.col], line[self.col:]
        parts = text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    ").split("\n")
        if len(parts) == 1:
            self.lines[self.active_line] = before + parts[0] + after
            self.col += len(parts[0])
        else:
            self.lines[self.active_line] = before + parts[0]
            new = parts[1:-1] + [parts[-1] + after]
            self.lines[self.active_line + 1:self.active_line + 1] = new
            self.active_line += len(parts) - 1
            self.col = len(parts[-1])
        self._touch()

    def _paste(self):
        try:
            if hasattr(pygame.scrap, "get_text"):          # pygame 2.2+ / pygame-ce
                text = pygame.scrap.get_text()
            else:
                if not pygame.scrap.get_init():
                    pygame.scrap.init()
                raw = pygame.scrap.get(pygame.SCRAP_TEXT)
                text = raw.decode("utf-8", "ignore").rstrip("\x00") if raw else ""
        except Exception:
            text = ""
        if text:
            self._insert(text)

    def _col_from_x(self, line, px):
        """Character index in `line` closest to pixel offset px."""
        for i in range(len(line) + 1):
            if self.font.size(line[:i])[0] >= px:
                if i > 0 and px < (self.font.size(line[:i - 1])[0] + self.font.size(line[:i])[0]) / 2:
                    return i - 1
                return i
        return len(line)

    # ---- events ----
    def handle_event(self, event):
        if event.type == pygame.TEXTINPUT:
            self._insert(event.text)
            self._ensure_visible()
            return
        if event.type == pygame.MOUSEWHEEL:
            max_scroll = max(0, len(self.lines) - self._visible_lines())
            self.scroll = max(0, min(max_scroll, self.scroll - event.y * 3))
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            row = (event.pos[1] - self.rect.y - 5) // self.line_height
            self.active_line = max(0, min(len(self.lines) - 1, self.scroll + row))
            px = event.pos[0] - (self.rect.x + self.gutter_width + 6)
            self.col = self._col_from_x(self.lines[self.active_line], px)
            self.cursor_blink = 0.0
            return
        if event.type != pygame.KEYDOWN:
            return

        ctrl = event.mod & (pygame.KMOD_CTRL | pygame.KMOD_META)
        line = self.lines[self.active_line]

        if ctrl and event.key == pygame.K_v:
            self._paste()
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            before = line[:self.col]
            indent = len(before) - len(before.lstrip(" "))
            if before.rstrip().endswith(":"):
                indent += 4
            self._insert("\n" + " " * indent)
        elif event.key == pygame.K_BACKSPACE:
            if self.col > 0:
                # remove a whole indent level when only spaces are left of the cursor
                n = 4 if line[:self.col].strip() == "" and self.col % 4 == 0 else 1
                self.lines[self.active_line] = line[:self.col - n] + line[self.col:]
                self.col -= n
            elif self.active_line > 0:
                prev = self.lines[self.active_line - 1]
                self.lines[self.active_line - 1] = prev + line
                self.lines.pop(self.active_line)
                self.active_line -= 1
                self.col = len(prev)
            self._touch()
        elif event.key == pygame.K_DELETE:
            if self.col < len(line):
                self.lines[self.active_line] = line[:self.col] + line[self.col + 1:]
            elif self.active_line < len(self.lines) - 1:
                self.lines[self.active_line] = line + self.lines.pop(self.active_line + 1)
            self._touch()
        elif event.key == pygame.K_TAB:
            self._insert("    ")
        elif event.key == pygame.K_LEFT:
            if self.col > 0:
                self.col -= 1
            elif self.active_line > 0:
                self.active_line -= 1
                self.col = len(self.lines[self.active_line])
        elif event.key == pygame.K_RIGHT:
            if self.col < len(line):
                self.col += 1
            elif self.active_line < len(self.lines) - 1:
                self.active_line += 1
                self.col = 0
        elif event.key == pygame.K_UP and self.active_line > 0:
            self.active_line -= 1
            self._clamp_col()
        elif event.key == pygame.K_DOWN and self.active_line < len(self.lines) - 1:
            self.active_line += 1
            self._clamp_col()
        elif event.key == pygame.K_HOME:
            stripped = len(line) - len(line.lstrip(" "))
            self.col = stripped if self.col != stripped else 0
        elif event.key == pygame.K_END:
            self.col = len(line)
        self.cursor_blink = 0.0
        self._ensure_visible()

    def update(self, dt):
        self.cursor_blink += dt
        if self.flash > 0:
            self.flash = max(0.0, self.flash - dt * 4)

    def draw(self, screen):
        pygame.draw.rect(screen, (30, 30, 34), self.rect, border_radius=6)
        pygame.draw.rect(screen, (60, 60, 68), self.rect, 2, border_radius=6)

        clip = screen.get_clip()
        screen.set_clip(self.rect.inflate(-4, -4))

        visible = self._visible_lines()
        active_row = self.active_line - self.scroll
        if 0 <= active_row < visible:
            hy = self.rect.y + 5 + active_row * self.line_height
            hl = pygame.Surface((self.rect.width - 4, self.line_height), pygame.SRCALPHA)
            alpha = 26 + int(self.flash * 55)
            hl.fill((100, 180, 255, alpha))
            screen.blit(hl, (self.rect.x + 2, hy))

        gutter_rect = pygame.Rect(self.rect.x, self.rect.y, self.gutter_width, self.rect.height)
        pygame.draw.rect(screen, (25, 25, 29), gutter_rect)

        text_x = self.rect.x + self.gutter_width + 6
        for row in range(visible):
            i = self.scroll + row
            if i >= len(self.lines):
                break
            y = self.rect.y + 5 + row * self.line_height
            num_color = (150, 210, 255) if i == self.active_line else (85, 85, 95)
            num_surf = self.font.render(str(i + 1).rjust(3), True, num_color)
            screen.blit(num_surf, (self.rect.x + 4, y))

            x = text_x
            for text, color in tokenize(self.lines[i]):
                seg = self.font.render(text, True, color)
                screen.blit(seg, (x, y))
                x += seg.get_width()

            if i == self.active_line and (self.cursor_blink % 1.0) < 0.6:
                cx = text_x + self.font.size(self.lines[i][:self.col])[0]
                pygame.draw.line(screen, (230, 230, 230), (cx + 1, y), (cx + 1, y + 16), 2)

        screen.set_clip(clip)
