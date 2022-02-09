class Solution:
    def romanToInt(self, s: str) -> int:
        romanNumbers = {'I': 1,
                        'V': 5,
                        'X': 10,
                        'L': 50,
                        'C': 100,
                        'D': 500,
                        'M': 1000}
        intNum = 0
        # decrementing from length of s-1 to 0 by 1
        for i in range(len(s)-1, -1, -1):
            num = romanNumbers[s[i]]
            if 3*num < intNum:
                intNum -= num
            else:
                intNum += num
        return intNum
