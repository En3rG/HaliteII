
import numpy
from heapq import *
import logging
import MyCommon
import datetime
import time


NON_OBSTRUCTION = 0


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
            if array[neighbor[0]][neighbor[1]] == NON_OBSTRUCTION:
                return False ## VALID NEIGHBOR
            else:
                ## ITS AN OBSTRUCTION (BAD/SKIP)
                return True
        else:
            # OUTSIDE ARRAY Y WALLS (BAD/SKIP)
            return True
    else:
        # OUTSIDE ARRAY X WALLS (BAD/SKIP)
        return True

def a_star(array, start_point, goal_point):
    """
    A* ALGO TO GET THE BEST PATH FROM start TO goal

    SAW THIS A* ALGO ONLINE FROM Christian Careaga (christian.careaga7@gmail.com)
    UPDATED FOR CLARITY
    """
    ## MAKE SURE COORDS ARE ROUNDED AS INTS
    start = (int(round(start_point[0])),int(round(start_point[1])))
    goal = (int(round(goal_point[0])),int(round(goal_point[1])))

    logging.debug("a_star: start: {} goal: {}".format(start, goal))

    ## NEIGHBORS IN NORTH, EAST, SOUTH, WEST DIRECTIONS, PLUS DIAGONALS
    neighbors = [(-1,0),(0,1),(1,0),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]

    visited_points = set()
    came_from = {}
    gscore = {start:0}                      ## ACTUAL DISTANCE FROM START
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
            ## tentative_g_score IS BASICALLY THE DISTANCE/STEPS AWAY FROM START
            tentative_g_score = gscore[current_point] + heuristic(current_point, neighbor_point)

            if isBadNeighbor(array, neighbor_point):
                continue

            if neighbor_point in visited_points and tentative_g_score >= gscore.get(neighbor_point, 0): ## 0 DEFAULT VALUE
                continue

            ## IF A BETTER GSCORE IS FOUND FOR THAT NEIGHBOR COORD OR NEIGHBOR COORD NOT IN HEAP
            if  tentative_g_score < gscore.get(neighbor_point, 0) or neighbor_point not in (i[1] for i in myheap):
                came_from[neighbor_point] = current_point   ## NEIGHBOR COORD CAME FROM CURRENT COORD
                gscore[neighbor_point] = tentative_g_score  ## NEIGHBOR DISTANCE FROM START
                fscore[neighbor_point] = tentative_g_score + heuristic(neighbor_point, goal)  ## GSCORE PLUS DISTANCE TO GOAL
                heappush(myheap, (fscore[neighbor_point], neighbor_point))  ## PUSH NEIGHBOR TO HEAP

    return []


def a_star2(arrays, start_point, goal_point):
    """
    A* ALGO TO GET THE BEST PATH FROM start TO goal

    UPDATED A* ABOVE, THIS TIME IT WILL TAKE MULTIPLE ARRAYS (INCLUDING INTERMEDIATE STEPS)

    ARRAY WILL BE A DICTIONARY OF STEPSe
    """
    ## MAKE SURE COORDS ARE ROUNDED AS INTS
    start = (int(round(start_point[0])),int(round(start_point[1])))
    goal = (int(round(goal_point[0])),int(round(goal_point[1])))

    ## HOW FAR AWAY IS THE GOAL DISTANCE
    goal_distance = MyCommon.calculate_distance(MyCommon.Coordinates(start_point[0], start_point[1]),
                                                MyCommon.Coordinates(goal_point[0], goal_point[1]))
    goal_distance = min(7, goal_distance)  ## SOMETIMES GOAL CAN BE VERY FAR, BUT LIMIT TO 7 ONLY


    index_per_step = 7/goal_distance  ## THIS WILL BE THE INCREASE IN INDEX (POSITION MATRIX) PER STEP

    logging.debug("a_star: start: {} goal: {}".format(start, goal))

    ## NEIGHBORS IN NORTH, EAST, SOUTH, WEST DIRECTIONS, PLUS DIAGONALS
    neighbors = [(-1,0),(0,1),(1,0),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]

    visited_points = set()
    came_from = {}
    gscore = {start:0}                      ## ACTUAL DISTANCE FROM START
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
            ## tentative_g_score IS BASICALLY THE DISTANCE/STEPS AWAY FROM START
            tentative_g_score = gscore[current_point] + heuristic(current_point, neighbor_point)

            ## HIGHEST INDEX CAN ONLY BE 7 STEPS (WE ONLY HAVE 7 POSITION MATRIX)
            index_value = min(7, int(round(tentative_g_score * index_per_step)))

            ## BASE ON INDEX IN POSITION MATRIX
            ## THIS IS TO TAKE INTO ACCOUNT INTERMEDIATE STEPS
            if isBadNeighbor(arrays[index_value], neighbor_point):
                continue

            if neighbor_point in visited_points and tentative_g_score >= gscore.get(neighbor_point, 0): ## 0 DEFAULT VALUE
                continue

            ## IF A BETTER GSCORE IS FOUND FOR THAT NEIGHBOR COORD OR NEIGHBOR COORD NOT IN HEAP
            if  tentative_g_score < gscore.get(neighbor_point, 0) or neighbor_point not in (i[1] for i in myheap):
                came_from[neighbor_point] = current_point   ## NEIGHBOR COORD CAME FROM CURRENT COORD
                gscore[neighbor_point] = tentative_g_score  ## NEIGHBOR DISTANCE FROM START
                fscore[neighbor_point] = tentative_g_score + heuristic(neighbor_point, goal)  ## GSCORE PLUS DISTANCE TO GOAL
                heappush(myheap, (fscore[neighbor_point], neighbor_point))  ## PUSH NEIGHBOR TO HEAP

    return []


def simplify_paths(path_points):
    """
    SIMPLIFY PATH.  COMBINE MOVEMENT WITH THE SAME SLOPES
    NEED TO MAXIMIZE THRUST OF 7 (MAX)
    """
    if path_points != []:
        simplified_path = [path_points[-1]]
        prev_point = path_points[-1]
        prev_angle = None
        tempCoord = None
        prev_distance = 0
        length = len(path_points) - 1  ## MINUS THE PREVIOUS

        ## SINCE STARTING IS AT THE END, SKIP LAST ONE (PREV COORD)
        for i, current_point in enumerate(path_points[-2::-1], start=1):
            ## GATHER PREVIOUS AND CURRENT COORD
            prevCoord = MyCommon.Coordinates(prev_point[0], prev_point[1])
            currentCoord = MyCommon.Coordinates(current_point[0], current_point[1])

            current_angle = MyCommon.get_angle(prevCoord, currentCoord)
            current_distance = MyCommon.calculate_distance(prevCoord, currentCoord)

            if i == length:  ## IF ITS THE LAST ITEM
                if not(prev_distance + current_distance < 7 and (prev_angle is None or prev_angle == current_angle)):
                    simplified_path.append((tempCoord.y, tempCoord.x))  ## CAN NOT COMBINE, ADD TEMP COORD

                ## ADD LAST ITEM TO SIMPLIFIED LIST
                simplified_path.append((currentCoord.y, currentCoord.x))
            else:
                ## IF THE SAME SLOPE/ANGLE AS BEFORE AND STILL BELOW 7, CAN CONTINUE TO COMBINE/SIMPLIFY
                if prev_distance + current_distance < 7 and \
                        (prev_angle is None or prev_angle == current_angle):
                    ## PREV COORD WILL STAY AS PREV COORD
                    prev_distance = 0

                else:  ## CANT COMBINE, NEED TO CHANGE DIRECTION
                    simplified_path.append((tempCoord.y, tempCoord.x))
                    current_angle = MyCommon.get_angle(tempCoord, currentCoord)  ## NEW ANGLE FROM TEMP TO CURRENT

                    #currentCoord = MyCommon.Coordinates(current_point[0], current_point[1])
                    prev_point = (tempCoord.y, tempCoord.x)
                    prev_distance = MyCommon.calculate_distance(tempCoord, currentCoord)

                ## UPDATE FOR NEXT ITERATION
                tempCoord = currentCoord
                prev_angle = current_angle

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


# '''Here is an example of using my algo with a numpy array,
#    astar(array, start, destination)
#    astar function returns a list of points (shortest path)'''
#
# nmap = numpy.array([
#     [0,0,0,0,0,0,0,0,0,0,0,0,0,0],
#     [1,0,0,0,0,0,0,1,1,1,1,1,0,1],
#     [1,1,0,0,0,0,0,0,0,0,0,0,0,0],
#     [1,1,1,0,0,0,0,0,1,1,1,1,1,1],
#     [1,1,1,1,0,0,0,0,0,0,0,0,0,0],
#     [1,1,1,1,0,1,1,1,1,1,1,1,0,1],
#     [0,0,0,0,0,0,0,0,0,0,0,0,0,0],
#     [1,0,1,1,1,1,1,1,1,1,1,1,1,1],
#     [0,0,0,0,0,0,0,0,0,0,0,0,0,0],
#     [1,1,1,1,1,1,1,1,1,1,1,1,0,1],
#     [0,0,0,0,0,0,0,0,0,0,0,0,0,0]])
#
# arr = {1:nmap, 2:nmap, 3:nmap, 4:nmap ,5:nmap ,6:nmap, 7:nmap}
#
# start = datetime.datetime.now()
#
# path = a_star(nmap, (0,0), (5,4))
# #path = a_star2(arr, (0,0), (0,3))
#
# end = datetime.datetime.now()
# print("Length: {} Path: {}".format(len(path),path))
#
# print(end-start)

