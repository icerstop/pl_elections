class Committee:
    def __init__(self, id, name, threshold, pastSupportEquivalence):
        self.id = id
        self.name = name
        self.threshold = threshold
        self.pastSupportEquivalence = pastSupportEquivalence

class Constituency:
    def __init__(self, number, size, pastSupport):
        self.number = number
        self.size = size
        self.pastSupport = pastSupport
        self.support = None
        self.mandates = None