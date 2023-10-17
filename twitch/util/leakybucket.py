
class LeakyBucketException(Exception):
    pass


class LeakyBucket:
    def __init__(self, capacity):
        self.capacity = capacity
        self.bucket = []

    def add(self, data, throw=False):
        if data in self.bucket and throw:
            raise LeakyBucketException("Item in bucket")

        self.bucket.append(data)
        if len(self.bucket) > self.capacity:
            self.bucket.pop(0)

    def get(self):
        if len(self.bucket) > 0:
            return self.bucket.pop(0)
        else:
            return None

    def is_empty(self):
        return len(self.bucket) == 0

    def is_full(self):
        return len(self.bucket) == self.capacity

    def clean(self):
        self.bucket = []