import math
import sys

import pygame

from game.world import World
from game.player import Player
from game.api import GameAPI
from game.runtime import ScriptRuntime
from game.editor import CodeEditor
from game.button import Button
from game import render_farm as rf

WIDTH, HEIGHT = 1000, 620
WORLD_PANEL_WIDTH = 400
CELL_SIZE = 40
GRID_SIZE = 8
TICK_RATE = 8      # bot ACTIONS per second - slow enough to watch
RENDER_FPS = 60    # game/UI refresh rate - keeps typing and rendering smooth
HOE_SWING_DURATION = 0.28
HOE_REST_ANGLE = 55
MAX_LOG_LINES = 7
MAX_LOG_CHARS = 70

DEFAULT_CODE = """# Write your bot code here, then press Run (F5)
# Available:
#   api.move(dx, dy)      dx, dy are -1, 0 or 1
#   api.harvest()
#   api.can_harvest()
#   api.get_pos()         returns (x, y)
#   api.get_world_size()
#   api.crops_left()
#   print(...)            shows in the Output panel

# Starter bot: sweep the farm row by row (snake pattern)
size = api.get_world_size()
direction = 1

for row in range(size):
    for step in range(size):
        if api.can_harvest():
            api.harvest()
        if step < size - 1:
            api.move(direction, 0)
    if row < size - 1:
        api.move(0, 1)
    direction = -direction

print("Sweep complete!", api.crops_left(), "crops left")
"""


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Code Arena - Practice")
    pygame.key.start_text_input()
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas,menlo,dejavusansmono,monospace", 16)
    small_font = pygame.font.SysFont("consolas,menlo,dejavusansmono,monospace", 14)

    world = World(GRID_SIZE)
    player = Player(0, 0)
    api = GameAPI(world, player)
    runtime = ScriptRuntime(api)

    editor = CodeEditor(WORLD_PANEL_WIDTH + 20, 20, WIDTH - WORLD_PANEL_WIDTH - 40, 400, font, DEFAULT_CODE)
    run_button = Button(WORLD_PANEL_WIDTH + 20, 440, 130, 36, "Run (F5)", (40, 140, 60))
    stop_button = Button(WORLD_PANEL_WIDTH + 160, 440, 130, 36, "Stop (Esc)", (140, 50, 50))
    farm_button = Button(WORLD_PANEL_WIDTH + 300, 440, 130, 36, "New Farm", (60, 90, 150))

    log_lines = []
    state = {"last_harvested": 0, "hoe_timer": 0.0, "won": False}
    action_timer = 0.0
    action_interval = 1.0 / TICK_RATE

    def add_log(msg):
        for part in str(msg).splitlines() or [""]:
            log_lines.append(part)
        del log_lines[:-MAX_LOG_LINES]

    def reset_farm():
        world.reset()
        player.reset()
        state.update(last_harvested=0, hoe_timer=0.0, won=False)

    def run_code():
        runtime.stop()
        reset_farm()
        if runtime.start(editor.get_code()):
            add_log("> Running...")

    def stop_code():
        if runtime.stop():
            add_log("> Stopped.")

    def new_farm():
        stop_code()
        reset_farm()
        add_log("> New farm generated.")

    running = True
    while running:
        dt = clock.tick(RENDER_FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F5:
                run_code()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                stop_code()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and run_button.is_clicked(event.pos):
                run_code()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and stop_button.is_clicked(event.pos):
                stop_code()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and farm_button.is_clicked(event.pos):
                new_farm()
            else:
                editor.handle_event(event)

        # --- one bot action per tick ---
        action_timer += dt
        if action_timer >= action_interval:
            action_timer -= action_interval
            api.process_pending()
            if world.harvested_count > state["last_harvested"]:
                state["last_harvested"] = world.harvested_count
                state["hoe_timer"] = HOE_SWING_DURATION
            if world.all_harvested and not state["won"]:
                state["won"] = True
                add_log(f"* All {world.total_crops} crops harvested!")

        if state["hoe_timer"] > 0:
            state["hoe_timer"] = max(0.0, state["hoe_timer"] - dt)

        editor.update(dt)

        for kind, text in runtime.poll_messages():
            prefix = {"err": "! ", "info": "> "}.get(kind, "")
            add_log(prefix + text)

        # --- draw ---
        screen.fill((22, 22, 26))

        pygame.draw.rect(screen, (14, 14, 17), (0, 0, WORLD_PANEL_WIDTH, HEIGHT))
        ox, oy = 20, 20
        for gy in range(world.size):
            for gx in range(world.size):
                rect = pygame.Rect(ox + gx * CELL_SIZE, oy + gy * CELL_SIZE, CELL_SIZE - 2, CELL_SIZE - 2)
                rf.draw_soil_tile(screen, rect, gx, gy)
                crop = world.crop_at(gx, gy)
                if crop:
                    rf.draw_crop(screen, rect.centerx, rect.centery, crop)

        if state["hoe_timer"] > 0:
            progress = 1 - (state["hoe_timer"] / HOE_SWING_DURATION)
            hoe_angle = HOE_REST_ANGLE - 80 * math.sin(math.pi * progress)
        else:
            hoe_angle = HOE_REST_ANGLE

        px = ox + player.x * CELL_SIZE + CELL_SIZE // 2
        py = oy + player.y * CELL_SIZE + CELL_SIZE // 2
        rf.draw_player(screen, px, py, hoe_angle)

        info_y = oy + world.size * CELL_SIZE + 10
        score = f"Harvested: {world.harvested_count} / {world.total_crops}"
        screen.blit(font.render(score, True, (230, 230, 230)), (ox, info_y))

        if runtime.running:
            status, status_color = "RUNNING", (100, 220, 100)
        elif state["won"]:
            status, status_color = "FARM CLEARED", (240, 200, 80)
        else:
            status, status_color = "IDLE", (150, 150, 150)
        screen.blit(small_font.render(f"Status: {status}", True, status_color), (ox, info_y + 25))
        hint = "F5 run  |  Esc stop  |  Ctrl+V paste"
        screen.blit(small_font.render(hint, True, (95, 95, 105)), (ox, info_y + 50))

        editor.draw(screen)
        run_button.draw(screen, font)
        stop_button.draw(screen, font)
        farm_button.draw(screen, font)

        log_y = 490
        screen.blit(small_font.render("Output:", True, (150, 150, 160)), (WORLD_PANEL_WIDTH + 20, log_y))
        log_y += 20
        for line in log_lines:
            if line.startswith("!"):
                color = (255, 120, 120)
            elif line.startswith("*"):
                color = (240, 200, 80)
            else:
                color = (200, 200, 200)
            text = line if len(line) <= MAX_LOG_CHARS else line[:MAX_LOG_CHARS - 3] + "..."
            screen.blit(small_font.render(text, True, color), (WORLD_PANEL_WIDTH + 20, log_y))
            log_y += 17

        pygame.display.flip()

    runtime.stop()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
