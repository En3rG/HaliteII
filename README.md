# Halite II

Two Sigma's <a href="https://halite.io/">Halite II</a> competition ending on Jan 22, 2018. Finished as rank 84 out of 5832.

## Summary
I initially wanted to use Machine Learning on my bot.  Most people doing machine learning will train their model against the top players or use reinforcement learning, but I wanted to try something different.  I wanted to train against the top players and also train during every game.  Basically use transfer learning during the game and update the weights based on enemy's movements.  I initialize 2 processes per enemy player (one for predicting and one for training).  It was a very basic neural network which worked okay on my local machine.  But once I tried uploading it to the server, it started crapping out.  First it was due to tensorflow printing status on the terminal, that crashes the hlt engine.  Though this wasnt happening on my local machine, it was on the server.  I eventually found a solution in the forum that worked.  

I was skeptical since the beginning that this would work, due the amount of sample/training set available per game.  Basically each enemy ships, per turn, per player.  And you really cant wait until the end of the game to figure out their moves (in order to benefit from it), hence you really want a good model by turn 80 - 100.  Without even utilizing the predicted moves, and just trying to train and predict each turn, for each ships, per enemy, my bot was already timing out.  After turn 100+ with an enemy having 150+ ships, my bot will eventually time out.

Unfortunately, by the beginning of January I had to ditch trying to use machine learning and just hand written an algorithm for my bot.

## Bot Summary
Here's a quick summary of my bot from <a href="https://github.com/En3rG/HaliteII/tree/Submission">Submission branch</a>.  I basically didnt use or update the starter kit.  I should've done that or updated it like most people. 

* Initialization

Under explore.py, I basically gather all the planet information.  Calculate the distances of each planet to each other.  Figure out the best planet to conquer first.  I also divided the map into sections and determine distances from each sections to all other sections.  There may be other functions here that are no longer used, that I was experimenting on earlier.

Astar.py shouldnt really belong to initialization.  This contains the astar algorithm used to determine path for each ships.  It basically gathers a section (surrounding) of a ship and determines a path to get to the destination, using astar algorithm.  It utilizes a position matrix that states ships position per sub-turn.  Each turn contains 7 sub-turns since a ship can move with a maximum velocity of 7 units per turn.  I will then iterate through each of the box/coordinate found in the astar path and see if there is no collision to going there directly, since we only need one angle/one thrust.  This honestly seem inefficient, and could probably be improved using theta * algorithm or something completely different that others used.

* Models

Model.py is no longer used, this was used for experimenting using neural network mentioned earlier.

Under data.py, I basically generate my own data structure of each players ships.  I also generate multiple numpy arrays used for position matrix and finding enemy ships, used for attacking/defending.

* Multiprocessor

Again no longer used, was used for experimenting with machine learning.

* Testing

Used for debugging

* Train

Used to parse .hlt files from online and generate each players moves per turn.  Used to simulate enemy's bot and run locally to determine bugs on my bot.

* Movement

Moves2.py handles the main logic of my bot.  First it checks if we should retreat.  Basically when our ships is below a certain percentage of the total number of enemy ships, we run to the corner.  If this is true, all ships will be assigned a task 'retreating'

I didnt get to implement rushing so this was just commented out.

If the ships arent retreating, I then move/assign tasks to ships that are currently mining, so that these ships will no longer be considered in attacking/defending logic.

The defending algorithm will then be executed.  It basically goes through each mining ships and check if any enemy is within a certain radius.  If it is, then ships that are within a certain radius will be tasked to defend the mining ship.  To minimize collision, ships closest to the mining ship will be moved first.  The further ones will then be moved towards the mining ship.

I didnt get to implement sniping.  Basically I wanted to implement an algorithm to kill/assassinate a specific docked ship.  Thus this is just commented out.

I also didnt get to implement harrassing.  This would have been under running, again this is just commented out.

Attacking2.py basically handles ships that have an enemy within a certain radius.  If a ship is within imminent battle, meaning an enemy is within 14 distance away, if calculates if its section is strong enough to attack the enemy section.  If its not strong enough, it will move backwards, away from the enemy and ask availabe ships around the area to support this ship.  Basically ask for backup.  If its strong enough it goes towards the enemy.  Ships that are not in imminent battle, but detect enemy within the specified radius, will be assigned to move towards the closest enemy.

Rest of the ships will be assigned to expand (get closest available planets).  If there are no longer planets availabe to conquer, it finds the closest docked enemy ships and is assigned to go towards that location.

## Improvements to be made

* Pathfinding. Though I didnt really have any timeout issues, the pathfinding algorithm needs improvement.  Also, collisions still occur here and there. 

* Grouping.  I need to be able to move my ships closer together.  With my current implementation, I generate a 2D numpy array based on the size of the map. This is not really good enough, since ships' coordinate can have up to 4 decimal places.  Thus, with my current implementation there is a lot of rounding that occurs which prevents a better/exact representation of the ships' location.

* Harrassing.  Implementing even a simple harrass algorithm would help a lot.  It distracts/slows down enemy from expanding.

 ## Conclusion
Again, thanks for Two Sigma for hosting another competition.  Halite II was as fun as the first one.  Can't wait for the next version.

