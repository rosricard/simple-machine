# input: a 2d grid that represents a floor layout
# we can travel within the squares labelled 1 but not the sqares labelled 0
# can travel horizontally and vertically but not diagonally
# the robot needs to know the size of the largest contiguous open region that it could patrol without crosisng obstacles
# return the count of cells of the largest connected region of 1s. 
# Return 0 if there are no 1s 

# edge cases: how solid is the input? does it HAVE to be 0 or 1? could it be null or something else? the grid isn't necessarily a perfect square

# brute force: nested loop through the list of lists where we check if there's a 1 and then check if there's a 1 next to it in the sub loop (todo: discuss the nuance of loop through a matrix to check both sides)
# this option would be O(m*n)^2
# can we do better? like O(N) time complexity? this 2D grid lends itself to either BFS / DFS O(mn)

# assumptions: what is the starting condition? because the problem says ANY largest area, it sounds like we have to check all boundary conditions?

# let's pick DFS because it's simpler recursively
def max_grid_area(grid : list[list[int]]) -> int:
    "find the largest patrol region"
    best = 0
    # things to watch out for : cyclic graph
    print(grid)

    # check for errors / edge condition, empty or null grid
    if not grid or not grid[0]:
        return 0

    rows, cols = len(grid), len(grid[0])

    def area_from(r, c):
        # check for out of bounds conditions + value check
        if r < 0 or r >= rows or c < 0 or c >= cols or grid[r][c] != 1:
            return 0
        grid[r][c] = 0 # mark visited
        # calculate the area of the unreachable parts
        # requires 4 recursive calls
         
        # add together all the recursive checks of up, down, left, right
        return (1 
            + area_from(r - 1, c)  # up
            + area_from(r + 1, c)  # down
            + area_from(r, c - 1)  # left
            + area_from(r, c + 1)) # right

    # outer loop scan
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 1:
                area = area_from(r,c)
                best = max(best,area)

    return best

if __name__ == "__main__":
    grid = [
    [1, 1, 0, 0],
    [1, 0, 0, 1],
    [0, 0, 1, 1],
    [0, 0, 1, 0],
    ]

    max_grid_area(grid)

# → 4   (bottom-right cluster of four 1s is the largest)