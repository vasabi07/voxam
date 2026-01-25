# CS - olmOCR-2 (7B)

**Pages tested:** 3
**Characters:** 5,504
**Tokens:** 10,668
**Latency:** 14,697ms
**Cost:** $0.0010
**Tables detected:** No
**Equations detected:** No
**Code blocks detected:** No

---

## Extraction Preview

## Page 1

Chapter 6 Searching

In this Chapter
» Introduction
» Linear Search
» Binary Search
» Search by Hashing

"Even though most people won't be directly involved with programming, everyone is affected by computers, so an educated person should have a good understanding of how computer hardware, software, and networks operate."
— Brian Kernighan

6.1 INTRODUCTION
We store many things in our home and find them out later as and when required. Sometimes we remember the exact location of a required item. But, sometimes we do not remember the exact location and in that case we need to search for the required item. A computer also stores lots of data to be retrieved later as and when demanded by a user or a program.

Searching means locating a particular element in a collection of elements. Search result determines whether that particular element is present in the collection or not. If it is present, we can also find out the position of that element in the given collection. Searching is an important technique in computer science. In order to design algorithms, programmers need to understand the different ways in which a collection of data can be searched for retrieval.

---

## Page 3

Table 6.2 Linear search for key 17 in numList of Table 6.1

<table>
  <tr>
    <th>index</th>
    <th>index < n</th>
    <th>numList[index]= key</th>
    <th>index=index+1</th>
  </tr>
  <tr>
    <td>0</td>
    <td>0 < 7 ? Yes</td>
    <td>8 = 17? No</td>
    <td>1</td>
  </tr>
  <tr>
    <td>1</td>
    <td>1 < 7 ? Yes</td>
    <td>-4 = 17? No</td>
    <td>2</td>
  </tr>
  <tr>
    <td>2</td>
    <td>2 < 7 ? Yes</td>
    <td>7 = 17? No</td>
    <td>3</td>
  </tr>
  <tr>
    <td>3</td>
    <td>3 < 7 ? Yes</td>
    <td>17 = 17? Yes</td>
    <td></td>
  </tr>
</table>

Observe that after four comparisons, the algorithm found the key 17 and will display 'Element found at position 4'.

Let us now assume another arrangement of the elements in numList as [17, 8, -4, 7, 0, 2, 19] and search for the key K=17 in numList.

Table 6.3 Elements in numList alongwith their index value

<table>
  <tr>
    <th>Index in numList</th>
    <th>0</th>
    <th>1</th>
    <th>2</th>
    <th>3</th>
    <th>4</th>
    <th>5</th>
    <th>6</th>
  </tr>
  <tr>
    <th>Value</th>
    <td>17</td>
    <td>8</td>
    <td>-4</td>
    <td>7</td>
    <td>0</td>
    <td>2</td>
    <td>19</td>
  </tr>
</table>

Table 6.4 Linear search for key 17 in numList given in Table 6.3

<table>
  <tr>
    <th>index</th>
    <th>index < n</th>
    <th>numList[index]= key</th>
    <th>index=index+1</th>
  </tr>
  <tr>
    <td>0</td>
    <td>0 < 7 ? Yes</td>
    <td>17 = 17? Yes</td>
    <td>1</td>
  </tr>
</table>

From Table 6.4, it is clear that the algorithm had to make only 1 comparison to display 'Element found at position 1'. Thus, if the key to be searched is the first element in the list, the linear search algorithm will always have to make only 1 comparison. This is the minimum amount of work that the linear search algorithm would have to do.

Let us now assume another arrangement of the elements in numList as [8, -4, 7, 0, 2, 19, 17] and search for the key K =17 in numList.

On a dry run, we can find out that the linear search algorithm has to compare each element in the list till the end to display 'Element found at position 7'. Thus, if the key to be searched is the last element in the list, the linear search algorithm will have to make n comparisons, where n is the number of elements in the list. This is in fact the maximum amount of work the linear search algorithm would have to do.

Activity 6.2
In the list : L = [7,-1, 11,32,17,19,23,29,31, 37,43]
Determine the number of comparisons linear search takes to search for key = 43.

---

## Page 5

6.3 Binary Search

Consider a scenario where we have to find the meaning of the word Zoology in an English dictionary. Where do we search it in the dictionary?
  1. in the first half?
  2. around the middle?
  3. in the second half?

It is certainly more prudent to look for the word in the second half of the dictionary as the word starts with the alphabet 'Z'. On the other hand, if we were to find the meaning of the word Biology, we would have searched in the first half of the dictionary.

We were able to decide where to search in the dictionary because we are aware of the fact that all words in an English dictionary are placed in alphabetical order. Taking advantage of this, we could avoid unnecessary comparison through each word beginning from the first word of the dictionary and moving towards the end till we found the desired word. However, if the words in the dictionary were not alphabetically arranged, we would have to do linear search to find the meaning of a word.

The binary search is a search technique that makes use of the ordering of elements in the list to quickly search a key. For numeric values, the elements in the list may be arranged either in ascending or descending order of their key values. For textual 