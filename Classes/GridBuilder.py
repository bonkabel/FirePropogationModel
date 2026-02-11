from Classes.Grid import Grid


class GridBuilder:
    def __init__(self, width, height):
        self.width = width
        self.height = height

    def Build(self):
        grid = Grid(self.width, self.height)

        #logic

        return grid