class Solution:
    def twoSum(self, nums, target):
        for i in range(len(nums)):
            diff = target - nums[i]
            if diff in nums[i+1:]:
                index = nums[i + 1:].index(diff)+i+1
                return [i, index]
