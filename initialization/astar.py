
import numpy
from heapq import *
import logging
import MyCommon



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
    """
    A* ALGO TO GET THE BEST PATH FROM start TO goal

    SAW THIS A* ALGO ONLINE FROM Christian Careaga (christian.careaga7@gmail.com)
    UPDATED FOR CLARITY
    """
    ## MAKE SURE COORDS ARE ROUNDED AS INTS
    start = (int(round(start[0])),int(round(start[1])))
    goal = (int(round(goal[0])),int(round(goal[1])))

    ## NEIGHBORS IN NORTH, EAST, SOUTH, WEST DIRECTIONS, PLUS DIAGONALS
    neighbors = [(-1,0),(0,1),(1,0),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]

    visited_points = set()
    came_from = {}
    gscore = {start:0} ## ACTUAL DISTANCE FROM START
    fscore = {start:heuristic(start, goal)} ## GSCORE PLUS DISTANCE TO GOAL
    myheap = []

    ## HEAP CONSIST OF FSCORE, COORD
    heappush(myheap, (fscore[start], start))

    while myheap:

        current_point = heappop(myheap)[1]

        if current_point == goal: ## GOAL REACHED
            data_points = []
            while current_point in came_from:
                data_points.append(current_point)
                current_point = came_from[current_point]
            data_points.append(start) ## APPEND STARTING LOCATION
            return data_points ## FIRST COORD WILL BE AT THE END!

        visited_points.add(current_point)
        for r, c in neighbors:
            neighbor_point = (current_point[0] + r, current_point[1] + c)
            tentative_g_score = gscore[current_point] + heuristic(current_point, neighbor_point)

            if isBadNeighbor(array, neighbor_point):
                continue

            if neighbor_point in visited_points and tentative_g_score >= gscore.get(neighbor_point, 0): ## 0 DEFAULT VALUE
                continue

            ## IF A BETTER GSCORE IF FOUND FOR THAT NEIGHBOR COORD OR NEIGHBOR COORD NOT IN HEAP
            if  tentative_g_score < gscore.get(neighbor_point, 0) or neighbor_point not in (i[1] for i in myheap):
                came_from[neighbor_point] = current_point   ## NEIGHBOR COORD CAME FROM CURRENT COORD
                gscore[neighbor_point] = tentative_g_score  ## NEIGHBOR DISTANCE FROM START
                fscore[neighbor_point] = tentative_g_score + heuristic(neighbor_point, goal)  ## GSCORE PLUS DISTANCE TO GOAL
                heappush(myheap, (fscore[neighbor_point], neighbor_point))  ## PUSH NEIGHBOR TO HEAP

    return []


def simplify_paths(path_coords):
    """
    SIMPLIFY PATH.  COMBINE MOVEMENT WITH THE SAME SLOPES
    NEED TO MAXIMIZE THRUST OF 7 (MAX)
    """
    #logging.info("Original path: {}".format(path_coords))

    if path_coords != []:
        simplified_path = [path_coords[-1]]
        prev_point = path_coords[-1]
        prev_angle = None
        tempCoord = None
        prev_distance = 0
        length = len(path_coords) - 1  ## MINUS THE PREVIOUS

        ## SINCE STARTING IS AT THE END, SKIP LAST ONE (PREV COORD)
        for i, current_point in enumerate(path_coords[-2::-1], start=1):
            ## GATHER PREVIOUS AND CURRENT COORD
            prevCoord = MyCommon.Coordinates(prev_point[0], prev_point[1])
            currentCoord = MyCommon.Coordinates(current_point[0], current_point[1])

            #logging.debug("prevCoord: {} currentCoord: {}".format(prevCoord,currentCoord))

            current_angle = MyCommon.get_angle(prevCoord, currentCoord)
            current_distance = MyCommon.calculate_distance(prevCoord, currentCoord)

            #logging.debug("current_angle: {} current_distance: {} prev_distance: {}".format(current_angle, current_distance, prev_distance))

            if i == length:  ## IF ITS THE LAST ITEM
                if not(prev_distance + current_distance < 7 and (prev_angle is None or prev_angle == current_angle)):
                    simplified_path.append((tempCoord.y, tempCoord.x))  ## CAN NOT COMBINE, ADD TEMP COORD

                ## ADD LAST ITEM TO SIMPLIFIED LIST
                simplified_path.append((currentCoord.y, currentCoord.x))
            else:
                ## IF THE SAME SLOPE/ANGLE AS BEFORE AND STILL BELOW 7, CAN CONTINUE TO COMBINE/SIMPLIFY
                if prev_distance + current_distance < 7 and \
                        (prev_angle is None or prev_angle == current_angle):
                    #logging.debug("Can continue")
                    ## PREV COORD WILL STAY AS PREV COORD
                    prev_distance = 0

                else:  ## CANT COMBINE, NEED TO CHANGE DIRECTION
                    #logging.debug("Cannot continue")
                    simplified_path.append((tempCoord.y, tempCoord.x))
                    current_angle = MyCommon.get_angle(tempCoord, currentCoord)  ## NEW ANGLE FROM TEMP TO CURRENT

                    #currentCoord = MyCommon.Coordinates(current_point[0], current_point[1])
                    prev_point = (tempCoord.y, tempCoord.x)
                    prev_distance = MyCommon.calculate_distance(tempCoord, currentCoord)

                ## UPDATE FOR NEXT ITERATION
                tempCoord = currentCoord
                prev_angle = current_angle


        #logging.info("simplified path: {}".format(simplified_path))



        return simplified_path

    return []


def get_start_target_table(simplified_path):
    """
    TAKES SIMPLIFIED PATH AND GENERATE A HASH TABLE
    KEY AS CURRENT COORD AND VALUE AS TARGET (DESTINATION) COORD
    """
    hash_table = {}

    if simplified_path != []:
        for i, coord in enumerate(simplified_path[:-1]):  ## SKIPPING LAST ELEMENT
            hash_table[coord] = simplified_path[i + 1]

    return hash_table

def get_Astar_table(matrix, starting_point, target_point):
    """
    GET PATH TABLE USING A* ALGO
    """
    path_points = a_star(matrix, starting_point, target_point)
    simplified_paths = simplify_paths(path_points)
    path_table_forward = get_start_target_table(simplified_paths)

    return path_table_forward, simplified_paths



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