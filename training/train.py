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

def save_json(filename,data):
    """
    TAKES DATA IN JSON FORMAT
    AND WRITES INTO A FILE (FILENAME)
    """
    with open(filename, 'w') as outfile:
        json.dump(data, outfile, indent=4)



filename = "replay-20180106-001223-0500--2529531316-336-224-240573.hlt"
data = load_hlt(filename)

save_json("test.txt",data)


