class Solution:
    def isPalindrome(self, x: int) -> bool:
        strNum = str(x)[::-1]
        return str(x) == strNum
