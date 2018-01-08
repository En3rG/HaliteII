"""
TRY IMPLEMENTING NUMPY HERE
THAT WILL GET THE DISTANCE OF EACH SHIPS TO EACH PLANETS
AND DISTANCE TO CLOSEST ENEMY AS WELL

USE THIS INSTEAD OF HEAP? MIGHT BE MORE ACCURATE
BUT NOT SURE IF IT"LL TAKE TOO MUCH TIME
"""
import numpy as np
import pandas as pd

## SAMPLE GET DISTANCES FROM A POINT TO LIST OF POINTS
to_points = np.array([(0,1),(1,0),(-1,0),(0,-1),(2,2)])
start = np.array([0,0])

distances = np.linalg.norm(to_points - start, ord=2, axis=1.)  # distances is a list



## SAMPLE GET TOP 3 VALUES FROM A NUMPY ARRAY
values = np.array([9,1,3,4,8,7,2,5,6,0])

N = 3 ## TOP 3

temp = np.argpartition(-values, N)
result_args = temp[:N]

temp = np.partition(-values, N)
result = -temp[:N]

#print("values",values)
#print("result_args",result_args)
#print("result",result)


## SAMPLE GET TOP 3 VALUES FROM A COLUMN IN A NUMPY ARRAY
values = np.array([
    [1,2,3,4],
    [5,6,7,8],
    [9,10,11,12],
    [13,14,15,16]
])

N = 2 ## TOP 3


temp = np.argpartition(-values[:,0], N)
result_args = temp[:N]

temp = np.partition(-values[:,0], N)
result = -temp[:N]

# print("values",values)
# print("result_args",result_args)
# print("result",result)


## SAMPLE GET TOP 3 VALUES FROM A COLUMN IN A PANDA
df = pd.DataFrame({1:[1,2,3,4],
                  2:[5,6,7,8],
                  3:[9,10,11,12],
                  4:[13,14,15,16]})

print(df.nlargest(2,columns=1))