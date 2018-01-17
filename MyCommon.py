import logging
import datetime
import numpy as np
import math
from enum import Enum
import heapq


class Constants():

    DISABLE_LOG = True
    MAX_TRAVEL_DISTANCE = 7
    ATTACK_RADIUS = 5
    DOCK_RADIUS = 4

    ## NEURAL NETWORK MODEL
    INPUT_MATRIX_Y = 27
    INPUT_MATRIX_X = 27
    INPUT_MATRIX_Z = 4
    NUM_EPOCH = 1 ## WAS 2, BUT MAY TIME OUT
    BATCH_SIZE = 300

    ## FOR MULTIPROCESSING
    MAX_DELAY = 1.875  ## TO MAXIMIZE TIME PER TURN
    WAIT_TIME = 0.750  ## WAIT TIME FOR PREDICTIONS TO GET INTO QUEUE
    GET_TIMEOUT = 0.005  ## TIMEOUT SET FOR .GET()

    ## FOR A* SECTIONED
    ASTAR_SQUARE_RADIUS = 8 ## 8.  WILL BE 17x17
    ASTAR_CIRCLE_RADIUS = 7 ## 7. 14 TIMES OUT
    FILL_PLANET_PAD = 1
    MOVE_BACK = 1
    NON_OBSTRUCTION = 0

    ## FOR DIVIDING WHOLE MAP INTO SECTIONS
    NUM_SECTIONS = 7  ## DIVIDES THE MAP INTO THESE SIZE SECTIONS
    SIZE_SECTIONS_RADIUS = 5

    BIG_DISTANCE = 9999

    ## ATTACKING
    MOVE_BACK_OFFENSE = 0       ## NO LONGER USED
    PERIMETER_CHECK_RADIUS = 14 ## CHECK ENEMY WITHIN PERIMETER TO ATTACK, IF FOUND GET SECTIONS
    ATTACKING_RADIUS = 14       ## CONSIDERED IN IMMINENT BATTLE
    BACKUP_CIRCLE_RADIUS = 14   ## RADIUS TO CHECK FOR BACKUP NEEDED
    BACKUP_SQUARE_RADIUS = 14
    STRONG_ENOUGH_RADIUS = 14    ## RADIUS WHEN DETERMINING STRONG ENOUGH ATTACK POWER

    ## ADDED TO WITHIN CIRCLE
    ## TO INCLUDE 7.2 WITHIN 7 RADIUS
    CIRCLE_RADIUS_EXTRA_EDGES = 0.8 ## 0.47 or 0.80 MULTIPLIED TO RADIUS. 1.2 Better??

class Target():
    """
    SHOULD WE DELETE? NOT REALLY BEING UTILIZED
    """
    NOTHING = -1
    PLANET = 0
    SHIP = 1

class ShipTasks(Enum):
    """
    VALUES FOR SHIPS TASKS

    NOT REALLY USED YET
    """
    NONE = -1   ## DEFAULT
    MINING = 0
    EXPANDING = 1
    DEFENDING = 2
    ATTACKING_FRONTLINE = 3
    ATTACKING = 4
    SUPPORTING = 5
    EVADING = 6
    RUNNING = 7
    SNIPING = 8


def disable_log(disable,log):
    """
    DISABLE LOGGING FOR THE GIVEN LOG

    LOGGER OBJECT HAS NO DISABLE? THUS ALWAYS PASSING logging
    """
    if disable:
        log.disable(logging.DEBUG)

def get_logger(name):
    """
    CREATE A LOGGER PER PROCESSOR/THREAD
    """
    ## INITIALIZE LOGGING
    fh = logging.FileHandler(name + '.log')
    fmt = logging.Formatter("%(asctime)-6s: %(name)s - %(levelname)s - %(message)s)")
    fh.setFormatter(fmt)
    local_logger = logging.getLogger(name)
    local_logger.setLevel(logging.DEBUG)
    local_logger.addHandler(fh)
    local_logger.debug(name + ' (worker) Process started')

    return local_logger

class Coordinates():
    """
    CLASS FOR COORDS
    """
    def __init__(self,y,x):
        self.y = y
        self.x = x

    ## OVERRIDE PRINTING FUNCTION
    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "y: {} x: {}".format(self.y,self.x)


def fill_circle(array, center, radius, value, cummulative=False, override_edges=None):
    """
    MASK A CIRCLE ON THE ARRAY SPECIFIED WITH VALUE PROVIDED

    hieght AND width BASED ON ARRAY SIZE
    """
    height = array.shape[0]
    width = array.shape[1]

    ## y IS JUST AN ARRAY OF 1xY (ROWS)
    ## x IS JUST AN ARRAY OF 1xX (COLS)
    y, x = np.ogrid[-center.y:height - center.y, -center.x:width - center.x]
    ## MASKS IS A HEIGHTxWIDTH ARRAY WITH TRUE INSIDE THE CIRCLE SPECIFIED
    #mask = x * x + y * y <= radius * radius

    if override_edges:
        mask = x * x + y * y <= radius * radius + radius * override_edges  ## USED FOR FILLING PLANETS IN EXPLORE
    else:
        mask = x * x + y * y <= radius * radius + radius*Constants.CIRCLE_RADIUS_EXTRA_EDGES  ## WHEN WANT TO BE MORE CIRCLE (DUE TO ROUNDING)

    if cummulative:  ## VALUE KEEPS GETTING ADDED
        array[mask] += value
    else:
        array[mask] = value

    return array



def get_angle(coords, target_coords):
    """
    RETURNS ANGLE BETWEEN COORDS AND TARGET COORDS
    BOTH ARE IN (y,x) FORMAT
    """
    angle = math.degrees(math.atan2(target_coords.y - coords.y, target_coords.x - coords.x)) % 360
    return int(round(angle))


def get_destination_coord(start_coord, angle, thrust, rounding=False):
    """
    GIVEN ANGLE AND THRUST, GET DESTINATION COORDS

    start_coord HAVE (y,x) FORMAT
    """
    if angle == 0:
        new_y, new_x = start_coord.y, start_coord.x + thrust

    elif angle < 90:
        angle_radian = math.radians(angle)
        rise = thrust * math.sin(angle_radian)
        run = thrust * math.cos(angle_radian)
        new_y, new_x = start_coord.y + rise, start_coord.x + run

    elif angle == 90:
        #return Coordinates(start_coord.y - thrust, start_coord.x)
        new_y, new_x = start_coord.y + thrust, start_coord.x

    elif angle < 180:
        angle = 180 - angle
        angle_radian = math.radians(angle)

        rise = thrust * math.sin(angle_radian)
        run = thrust * math.cos(angle_radian)
        new_y, new_x = start_coord.y + rise, start_coord.x - run

    elif angle == 180:
        new_y, new_x = start_coord.y, start_coord.x - thrust

    elif angle < 270:
        angle = angle - 180
        angle_radian = math.radians(angle)

        rise = thrust * math.sin(angle_radian)
        run = thrust * math.cos(angle_radian)
        new_y, new_x = start_coord.y - rise, start_coord.x - run

    elif angle == 270:
        #return Coordinates(start_coord.y + thrust, start_coord.x)
        new_y, new_x = start_coord.y - thrust, start_coord.x

    else:
        angle = 360 - angle
        angle_radian = math.radians(angle)

        rise = thrust * math.sin(angle_radian)
        run = thrust * math.cos(angle_radian)
        new_y, new_x = start_coord.y - rise, start_coord.x + run

    if rounding:
        return Coordinates(int(round(new_y)), int(round(new_x)))
    else:
        return Coordinates(new_y, new_x)

def get_variance(arr):
    """
    RETURN VARIANCE OF THE LIST OF POINTS PROVIDED
    """
    data = np.array(arr)
    return np.var(data)


def calculate_centroid(arr_points):
    """
    CALCULATE CENTROID.  COORDS ARE IN (y,x) FORMAT
    CALCULATE MIDDLE POINT OF A TRIANGLE (3 SHIPS)
    BASED ON:
    x = x1+x2+x3 / 3
    y = y1+y2+y3 / 3

    UPDATED TO CALCULATE CENTROID OF MULTIPLE POINTS, NOT JUST 3 POINTS
    """

    ## CONVERT ARR (LIST) TO NDARRAY
    data = np.array(arr_points)
    length = data.shape[0]
    sum_y = np.sum(data[:, 0])
    sum_x = np.sum(data[:, 1])

    return Coordinates(sum_y / length, sum_x / length)


def within_circle(point_coord, center_coord, radius):
    """
    RETURNS TRUE OR FALSE
    WHETHER point IS INSIDE THE CIRCLE, AT center WITH radius provided
    point AND center HAVE (y,x) FORMAT
    """
    ## ADDING 3.3 BECAUSE SOMETIMES WHEN IT ROUNDS IT DOESNT INCLUDE IT ANYMORE WITHIN THE CIRCLE
    ## SO DISTANCE 7.23 WILL STILL BE CONSIDERED WITHIN THE CIRCLE
    #return ((point_coord.y - center_coord.y) ** 2 + (point_coord.x - center_coord.x) ** 2) < (radius ** 2)
    return ((point_coord.y - center_coord.y) ** 2 + (point_coord.x - center_coord.x) ** 2) < (radius ** 2) + radius*Constants.CIRCLE_RADIUS_EXTRA_EDGES


def calculate_distance(coords1, coords2, rounding=True):
    """
    CALCULATE DISTANCE BETWEEN 2 POINTS
    """
    # y1 = int(round(coords1.y))
    # y2 = int(round(coords2.y))
    # x1 = int(round(coords1.x))
    # x2 = int(round(coords2.x))
    y1 = coords1.y
    y2 = coords2.y
    x1 = coords1.x
    x2 = coords2.x
    if rounding:
        return int(round(math.sqrt((y1 - y2) ** 2 + (x1 - x2) ** 2)))
    else:
        return math.sqrt((y1 - y2) ** 2 + (x1 - x2) ** 2)


def get_slope(prev_coord, current_coord):
    class Slope:
        def __init__(self,rise,run):
            self.rise = rise
            self.run = run

    slope = Slope(current_coord.y - prev_coord.y, current_coord.x - prev_coord.x)

    return slope

def get_reversed_angle(angle):
    """
    GIVEN AN ANGLE, RETURN ITS REVERSE/FLIP ANGLE
    """
    return (180+angle)%360

def get_angle_thrust(start_coord, target_coord):
    """
    RETURN ANGLE AND THRUST
    BASED ON START AND TARGET COORDS GIVEN
    """
    angle = get_angle(start_coord, target_coord)
    thrust = calculate_distance(start_coord, target_coord)

    return angle, thrust


def convert_for_command_queue(*args):
    if len(args) == 2:
        if args[1] is None:
            default_planet_id = 0
            return "d {} {}".format(args[0], default_planet_id)
        else:
            return "d {} {}".format(args[0], args[1])
    elif len(args) == 3:
        ## SHIP ID, THRUST (INT), ANGLE (INT)
        return "t {} {} {}".format(args[0], args[1], args[2]%360) ## KEEP ANGLE 0-359 RANGE
    else:
        logging.ERROR("Command Error Length")


def get_coord_of_value_in_angle(matrix, starting_coord, looking_for_val, angle):
    """
    GIVEN THE ANGLE, FIND THE CLOSEST VALUE
    FOLLOWING THE PATH OF THE UNIT VECTOR

    RETURN COORD OF THE CLOSEST VALUE (looking_for)

    RETURN NONE IF NOTHING IS FOUND

    90 DEGREES GOING DOWN, 270 DEGREES GOING UP
    """
    unit_vector = -np.cos(np.radians(-angle - 90)), -np.sin(np.radians(-angle - 90))
    multiplier = 1
    start_point = [starting_coord.y, starting_coord.x]

    try:
        while True:
            new_coord = [start_point[0] + multiplier * unit_vector[0],
                         start_point[1] + multiplier * unit_vector[1]]
            round_new_coord = (int(round(new_coord[0])), int(round(new_coord[1])))

            ## GET VALUE
            val = matrix[round_new_coord[0]][round_new_coord[1]]

            ## INCREASE MULTIPLIER
            multiplier += 1

            if val == looking_for_val:
                found_coord = Coordinates(round_new_coord[0], round_new_coord[1])
                return found_coord

    except Exception as e:
        logging.warning("{}".format(e))
        logging.warning("get_coord_closest_value DID NOT FIND ANY!")
        ## OUT OF BOUNDS
        ## DID NOT FIND WHAT WE WERE LOOKING FOR
        return None


def add_padding(a, center_coord, square_radius, pad_values):
    """
    RETURNS A MATRIX PADDED, WHEN ITS OUTSIDE THE BOUNDARIES OF THE ORIGINAL MATRIX
    """
    tp = max(0, -(center_coord.y - square_radius))
    bp = max(0, -((a.shape[0]-center_coord.y-1) - square_radius))
    lp = max(0, -(center_coord.x - square_radius))
    rp = max(0, -((a.shape[1]-center_coord.x-1) - square_radius))

    ## ADDS THE PADDING TO 'a'
    a = np.pad(a, [[tp, bp], [lp, rp]], 'constant', constant_values=(pad_values))

    ## RETURN THE SECTION THATS WITHIN THE BOUDARIES
    ## BUT THIS WILL BE AUTOMATICALLY PADDED BECAUSE OF np.pad?
    return a[center_coord.y - square_radius + tp:center_coord.y + square_radius + 1 + tp, \
           center_coord.x - square_radius + lp:center_coord.x + square_radius + 1 + lp]



def get_circle_in_square(array, center_coord, circle_radius, square_radius, pad_values, pad_outside_circle=False):
    """
    RETURNS A SQUARE MATRIX
    GET VALUES FROM THE MATRIX PROVIDED, WITHIN THE CIRCLE SPECIFIED
    """

    center_y = int(round(center_coord.y))
    center_x = int(round(center_coord.x))

    height = array.shape[0]
    width = array.shape[1]

    ## VALUES OUTSIDE THE CIRCLE WILL BE ZEROES
    temp_matrix = np.zeros((height, width), dtype=np.float16)

    if pad_outside_circle: ## NORMALLY OUTSIDE CIRCLE IS 0, THIS IS TO OVERRIDE THAT
        temp_matrix.fill(pad_values)

    ## y IS JUST AN ARRAY OF 1xY (ROWS)
    ## x IS JUST AN ARRAY OF 1xX (COLS)
    y, x = np.ogrid[-center_y:height - center_y, -center_x:width - center_x]
    ## MASKS IS A HEIGHTxWIDTH ARRAY WITH TRUE INSIDE THE CIRCLE SPECIFIED
    mask = x * x + y * y <= circle_radius * circle_radius

    ## PLACE VALUES FROM THE CIRCLE ON THE TEMP MATRIX
    temp_matrix[mask] = array[mask]

    ## ADD PADDING, IF OUTSIDE THE MATRIX BOUNDARIES
    section = add_padding(temp_matrix, Coordinates(center_y, center_x), square_radius, pad_values)

    return section


def get_section_with_padding(a, center_coord, square_radius, pad_values):
    """
    GET A SECTION FROM AN ARRAY, CONSIDER ADDING PADDING IF OVER THE BOUNDARY
    """
    ## MAKE SURE ITS ROUNDED
    point = get_rounded_point(center_coord)
    center_coord = Coordinates(point[0], point[1])

    return add_padding(a, center_coord, square_radius, 0)


def get_coord_closest_seek_value(seek_val, values, distances):
    """
    GET CLOSESTS AND MOST ENEMIES FROM THE SECTION PROVIDED

    RETURNS COORD BASED ON VALUES/DISTANCES PASSED, MIN DISTANCE, VALUE WITH MINIMUM DISTANCE
    """
    # Get row, col indices for the condition
    if seek_val == 1:
        r, c = np.where(values >= seek_val)
    else: ## FOR -1s
        r, c = np.where(values <= seek_val)

    # Extract corresponding values off d
    di = distances[r, c]

    if len(di) >= 1:
        min_di = di.min()

        # Get indices (indexable into r,c) corresponding to lowest distance
        ld_indx = np.flatnonzero(di == min_di)

        ## GETTING CLOSEST MOST ENEMY
        ## Get max index (based off v) out of the selected indices
        # max_idx = values[r[ld_indx], c[ld_indx]].argmax()
        #
        # ## Index into r,c with the lowest dist indices and
        # ## from those select maxed one based off v
        # return (r[ld_indx][max_idx], c[ld_indx][max_idx]), min_di, values[r[ld_indx][max_idx], c[ld_indx][max_idx]]

        ## GETTING THE CLOSEST LEAST ENEMY
        ## Get max index (based off v) out of the selected indices
        min_idx = values[r[ld_indx], c[ld_indx]].argmin()

        ## Index into r,c with the lowest dist indices and
        ## from those select maxed one based off v
        return (r[ld_indx][min_idx], c[ld_indx][min_idx]), min_di, values[r[ld_indx][min_idx], c[ld_indx][min_idx]]

    else:
        ## NO ENEMIES FOUND
        return None, None, None


def get_ship_ids_in_array(values, distances):
    """
    GET COORDS OF ALL VALUES FOUND, ORDER BY DISTANCE
    """
    seek_val = 0
    return values[np.where(values >= seek_val)][np.argsort(distances[np.where(values >= seek_val)])]


def get_section_num(coord):
    """
    TAKES A COORD AND RETURN THE SECTION VALUE
    """
    return (int(coord.y // Constants.NUM_SECTIONS), int(coord.x // Constants.NUM_SECTIONS))

def get_coord_from_section(section):
    """
    GET COORD FROM SECTION PROVIDED
    """
    ## SUBTRACT HALF OF NUM SECTIONS TO GET THE MIDDLE FO THAT SECTION
    return Coordinates((section[0]+1) * Constants.NUM_SECTIONS - (Constants.NUM_SECTIONS/2),
                       (section[1]+1) * Constants.NUM_SECTIONS - (Constants.NUM_SECTIONS/2) )


def get_rounded_point(coord):
    """
    GET ROUNDED COORD
    """
    return (int(round(coord.y)), int(round(coord.x)))

def isInside_map(coord, MyMoves):
    """
    CHECK IF COORD IS OUTSIDE THE MAP
    """
    return 0 <= coord.y <= MyMoves.EXP.height and 0 <= coord.x <= MyMoves.EXP.width

# array = [
#     [1, 2, 3, 4, 5, 6, 7, 8, 9],
#     [2, 3, 4, 5, 6, 7, 8, 9, 1],
#     [3, 4, 5, 0, 7, 8, 9, 1, 2],
#     [4, 5, 6, 7, 8, 9, 1, 2, 3],
#     [5, 0, 7, 8, 9, 4, 5, 6, 7],
#     [6, 7, 8, 9, 1, 2, 3, 4, 5]
# ]
# a = np.asarray(array)
# circle_radius = 2
# square_radius = 2
#
# #array = np.random.randint(5, size=(40,40))
# print(get_circle_in_matrix(a, Coordinates(4,1), circle_radius, square_radius))


# coord = Coordinates(0,0)
# angle = 45
# thrust = 7.22
# coord2 = get_destination_coord(coord,angle,thrust,rounding=False)
# # print(coord2)
# # coord2 = get_destination_coord(coord,angle,thrust,rounding=True)
# print("Rounded: ",coord2)
# print("Distance:",calculate_distance(coord, coord2))
# print("in circle: ",within_circle(coord2,coord,7))
#
#
# print(calculate_distance(coord,coord2,rounding=False))



# def get_distances(start, height, width):
#     matrix = np.zeros((height, width), dtype=np.float16)
#     indexes = [(y, x) for y, row in enumerate(matrix) for x, val in enumerate(row)]
#     to_points = np.array(indexes)
#     start_point = np.array(start)
#     distances = np.linalg.norm(to_points - start_point, ord=2, axis=1.)
#
#     return distances.reshape((height, width))
#
#
# height = 16
# width = 16
# start = [8, 8]
# distance_matrix = get_distances(start, height, width)
# print(distance_matrix)



# array = np.zeros((31,31), dtype=np.float16)
# center = Coordinates(15,15)
# radius = 10
# value = 1
# np.set_printoptions(threshold=np.inf,linewidth=np.inf)  ## SET PRINT THRESHOLD TO INFINITY
# print(fill_circle(array, center, radius, value, cummulative=False, override_edges=0))
# np.set_printoptions(threshold=10)     ## SET PRINT THRESHOLD TO 10
#
#
# print("-------")
#
# array = np.zeros((31,31), dtype=np.float16)
# center = Coordinates(15,15)
# radius = 10
# value = 1
# np.set_printoptions(threshold=np.inf,linewidth=np.inf)  ## SET PRINT THRESHOLD TO INFINITY
# print(fill_circle(array, center, radius, value, cummulative=False, override_edges=2))
# np.set_printoptions(threshold=10)     ## SET PRINT THRESHOLD TO 10
#
# print("-------")
#
# array = np.zeros((31,31), dtype=np.float16)
# center = Coordinates(15,15)
# radius = 10
# value = 1
# np.set_printoptions(threshold=np.inf,linewidth=np.inf)  ## SET PRINT THRESHOLD TO INFINITY
# print(fill_circle(array, center, radius, value, cummulative=False, override_edges=2.1))
# np.set_printoptions(threshold=10)     ## SET PRINT THRESHOLD TO 10
#
# print("-------")
#
# array = np.zeros((20,20), dtype=np.float16)
# center = Coordinates(9,9)
# radius = 7
# value = 1
# np.set_printoptions(threshold=np.inf,linewidth=np.inf)  ## SET PRINT THRESHOLD TO INFINITY
# print(fill_circle(array, center, radius, value, cummulative=False, override_edges=0))
# np.set_printoptions(threshold=10)     ## SET PRINT THRESHOLD TO 10


