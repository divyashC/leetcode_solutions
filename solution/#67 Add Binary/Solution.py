class Solution:
    def addBinary(self, a: str, b: str) -> str:
        return format(int(int(a, 2) + int(int(b, 2))), 'b')
