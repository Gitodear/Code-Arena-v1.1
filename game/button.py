import pygame


class Button:
    def __init__(self, x, y, w, h, text, color):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

    def draw(self, screen, font):
        pygame.draw.rect(screen, self.color, self.rect, border_radius=6)
        text_surf = font.render(self.text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)
