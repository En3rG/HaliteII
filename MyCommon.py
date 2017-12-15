import logging
import datetime
import numpy as np
import math

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
    MASK A CIRCLE ON THE ARRAY WITH VALUE PROVIDED

    hieght AND width BASE ON ARRAY SIZE
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
    return round(angle)


def get_destination(start_coord, angle, thrust):
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
        return Coordinates(start_coord.y - thrust, start_coord.x)

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
        return Coordinates(start_coord.y + thrust, start_coord.x)

    else:
        angle = 360 - angle
        angle_radian = math.radians(angle)

        rise = thrust * math.sin(angle_radian)
        run = thrust * math.cos(angle_radian)
        return Coordinates(start_coord.y - rise, start_coord.x + run)