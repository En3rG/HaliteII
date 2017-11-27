import logging
import datetime



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




