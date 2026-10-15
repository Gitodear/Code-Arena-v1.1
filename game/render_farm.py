import math
import random
import pygame

SOIL_LIGHT = (96, 63, 32)
SOIL_DARK = (78, 50, 24)
SOIL_FURROW = (58, 37, 17)

_speckle_cache = {}


def draw_soil_tile(screen, rect, gx, gy):
    """Draws a tilled-earth look: alternating shade, furrow lines, and a few
    deterministic speckle dots (deterministic so it doesn't shimmer every frame)."""
    base = SOIL_LIGHT if (gx + gy) % 2 == 0 else SOIL_DARK
    pygame.draw.rect(screen, base, rect, border_radius=2)

    for i in (1, 2):
        y = rect.y + rect.height * i // 3
        pygame.draw.line(screen, SOIL_FURROW, (rect.x + 3, y), (rect.right - 3, y), 1)

    key = (gx, gy)
    if key not in _speckle_cache:
        rng = random.Random(gx * 1000 + gy)
        _speckle_cache[key] = [
            (rng.randint(3, rect.width - 4), rng.randint(3, rect.height - 4)) for _ in range(3)
        ]
    for dx, dy in _speckle_cache[key]:
        pygame.draw.circle(screen, SOIL_FURROW, (rect.x + dx, rect.y + dy), 1)


def draw_crop(screen, cx, cy, crop_type):
    if crop_type == "carrot":
        green = (70, 170, 70)
        pygame.draw.line(screen, green, (cx, cy - 2), (cx - 4, cy - 10), 2)
        pygame.draw.line(screen, green, (cx, cy - 2), (cx, cy - 12), 2)
        pygame.draw.line(screen, green, (cx, cy - 2), (cx + 4, cy - 10), 2)
        pygame.draw.polygon(screen, (230, 126, 34), [(cx - 5, cy - 2), (cx + 5, cy - 2), (cx, cy + 10)])
        pygame.draw.polygon(screen, (200, 100, 25), [(cx - 5, cy - 2), (cx, cy - 2), (cx - 1, cy + 8)])

    elif crop_type == "tomato":
        pygame.draw.circle(screen, (200, 50, 50), (cx, cy + 2), 7)
        pygame.draw.circle(screen, (230, 90, 80), (cx - 2, cy), 2)
        pygame.draw.line(screen, (70, 160, 70), (cx - 3, cy - 6), (cx, cy - 4), 2)
        pygame.draw.line(screen, (70, 160, 70), (cx + 3, cy - 6), (cx, cy - 4), 2)

    elif crop_type == "corn":
        pygame.draw.rect(screen, (240, 200, 60), (cx - 4, cy - 9, 8, 17), border_radius=3)
        for i in range(-6, 9, 4):
            pygame.draw.line(screen, (200, 160, 40), (cx - 4, cy + i), (cx + 4, cy + i), 1)
        pygame.draw.polygon(screen, (90, 150, 70), [(cx - 4, cy - 9), (cx - 8, cy - 15), (cx - 1, cy - 9)])
        pygame.draw.polygon(screen, (90, 150, 70), [(cx + 4, cy - 9), (cx + 8, cy - 15), (cx + 1, cy - 9)])

    elif crop_type == "pumpkin":
        pygame.draw.circle(screen, (225, 120, 30), (cx, cy + 2), 8)
        pygame.draw.line(screen, (170, 90, 20), (cx - 6, cy + 2), (cx + 6, cy + 2), 1)
        pygame.draw.line(screen, (170, 90, 20), (cx, cy - 5), (cx, cy + 9), 1)
        pygame.draw.rect(screen, (90, 140, 60), (cx - 1, cy - 10, 2, 5))


def draw_player(screen, cx, cy, hoe_angle_deg):
    """Small farmer figure: body, straw hat, and a hoe that rotates around
    hoe_angle_deg (used to animate a swing when harvesting)."""
    pygame.draw.circle(screen, (60, 40, 20), (cx, cy + 2), 11)  # shadow/body base
    pygame.draw.circle(screen, (240, 200, 130), (cx, cy), 9)     # skin/body
    pygame.draw.ellipse(screen, (150, 100, 50), (cx - 12, cy - 13, 24, 7))   # hat brim
    pygame.draw.ellipse(screen, (180, 130, 70), (cx - 6, cy - 17, 12, 8))    # hat top

    length = 17
    rad = math.radians(hoe_angle_deg)
    ex = cx + math.cos(rad) * length
    ey = cy + math.sin(rad) * length
    pygame.draw.line(screen, (120, 80, 40), (cx, cy), (ex, ey), 2)

    perp = math.radians(hoe_angle_deg + 90)
    bx1, by1 = ex + math.cos(perp) * 4, ey + math.sin(perp) * 4
    bx2, by2 = ex - math.cos(perp) * 4, ey - math.sin(perp) * 4
    pygame.draw.line(screen, (190, 190, 200), (bx1, by1), (bx2, by2), 3)
