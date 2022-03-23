from typing import Union


class Interval(object):
    # half-closed form [a, b)
    def __init__(self, t1, t2):
        self.start, self.end = (t1, t2) if t1 < t2 else (t2, t1)

    def __repr__(self):
        return '{} - {}'.format(self.start, self.end)

    @property
    def length(self):
        return self.end - self.start

    def __add__(self, v: Union[int, float]):
        self.start += v
        self.end += v
        return self

    def __sub__(self, v: Union[int, float]):
        self.start -= v
        self.end -= v
        return self

    def __mul__(self, v: Union[int, float]):
        self.start *= v
        self.end *= v
        return self

    def is_overlap(self, o):
        assert isinstance(o, Interval)
        return not ((self.end <= o.start) or (o.end <= self.start))

    def is_in(self, o):
        assert isinstance(o, Interval)
        return o.start <= self.start and self.end <= o.end

    # self.start <= o.start <= o.end <= self.end
    def is_wrap(self, o):
        assert isinstance(o, Interval)
        return self.start <= o.start and o.end <= self.end

    def intersection(self, o):
        assert isinstance(o, Interval)
        return Interval(max(self.start, o.start), min(self.end, o.end)) if self.is_overlap(o) else None

    # if not overlap -> self
    def union(self, o):
        assert isinstance(o, Interval)
        return Interval(min(self.start, o.start), max(self.end, o.end)) if self.is_overlap(o) else None

    def IOU(self, o):
        try:
            intersect = self.intersection(o)
            union = self.union(o)
            iou = intersect.length / union.length
        except:
            iou = 0
        return iou
