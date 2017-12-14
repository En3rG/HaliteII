
import numpy
from heapq import *

## SAW THIS A* ALGO ONLINE FROM Christian Careaga (christian.careaga7@gmail.com)
## UPDATED FOR CLARITY

OBSTRUCTION = -100

def heuristic(a, b):
    """
    IS THE DISTANCE, IF TAKEN THE SQRT
    """
    return (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2

def isBadNeighbor(array,neighbor):
    """
    CHECKS IF THE NEIGHBOR IS WITHIN THE ARRAY
    OR IF THE NEIGHBOR IS AN OBSTRUCTION
    """
    if 0 <= neighbor[0] < array.shape[0]:
        if 0 <= neighbor[1] < array.shape[1]:
            ## NEIGHBOR COORDINATE IS WITHIN THE ARRAY
            if array[neighbor[0]][neighbor[1]] == OBSTRUCTION:
                ## ITS AN OBSTRUCTION (BAD/SKIP)
                return True
            else:
                return False ## VALID NEIGHBOR
        else:
            # OUTSIDE ARRAY Y WALLS (BAD/SKIP)
            return True
    else:
        # OUTSIDE ARRAY X WALLS (BAD/SKIP)
        return True

def a_star(array, start, goal):
    ## NEIGHBORS IN NORTH, EAST, SOUTH, WEST DIRECTIONS, PLUS DIAGONALS
    neighbors = [(-1,0),(0,1),(1,0),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]

    visited_coords = set()
    came_from = {}
    gscore = {start:0} ## ACTUAL DISTANCE FROM START
    fscore = {start:heuristic(start, goal)} ## GSCORE PLUS DISTANCE TO GOAL
    myheap = []

    ## HEAP CONSIST OF FSCORE, COORD
    heappush(myheap, (fscore[start], start))

    while myheap:

        current_coord = heappop(myheap)[1]

        if current_coord == goal: ## GOAL REACHED
            data = []
            while current_coord in came_from:
                data.append(current_coord)
                current_coord = came_from[current_coord]
            return data

        visited_coords.add(current_coord)
        for r, c in neighbors:
            neighbor_coord = current_coord[0] + r, current_coord[1] + c
            tentative_g_score = gscore[current_coord] + heuristic(current_coord, neighbor_coord)

            if isBadNeighbor(array, neighbor_coord):
                continue

            if neighbor_coord in visited_coords and tentative_g_score >= gscore.get(neighbor_coord, 0): ## 0 DEFAULT VALUE
                continue

            ## IF A BETTER GSCORE IF FOUND FOR THAT NEIGHBOR COORD OR NEIGHBOR COORD NOT IN HEAP
            if  tentative_g_score < gscore.get(neighbor_coord, 0) or neighbor_coord not in (i[1] for i in myheap):
                came_from[neighbor_coord] = current_coord   ## NEIGHBOR COORD CAME FROM CURRENT COORD
                gscore[neighbor_coord] = tentative_g_score  ## NEIGHBOR DISTANCE FROM START
                fscore[neighbor_coord] = tentative_g_score + heuristic(neighbor_coord, goal)  ## GSCORE PLUS DISTANCE TO GOAL
                heappush(myheap, (fscore[neighbor_coord], neighbor_coord))  ## PUSH NEIGHBOR TO HEAP

    return False

'''Here is an example of using my algo with a numpy array,
   astar(array, start, destination)
   astar function returns a list of points (shortest path)'''

# nmap = numpy.array([
#     [0,0,0,0,0,0,0,0,0,0,0,0,0,0],
#     [1,1,1,1,1,1,1,1,1,1,1,1,0,1],
#     [0,0,0,0,0,0,0,0,0,0,0,0,0,0],
#     [1,0,1,1,1,1,1,1,1,1,1,1,1,1],
#     [0,0,0,0,0,0,0,0,0,0,0,0,0,0],
#     [1,1,1,1,1,1,1,1,1,1,1,1,0,1],
#     [0,0,0,0,0,0,0,0,0,0,0,0,0,0],
#     [1,0,1,1,1,1,1,1,1,1,1,1,1,1],
#     [0,0,0,0,0,0,0,0,0,0,0,0,0,0],
#     [1,1,1,1,1,1,1,1,1,1,1,1,0,1],
#     [0,0,0,0,0,0,0,0,0,0,0,0,0,0]])
#
# start = datetime.datetime.now()
# path = a_star(nmap, (0,0), (10,13))
# print("Length: {} Path: {}".format(len(path),path))
# print(used)