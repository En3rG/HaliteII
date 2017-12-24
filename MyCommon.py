import logging
import datetime
import numpy as np
import math


class Constants():
    ATTACK_RADIUS = 5
    DOCK_RADIUS = 4

def disable_log(disable,log):
    """
    DISABLE LOGGING FOR THE GIVEN LOG

    LOGGER OBJECT HAS NO DISABLE? THUS ALWAYS PASSING logging
    """
    if disable:
        log.disable(logging.INFO)

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



def fill_circle(array, height, width , center, radius, value, cummulative=False):
    """
    MASK A CIRCLE ON THE ARRAY SPECIFIED WITH VALUE PROVIDED

    hieght AND width BASED ON ARRAY SIZE
    """

    ## y IS JUST AN ARRAY OF 1xY (ROWS)
    ## x IS JUST AN ARRAY OF 1xX (COLS)
    y, x = np.ogrid[-center.y:height - center.y, -center.x:width - center.x]
    ## MASKS IS A HEIGHTxWIDTH ARRAY WITH TRUE INSIDE THE CIRCLE SPECIFIED
    mask = x * x + y * y <= radius * radius

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


def get_destination_coord(start_coord, angle, thrust):
    """
    GIVEN ANGLE AND THRUST, GET DESTINATION COORDS

    start_coord HAVE (y,x) FORMAT
    """
    if angle == 0:
        return Coordinates(start_coord.y, start_coord.x + thrust)

    elif angle < 90:
        angle_radian = math.radians(angle)
        rise = thrust * math.sin(angle_radian)
        run = thrust * math.cos(angle_radian)
        return Coordinates(start_coord.y + rise, start_coord.x + run)

    elif angle == 90:
        #return Coordinates(start_coord.y - thrust, start_coord.x)
        return Coordinates(start_coord.y + thrust, start_coord.x)

    elif angle < 180:
        angle = 180 - angle
        angle_radian = math.radians(angle)

        rise = thrust * math.sin(angle_radian)
        run = thrust * math.cos(angle_radian)
        return Coordinates(start_coord.y + rise, start_coord.x - run)

    elif angle == 180:
        return Coordinates(start_coord.y, start_coord.x - thrust)

    elif angle < 270:
        angle = angle - 180
        angle_radian = math.radians(angle)

        rise = thrust * math.sin(angle_radian)
        run = thrust * math.cos(angle_radian)
        return Coordinates(start_coord.y - rise, start_coord.x - run)

    elif angle == 270:
        #return Coordinates(start_coord.y + thrust, start_coord.x)
        return Coordinates(start_coord.y - thrust, start_coord.x)

    else:
        angle = 360 - angle
        angle_radian = math.radians(angle)

        rise = thrust * math.sin(angle_radian)
        run = thrust * math.cos(angle_radian)
        return Coordinates(start_coord.y - rise, start_coord.x + run)


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


def within_circle(point,center,radius):
    """
    RETURNS TRUE OR FALSE
    WHETHER point IS INSIDE THE CIRCLE, AT center WITH radius provided
    point AND center HAVE (y,x) FORMAT
    """
    return ((point.y - center.y) ** 2 + (point.x - center.x) ** 2) < (radius ** 2)


def calculate_distance(coords1, coords2):
    """
    CALCULATE DISTANCE BETWEEN 2 POINTS
    """
    y1 = int(round(coords1.y))
    y2 = int(round(coords2.y))
    x1 = int(round(coords1.x))
    x2 = int(round(coords2.x))
    return int(math.sqrt((y1 - y2) ** 2 + (x1 - x2) ** 2))

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


def get_coord_closest_value(matrix, starting_coord, looking_for_val, angle):
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


