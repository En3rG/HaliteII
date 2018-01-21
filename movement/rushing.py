
import MyCommon

def move_all_ships(MyMoves):

    # EVERY OTHER TURN (EXCEPT FIRST TURN)
    if MyMoves.turn < MyCommon.Constants.ANTI_RUSH_TURNS:
        MyCommon.Constants.PERIMETER_CHECK_RADIUS = 56
    else:
        MyCommon.Constants.PERIMETER_CHECK_RADIUS = 28