class Solution:
    def lengthOfLastWord(self, s: str) -> int:
        lis = list(s.split(" "))
        last = len(lis) - 1
        while (lis[last] == ''):
            last -= 1
        return len(lis[last])
