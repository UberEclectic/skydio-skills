
from __future__ import print_function

# 0, 0 is bottom left corner
# x is 2nd coord

class Block(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.cells = [(0, 0), (0, 1), (1, 0), (1, 1)]

    def cells_pos(self):
        return [(x + self.x, y + self.y) for x, y in self.cells]

    def update(self, grid):
        """Move and return whether we stopped"""
        self.y -= 1
        for x, y in self.cells_pos():
            if grid[y-1][x]:
                return True
        return False

class Grid(object):
    def __init__(self):
        self.grid = [[i == 0] * 10 for i in range(23)]
        self.block = None

    def visible_cells(self):
        cells = []
        for y in range(1, 21):
            for x in range(10):
                if self.grid[y][x]:
                    cells.append((x, y))
        if self.block:
            cells.extend(self.block.cells_pos())
        return cells

    def update(self):
        if not self.block:
            self.block = Block(4, 20)
        if self.block.update(self.grid):
            if self.block.y >= 19:
                return False
            for x, y in self.block.cells_pos():
                self.grid[y][x] = True
            self.block = None
        return True

    def handle_action(self, action):
        if not self.block:
            return
        if action == 'left' and self.block.x > 0:
            self.block.x -= 1
        if action == 'right':
            self.block.x = min(8, self.block.x + 1)

def print_cells(cells):
    for y in range(21, 0, -1):
        line = [' ']*10
        for cell in cells:
            if cell[1] == y:
                line[cell[0]] = 'O'
        print(''.join(line))
    print('X' * 10)



if __name__ == '__main__':
    g = Grid()
    while g.update():
        print_cells(g.visible_cells())
