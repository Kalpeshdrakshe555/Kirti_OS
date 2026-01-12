"""Q) We have a list of names. Write a program to sort the list based on the second name.

Input: [Sachin Tendulkar, Virat Kohli, Mahendra Singh Dhoni]
Output: [Virat Kohli, Mahendra Singh Dhoni, Sachin Tendulkar]

inpute = [Sachin Tendulkar, Virat Kohli, Mahendra Singh Dhoni]
ls=['a','b','c','d','e','f','g','h','i','j']
for i in range inpute :
    if i """

ls=[5,6,3,8,9]
n=len(ls)
ls
for i in range (0,n):
    if ls[i]> ls[i+1] :
        ls[i],ls[i+1]=ls[i+1],ls[i]
    

