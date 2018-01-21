import zstd
import json

"""
TRAIN AGAINST TOP PLAYERS
THEN DO TRANSFER LEARNING

REFERENCE:
https://towardsdatascience.com/transfer-learning-using-keras-d804b2e04ef8
"""

"""
HLT CONSISTS OF:

width
version
moves           - per player - per ships
map_generator
num_players
planets
poi
num_frames
constants
engine_version
frames
height
seed
player_names
stats           - per player - rank


BREAKDOWN OF FRAMES:
ITS A LIST, PER FRAME
IN EACH FRAME HAS KEYS:

planets: {id:id, current_production, owner, health, remaining_production, docked_ships}
ships:{player_id:{ship_id:{owner,id,docking,y,x,vel_x,cooldown,health,vel_y}}}
events:[]


"""

"""
USE HALITE CLIENT TO DOWNLOAD GAMES

## 1092 IS daewook's ID
## 1490 IS zxqfl
client.py replay user -i 1092 -l 100 -d replays

"""
def load_hlt(filename):
    """
    TAKES HLT FILE AND RETURNS IN JSON FORMAT
    """
    ## DECOMPRESS HLT FILE (COMPRESSED JSON)
    data = zstd.decompress(open(filename, "rb").read())
    ## LOAD JSON
    data_json = json.loads(data.decode())

    return data_json

def save_json(filename, data):
    """
    TAKES DATA IN JSON FORMAT
    AND WRITES INTO A FILE (FILENAME)
    """
    with open(filename, 'w') as outfile:
        json.dump(data, outfile, indent=4)

def generate_run_game_bat(data):
    """
    GENERATE run_game.bat

    .\halite -d "264 176" -s "2781037135" "python MyBot.py" "python simulate_p1.py"
    """
    width = data['width']
    height = data['height']
    seed = data['seed']
    num_players = data['num_players']

    if num_players == 2:
        command = ".\halite -d \"{} {}\" -s \"{}\" \"python simulate_p0.py\" \"python simulate_p1.py\"".format(width, height, seed)
    elif num_players == 4:
        command = ".\halite -d \"{} {}\" -s \"{}\" \"python simulate_p0.py\" \"python simulate_p1.py\" \"python simulate_p2.py\" \"python simulate_p3.py\"".format(width,height, seed)

    with open('run_game.bat', 'w') as outfile:
        outfile.write(command)

def get_moves_per_player(data):
    """
    PARSE JSON TO GET EACH PLAYERS MOVES PER TURN
    """
    def get_moves_this_turn(player_data, command_moves_pX):
        """
        PARSES MOVES THIS TURN, ADD TO COMMAND_MOVES_PX
        """
        print(player_data)
        current_turn_commands = []
        for ship_id, ship_data in player_data[0].items(): ## [0] BECAUSE ITS A LIST WITH ONE DICTIONARY INSIDE

            if ship_data.get('type') == 'thrust':
                ## IF IT HAS ANGLE, ITS MOVING
                thrust = ship_data.get('magnitude')
                angle = ship_data.get('angle')
                current_turn_commands.append("t {} {} {}".format(ship_id, thrust, angle))
            else:
                ## DOCKING
                planet_id = ship_data.get('planet_id')
                current_turn_commands.append("d {} {}".format(ship_id, planet_id))

        command_moves_pX.append(current_turn_commands)

    def save_moves_json(filename, commands):
        """
        SAVES MOVES TO JSON FILE
        """
        #json_commands = {'moves':commands}
        save_json(filename, commands)

    command_moves_p0 = []
    command_moves_p1 = []
    command_moves_p2 = []
    command_moves_p3 = []

    for i, moves_per_turn in enumerate(data['moves']):
        """
        MOVING:  '2': {'owner': 0, 'angle': 273, 'type': 'thrust', 'magnitude': 3, 'shipId': 2, 'queue_number': 0}
        DOCKING: '1': {'type': 'dock', 'shipId': 1, 'planet_id': 8, 'owner': 0, 'queue_number': 0
        """
        print("At turn {}".format(i))
        get_moves_this_turn(moves_per_turn.get('0'), command_moves_p0)
        get_moves_this_turn(moves_per_turn.get('1'), command_moves_p1)
        get_moves_this_turn(moves_per_turn.get('2'), command_moves_p2)
        get_moves_this_turn(moves_per_turn.get('3'), command_moves_p3)

    save_moves_json("p0.txt", command_moves_p0)
    save_moves_json("p1.txt", command_moves_p1)
    save_moves_json("p2.txt", command_moves_p2)
    save_moves_json("p3.txt", command_moves_p3)

filename = "8638555.hlt"
data = load_hlt(filename)
get_moves_per_player(data)
generate_run_game_bat(data)
save_json("test.txt",data)


