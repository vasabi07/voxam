# CS - pymupdf

**Pages:** 16
**Characters:** 29,785
**Time:** 0.11s
**Cost:** $0.0000
**Tables detected:** No
**Equations detected:** No
**Code blocks detected:** Yes

---

## Preview (first 5000 chars)

[PAGE 1]
In this Chapter
»»
Introduction
»»
Linear Search
»»
Binary Search
»»
Search by Hashing
C
h
a
p
t
e
r
6.1 Introduction
We store many things in our home and find them 
out later as and when required. Sometimes we 
remember the exact location of a required item. 
But, sometimes we do not remember the exact 
location and in that case we need to search for 
the required item. A computer also stores lots of 
data to be retrieved later as and when demanded 
by a user or a program.
Searching 
means 
locating 
a 
particular 
element in a collection of elements. Search result 
determines whether that particular element is 
present in the collection or not. If it is present, 
we can also find out the position of that element 
in the given collection. Searching is an important 
technique in computer science. In order to design 
algorithms, programmers need to understand the 
different ways in which a collection of data can be 
searched for retrieval.
6 
Searching
“Even though most people won't be directly 
involved with programming, everyone is affected 
by computers, so an educated person should have 
a good understanding of how computer hardware, 
software, and networks operate.”
— Brian Kernighan
Reprint 2025-26


[PAGE 2]
Computer Science - Class XII
82
6.2 Linear Search
Linear search is the most fundamental and the simplest 
search method. It is an exhaustive searching technique 
where every element of a given list is compared with 
the item to be searched (usually referred to as ‘key’). 
So, each element in the list is compared one by one 
with the key. This process continues until an element 
matching the key is found and we declare that the 
search is successful. If no element matches the key and 
we have traversed the entire list, we declare the search 
is unsuccessful i.e., the key is not present in the list. 
This item by item comparison is done in the order, in 
which the elements are present in the list, beginning at 
the first element of the list and moving towards the last. 
Thus, it is also called sequential search or serial search. 
This technique is useful for collection of items that are 
small in size and are unordered.
Given a list numList of n elements and key value K, 
Algorithm 6.1 uses a linear search algorithm to find the 
position of the key K in numList.
Algorithm 6.1 : Linear Search
LinearSearch(numList, key, n)
Step 1: SET index = 0
Step 2: WHILE  index < n, REPEAT Step 3
Step 3: IF numlist[index]= key THEN
        PRINT “Element found at position”, index+1
        STOP
   ELSE
        index = index+1
Step 4: PRINT “Search unsuccessful”
Example 6.1	 Assume that the numList has seven elements 
[8, -4, 7, 17, 0, 2, 19] so, n = 7. We need to search for the key, 
say 17 in numList. Table 6.1 shows the elements in the given 
list along with their index values.
Table 6.1	 Elements in numList alongwith their index value
Index in numList
0
1
2
3
4
5
6
Value
8
-4
7
17
0
2
19
The step-by-step process of linear search using 
Algorithm 6.1. is given in Table 6.2.
Activity 6.1
Consider a list of 15 
elements: 
L=[2,3,9,7,-
6,11,12,17,45,23,29,
31,-37,41,43]. 
Determine the number 
of comparisons 
linear search 
makes to search 
for key = 12.
Reprint 2025-26


[PAGE 3]
Searching
83
Observe that after four comparisons, the algorithm 
found the key 17 and will display ‘Element found at 
position 4’.
Let us now assume another arrangement of the 
elements in numList as [17, 8, -4, 7, 0, 2, 19] and search 
for the key K=17 in numList.
Table 6.3	 Elements in numList alongwith their index value
Index in numList
0
1
2
3
4
5
6
Value
17
8
-4
7
0
2
19
Table 6.2	Linear search for key 17 in numList of Table 6.1
index
index < n
numList[index]= key
index=index+1
0
0 < 7 ? Yes
8 = 17? No
1
1
1 < 7 ? Yes
-4 = 17? No
2
2
2 < 7 ? Yes
7 = 17? No
3
3
3 < 7 ? Yes
17 = 17? Yes
Table 6.4	Linear search for key 17 in numList given in Table 6.3
index
index < n
numList[index]= 
key
index=index+1
0
0 < 7 ? Yes
17 = 17? Yes
1
From Table 6.4, it is clear that the algorithm had 
to make only 1 comparison to display ‘Element found 
at position 1’. Thus, if the key to be searched is the 
first element in the list, the linear search algorithm 
will always have to make only 1 comparison. This is 
the minimum amount of work that the linear search 
algorithm would have to do.
Let us now assume another arrangement of the 
elements in numList as [8, -4, 7, 0, 2, 19, 17] and search 
for the key K =17 in numList.
On a dry run, we can find out that the linear search 
algorithm has to compare each element in the list till 
the end to display ‘Element found at position 7’. Thus, 
if the key to be searched is the last element in the 
list, the linear search algorithm will have to make n 
comparisons, where n is the number of elements in the 
list. This is in fact the maximum amount of work the 
linear search algorithm would have to do.
Activity 6.2
In the list : L = [7,-1,
11,32,17,19,23,29,31,
37,43] 
Determine the number 
of comparisons 