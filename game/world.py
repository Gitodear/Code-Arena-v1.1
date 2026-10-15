import random

CROP_TYPES = ["carrot", "tomato", "corn", "pumpkin"]


class World:
    """A square grid farm with harvestable crops scattered on it."""

    def __init__(self, size=8, crop_count=None, seed=None):
        self.size = size
        self.crop_count = crop_count if crop_count is not None else size * 2
        self.rng = random.Random(seed)
        self.resources = {}  # (x, y) -> crop_type
        self.harvested_count = 0
        self.total_crops = 0
        self.reset()

    def reset(self):
        cells = [(x, y) for y in range(self.size) for x in range(self.size)]
        count = min(self.crop_count, len(cells))
        # sample() gives unique cells, so there are always exactly `count` crops
        self.resources = {pos: self.rng.choice(CROP_TYPES) for pos in self.rng.sample(cells, count)}
        self.harvested_count = 0
        self.total_crops = count

    def has_resource(self, x, y):
        return (x, y) in self.resources

    def crop_at(self, x, y):
        return self.resources.get((x, y))

    def harvest_at(self, x, y):
        if (x, y) in self.resources:
            del self.resources[(x, y)]
            self.harvested_count += 1
            return True
        return False

    @property
    def all_harvested(self):
        return not self.resources
