class Solution:
    def plusOne(self, digits: List[int]) -> List[int]:
        digits = [str(int) for int in digits]
        number = str(int(''.join(digits)) + 1)
        return list(map(int, number))
