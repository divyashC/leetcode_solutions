class Solution:
    def twoSum(self, nums, target):
        for i in range(len(nums)):
            diff = target - nums[i]
            if diff in nums[i+1:]:
                index = nums[i + 1:].index(diff)+i+1
                return [i, index]
    
    # Second option but not recommended
    # for i in range(len(nums)):
        #     for j in range(i, len(nums)):
        #         if (nums[i] + nums[j] == target and i != j):
        #             return [i, j]
        #             break
