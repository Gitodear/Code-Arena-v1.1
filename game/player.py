class Player:
    def __init__(self, x, y):
        self.start_x = x
        self.start_y = y
        self.x = x
        self.y = y

    def reset(self):
        self.x = self.start_x
        self.y = self.start_y

    def move(self, dx, dy, world):
        self.x = max(0, min(world.size - 1, self.x + dx))
        self.y = max(0, min(world.size - 1, self.y + dy))
