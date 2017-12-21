import MyCommon
import logging

class Groups():
    """
    WILL CONTAIN ALL THE GROUPS
    """
    COUNTER = -2 ## COUNTER FOR GROUP NUMBER. FIRST ONE WILL BE -1 (FIRST 3 SHIPS)

    def __init__(self, myMap):
        self.myMap = myMap
        self.groups_list = [] ## CONTAIN GROUP NUMBERS
        self.groups_dict = {} ## CONTAIN KEY AS GROUP NUMBER AND VALUE AS GROUP OBJECT

    def add_group(self, new_member_ids, keep_location):
        """
        ADD A NEW GROUP

        new_member_ids IS A SET
        """

        ## INCREMENT COUNTER
        Groups.COUNTER += 1

        ## CREATE GROUP INSTANCE
        new_group = Group(self.myMap)
        new_group.add_members(new_member_ids, keep_location)

        ## ADD TO GROUPS LIST
        self.groups_list.append(Groups.COUNTER)

        ## ADD TO GROUP DICT
        self.groups_dict[Groups.COUNTER] = new_group

    def keep_members(self, group_id, alive_ship_ids):
        """
        KEEP MEMBER OF A GROUP SPECIFIED
        """
        ## CREATE GROUP INSTANCE
        new_group = Group(self.myMap)
        new_group.add_members(alive_ship_ids, keep_location=True)

        ## UDPATE CENTROID
        new_group.update_centroid()

        ## ADD TO GROUPS LIST
        self.groups_list.append(group_id)

        ## ADD TO GROUP DICT
        self.groups_dict[group_id] = new_group


    def get_and_update_prev_group(self):
        """
        UPDATE PREVIOUS GROUP
        REMOVE SHIPS THAT DIED OR SEPARATED
        """
        for group_id, group in self.myMap.myMap_prev.groups.groups_dict.items():
            old = group.members_id
            current_ships = self.myMap.ships_owned

            alive_ship_ids = old & current_ships
            self.keep_members(group_id, alive_ship_ids)



    def get_move_group(self,group_id, thrust, angle):
        """
        MOVE SPECIFIED GROUP
        """
        command_queue_list = []
        for ship_id in self.groups_dict[group_id].members_id:
            if thrust == 0:
                ## START MINING
                target_planet_id = self.myMap.data_ships[self.myMap.my_id][ship_id].get('target_id', None)
                command_queue_list.append(MyCommon.convert_for_command_queue(ship_id, target_planet_id))
            else:
                command_queue_list.append(MyCommon.convert_for_command_queue(ship_id, thrust, angle))

            ## ADD TO SHIPS MOVED
            self.myMap.ships_moved_already.add(ship_id)
        return command_queue_list


    def add_value_to_group_members(self,group_id, key, value):
        """
        ADD VALUE TO PROVIDED KEY TO EACH OF THE SHIPS IN GROUP ID SPECIFIED
        """
        for ship_id in self.groups_dict[group_id].members_id:
            self.myMap.data_ships[self.myMap.my_id][ship_id][key] = value

    def add_value_to_group(self, group_id, key, value):
        """
        ADD VALUE TO GROUP
        """
        setattr(self.groups_dict[group_id],key,value)



class Group():
    """

    """
    def __init__(self, myMap):
        self.myMap = myMap
        self.centroid_coord = None    ## COORD OBJECT
        self.members_id = set()       ## SHIP IDS
        self.member_points = set()       ## WILL CONTAIN POINTS OF EACH MEMBER
        self.canMove = True           ## WHETHER OR NOT THIS GROUP IS MOVING
        self.Astar_path_key = None
        self.target_id = None

    def add_members(self, new_member_ids, keep_location):
        """
        ADD A NEW SHIP TO THE GROUP

        new_member_ids IS A SET OF SHIP IDs

        NEW MEMBERS GO TOWARDS THE CENTROID, THUS OLD MEMBERS DO NOT MOVE THIS TURN
        """

        ## DETERMINE LOCATION FOR THE NEW MEMBERS
        if keep_location == False:
            self.canMove = False  ## GETTING NEW LOCATIONS, THUS NEW MEMBERS ARE MOVING TOWARDS CENTROID. OLD DO NOT MOVE
            self.get_location(new_member_ids)
        else:
            self.canMove = True

        ## ADD NEW MEMBERS TO members_id
        self.members_id.update(new_member_ids)

        ## UPDATE member_points
        self.add_member_points(new_member_ids)



    def get_location(self, new_member_ids):
        """
        DETERMINE NEW LOCATIONS FOR EACH OF THE NEW MEMBERS
        """
        raise NotImplemented

        ## NEED TO UPDATE CENTROID
        #self.update_centroid()  ## SHOULD BE CALLED LATER.  AFTER MOVING. NO NEED TO UPDATE EVERY ADD??

    def add_member_points(self,new_member_ids):
        """
        ADD MEMBER POINTS DUE TO NEW ADDED MEMBERS
        """
        for ship_id in new_member_ids:
            y = self.myMap.data_ships[self.myMap.my_id][ship_id]['y']
            x = self.myMap.data_ships[self.myMap.my_id][ship_id]['x']
            self.member_points.add((y,x))

    def update_centroid(self):
        """
        UPDATE CENTROID OF THE GROUP
        """
        self.centroid_coord = MyCommon.calculate_centroid(list(self.member_points))



