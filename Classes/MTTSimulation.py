import math
import heapq
import numpy as np
import random
from Classes.Grid import Grid

class MTTSimulation:
    """
    Minimum Travel Time (MTT) fire spread simulation

    Implements Dijkstra's algorithm over a 2D grid to compute ignition times for cells.
    Using the ST-X-3 Fire Behaviour Prediction (FBP) system.

    Usage:
        sim = MTTSimulation(grid, dt=60)
        sim.Ignite(row, col)                # or sim.IgniteRandom(n)
        sim.Solve()
        history = sim.history               # time stepped history snapshots

    """

    def __init__(self, grid, dt=60):
        """
        :param grid: Grid object containing weather, terrain, and ROS data.
                     Expected attributes populated by Fire_Spread.roscalculation():
                       grid.ros  - 2D float, head-fire ROS in m/s
                       grid.wsv  - 2D float, net effective wind speed in km/h
                       grid.raz  - 2D float, resultant spread azimuth in degrees
                     And terrain/state attributes:
                       grid.gridSize  - int
                       grid.cellSize  - float, metres per cell
                       grid.state     - 2D int array (Grid.BURNING / UNBURNED / BURNED_OUT)
                       grid.water     - 2D bool array
                       grid.trees     - 2D bool array
        :param dt: Time step in seconds used when building history snapshots.
                   Does not affect accuracy of MTT ignition times.
        """
        self.grid = grid
        self.dt = dt

        # Filled by Solve()
        self.ignitionTime = None
        self.history = []  # list of {'time': float, 'state': ndarray}

    def Ignite(self, x, y):
        """
        Ignites a single cell at time 0.
        :param x: Row index.
        :param y: Column index.
        """
        self.grid.state[x, y] = Grid.BURNING

    def IgniteRandom(self, numCells):
        """
        Ignites numCells non-water cells at random.
        :param numCells: Number of cells to ignite.
        :raises ValueError: If there are not enough non-water cells.
        """
        nonWater = [
            (x, y)
            for x in range(self.grid.gridSize)
            for y in range(self.grid.gridSize)
            if not self.grid.water[x][y]
        ]

        if len(nonWater) < numCells:
            raise ValueError(f"Not enough non-water cells to ignite {numCells} cells")

        for x, y in random.sample(nonWater, numCells):
            self.Ignite(x, y)

    def Solve(self, maxFrames=100):
        """
        Runs the MTT solver.

        Executes Dijkstra's algorithm over the grid to compute exact ignition
        times, then reconstructs time-stepped history snapshots for visualisation.

        Call Ignite() or IgniteRandom() before calling Solve().
        """
        self._burnoutGrid = self._BurnoutTimeGrid()  # compute once, reuse everywhere
        self.ignitionTime = self._Dijkstra()
        x, y = self.grid.gridSize // 2, self.grid.gridSize // 2
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            ros = self._DirectionalROS(x, y, dx, dy)
            print(f"dx={dx:+d} dy={dy:+d} ROS={ros:.4f}")
        self.history = self._BuildHistory(maxFrames=maxFrames)

    def _Dijkstra(self):
        """
        Computes ignition times via Dijkstra's shortest-path algorithm.
        Each edge weight is the travel time in seconds for fire to cross
        from a burning cell to an unburned neighbour.

        Extinction is considered during propagation.

        :return: 2D float array of ignition times in seconds; inf = unreachable.
        """
        INF = float('inf')
        size = self.grid.gridSize
        ignitionTime = np.full((size, size), INF, dtype=float)
        burnoutGrid = self._burnoutGrid

        heap = []

        # Seed with all cells already ignited before Solve() is called
        for x in range(size):
            for y in range(size):
                if self.grid.state[x][y] == Grid.BURNING:
                    ignitionTime[x][y] = 0.0
                    heapq.heappush(heap, (0.0, x, y))

        while heap:
            time, x, y = heapq.heappop(heap)

            # A shorter path was already found
            if time > ignitionTime[x][y]:
                continue

            # Source cell burns out at its ignition time + its burnout duration
            burnout_time = ignitionTime[x][y] + burnoutGrid[x][y]

            for nx, ny in self._GetNeighbours(x, y):
                if self.grid.water[nx][ny]:
                    continue

                arrival = time + self._TravelTime(x, y, nx, ny)

                # Source cell must still be burning when fire reaches neighbour
                if arrival > burnout_time:
                    continue

                if arrival < ignitionTime[nx][ny]:
                    ignitionTime[nx][ny] = arrival
                    heapq.heappush(heap, (arrival, nx, ny))

        return ignitionTime

    def _DirectionalROS(self, x, y, dx, dy):
        """
        Rate of spread (m/s) from cell (x, y) in direction (dx, dy).

        Uses the polar form of the spread ellipse
        The ellipse axis is oriented along RAZ
        computed by Fire_Spread from the combined wind + slope vector (ST-X-3 eq 50).
        LB ratio is derived from WSV — the net effective wind speed (ST-X-3 eq 49).

        :param x:  Source cell row.
        :param y:  Source cell column.
        :param dx: Row component of spread direction (un-normalised).
        :param dy: Column component of spread direction (un-normalised).
        :return:   ROS in m/s; never negative.
        """
        ros_head = float(self.grid.ros[x][y])

        # no spread if <= 0
        if ros_head <= 0.0:
            return 0.0

        # Convert raz (net effective wind direction) to radians
        # Convert raz to a 2D unit vector
        # this unit vector points in the direction fire spreads fastest
        razRad = math.radians(self.grid.raz[x][y])
        xAxis = -math.cos(razRad)
        yAxis = math.sin(razRad)

        # LB ratio from WSV
        wsv = float(self.grid.wsv[x][y])
        if self.grid.trees[x][y]:
            # LB Ratio ST-X-3 Eq 79 All fuel axcept O-1
            LB = 1.0 + 8.729 * (1.0 - math.exp(-0.030 * wsv)) ** 2.155  # C-2
        else:
            # Lb Ratio ST-X-3 Eq 80/81 O-1 fuel
            if wsv >= 1.0:
                LB = 1.1 + wsv ** 0.464
            else:
                LB = 1.0
        LB = max(LB, 1.0) # Shouldnt be below 1

        # head-to-back ratio
        HB = (LB + math.sqrt(LB ** 2 - 1.0)) / max(LB - math.sqrt(LB ** 2 - 1.0), 1e-9)

        #TODO: Full ST-X-3 equation including BUI/BE. Requires drought data
        ros_back = ros_head / HB

        # Ellipse geometry
        b = (ros_head + ros_back) / 2.0  # semi-major axis
        c = (ros_head - ros_back) / 2.0  # focus offset
        a = b / LB  # semi-minor axis

        # Angle between spread direction and head-fire axis
        spread_len = math.sqrt(dx ** 2 + dy ** 2)
        cos_theta = (dx * xAxis + dy * yAxis) / spread_len
        cos_theta = max(-1.0, min(1.0, cos_theta))
        sin_theta = math.sqrt(max(0.0, 1.0 - cos_theta ** 2))

        denom = math.sqrt((a * cos_theta) ** 2 + (b * sin_theta) ** 2)
        return (a * (c * cos_theta + b)) / max(denom, 1e-9)

    def _TravelTime(self, x, y, nx, ny):
        """
        Time in seconds for fire to travel from (x, y) to neighbour (nx, ny).
        Diagonal neighbours are correctly weighted by sqrt(2) via the distance term.

        :return: Travel time in seconds. inf if ROS is zero.
        """
        dx, dy = nx - x, ny - y
        distance_m = math.sqrt(dx ** 2 + dy ** 2) * self.grid.cellSize
        ros = self._DirectionalROS(x, y, dx, dy)
        if ros <= 0.0:
            return float('inf')
        return distance_m / ros

    def _GetNeighbours(self, x, y):
        """
        Yields the 8-connected neighbours of (x, y) within grid bounds.

        :return: Generator of (nx, ny) tuples.
        """
        size = self.grid.gridSize
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < size and 0 <= ny < size:
                yield nx, ny

    def _BuildHistory(self, maxFrames=200):
        """
        Reconstructs time-stepped state snapshots from the ignitionTime raster.

        :return: List of {'time': float, 'state': ndarray} dicts.
        """
        finite = self.ignitionTime[self.ignitionTime != float('inf')]
        if finite.size == 0:
            return []

        maxTime = float(finite.max())
        burnoutGrid = self._burnoutGrid

        # Compute how many raw steps there would be, then stride to cap frames
        totalSteps = int(maxTime / self.dt) + 2
        step = max(1, totalSteps // maxFrames)

        history = []
        t = 0.0
        i = 0
        while t <= maxTime + self.dt:
            if i % step == 0:
                state = np.full(
                    (self.grid.gridSize, self.grid.gridSize),
                    Grid.UNBURNED,
                    dtype=int
                )
                ignitedMask = self.ignitionTime <= t
                burnedOutMask = self.ignitionTime <= (t - burnoutGrid)
                state[ignitedMask] = Grid.BURNING
                state[burnedOutMask] = Grid.BURNED_OUT
                history.append({'time': round(t, 2), 'state': state})  # drop .copy() too
            t += self.dt
            i += 1

        return history

    def _BurnoutTimeGrid(self):
        ISI_MIN = 5.0
        ISI_MAX = 20.0
        GRASS_FUEL_LOAD = 0.4
        TREE_FUEL_LOAD = 3.0

        fuelLoad = np.where(self.grid.trees, TREE_FUEL_LOAD, GRASS_FUEL_LOAD)
        fuelScale = fuelLoad / GRASS_FUEL_LOAD

        ros = np.maximum(self.grid.ros, 1e-9)
        baseBurnout = self.grid.cellSize / ros

        # Per-cell LB from WSV
        wsv = self.grid.wsv
        lbGrass = np.where(wsv >= 1.0, 1.1 + wsv ** 0.464, 1.0)
        lbTrees = 1.0 + 8.729 * (1.0 - np.exp(-0.030 * wsv)) ** 2.155
        LB = np.where(self.grid.trees, lbTrees, lbGrass)
        LB = np.maximum(LB, 1.0)

        # Absolute ISI normalisation
        isi = self.grid.isi
        isiNorm = np.clip((isi - ISI_MIN) / (ISI_MAX - ISI_MIN), 0.0, 1.0)

        # LB-scaled spread factor — burnout scales with ellipse elongation
        # so flank spread remains possible under good conditions
        spreadFactor = np.maximum(LB * isiNorm * 3.0, 0.5)

        return baseBurnout * fuelScale * spreadFactor

    def ArrivalTimeAt(self, x, y):
        """
        Returns the ignition time at cell (x, y) in seconds.

        :return: float; inf if the cell was never reached.
        :raises RuntimeError: If Solve() has not been called.
        """
        if self.ignitionTime is None:
            raise RuntimeError("Call Solve() before querying ignition times.")
        return float(self.ignitionTime[x][y])

    def FirePerimeterAt(self, t):
        """
        Returns a boolean mask of cells that are burning at time t.

        :param t: Time in seconds.
        :return:  2D bool array; True where state == BURNING at time t.
        :raises RuntimeError: If Solve() has not been called.
        """
        if self.ignitionTime is None:
            raise RuntimeError("Call Solve() before querying the perimeter.")
        burnoutGrid = self._burnoutGrid
        ignited = self.ignitionTime <= t
        burnedOut = self.ignitionTime <= (t - burnoutGrid)
        return ignited & ~burnedOut