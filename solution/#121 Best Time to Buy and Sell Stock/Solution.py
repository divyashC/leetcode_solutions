class Solution:
    def maxProfit(self, prices: List[int]) -> int:
        maxProfit = 0
        minAmount = float('inf')
        for i in prices:
            minAmount = min(minAmount, i)
            maxProfit = max(maxProfit, i - minAmount)
        return maxProfit
