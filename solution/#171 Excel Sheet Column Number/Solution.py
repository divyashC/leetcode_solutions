class Solution:
    def titleToNumber(self, columnTitle: str) -> int:
        col = 0
        for ch in columnTitle:
            col = col * 26
            col += ord(ch) - ord('A') + 1

        return col
