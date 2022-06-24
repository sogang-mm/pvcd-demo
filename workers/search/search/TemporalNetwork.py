from collections import defaultdict
import numpy as np

from .utils import Interval


class TemporalNetwork(object):
    def __init__(self, D, video_idx, frame_idx, numpy=True):
        # self.time_window, self.min_match, self.min_score = time_window, min_match, min_score
        self.numpy = numpy

        # [# of query index, topk]
        self.video_index = video_idx
        self.frame_index = frame_idx
        self.dist = D

        self.query_length = D.shape[0]
        self.topk = D.shape[1]

        # dist, count, query start, reference start
        self.paths = np.empty((*D.shape, 4), dtype=object)

    def find_previous_linkable_nodes(self, t, r, window, score):
        video_idx, frame_idx = self.video_index[t, r], self.frame_index[t, r]
        min_prev_time = max(0, t - window)

        # find previous nodes that have (same video index) and (frame timestamp - wnd <= previous frame timestamp < frame timestamp)
        time, rank = np.where((self.dist[min_prev_time:t, ] >= score) &
                              (self.video_index[min_prev_time:t, ] == video_idx) &
                              (self.frame_index[min_prev_time:t, ] >= frame_idx - window) &
                              (self.frame_index[min_prev_time:t, ] < frame_idx)
                              )

        return np.stack((time + min_prev_time, rank), axis=-1)

    def find_previous_linkable_nodes_naive(self, t, r, window, score):
        video_idx, frame_idx = self.video_index[t, r], self.frame_index[t, r]
        min_prev_time = max(0, t - window)
        nodes = []
        for prev_time in range(min_prev_time, t):
            for k in range(self.topk):
                if self.dist[prev_time, k] >= score and \
                        self.video_index[prev_time, k] == video_idx and \
                        (frame_idx - window) <= self.frame_index[prev_time, k] < frame_idx:
                    nodes.append([prev_time, k])
        return np.array(nodes)

    def _find_path(self, window, score):
        for time in range(self.query_length):
            for rank in range(self.topk):
                if self.dist[time, rank] > score:
                    if self.numpy:
                        prev_linkable_nodes = self.find_previous_linkable_nodes(time, rank, window, score)
                    else:
                        prev_linkable_nodes = self.find_previous_linkable_nodes_naive(time, rank, window, score)
                else:
                    prev_linkable_nodes = []

                if len(prev_linkable_nodes):
                    # priority : count, path length, path score
                    prev_time, prev_rank = max(prev_linkable_nodes, key=lambda x: (self.paths[x[0], x[1], 1],
                                                                                   self.frame_index[time, rank] -
                                                                                   self.paths[x[0], x[1], 3],
                                                                                   self.paths[x[0], x[1], 0]
                                                                                   ))
                    prev_path = self.paths[prev_time, prev_rank]
                    self.paths[time, rank] = [prev_path[0] + self.dist[time, rank],
                                              prev_path[1] + 1,
                                              prev_path[2],
                                              prev_path[3]]
                else:
                    self.paths[time, rank] = [self.dist[time, rank],
                                              1,
                                              time,
                                              self.frame_index[time, rank]]

    def connect_path(self, match):
        candidate = defaultdict(list)
        for time in reversed(range(self.query_length)):
            for rank in range(self.topk):
                score, count, q_start, r_start = self.paths[time, rank]
                if count >= match:
                    video_idx, frame_idx = self.video_index[time, rank], self.frame_index[time, rank]
                    q = Interval(q_start, time + 1)
                    r = Interval(r_start, frame_idx + 1)
                    path = (video_idx, q, r, score, count)
                    flag = True
                    for n, c in enumerate(candidate[video_idx]):
                        if path[1].is_wrap(c[1]) and path[2].is_wrap(c[2]):
                            candidate[video_idx][n] = path
                            flag = False
                            break
                        elif path[1].is_in(c[1]) and path[2].is_in(c[2]):
                            flag = False
                            break
                    if flag:
                        candidate[video_idx].append(path)
        for video, path in candidate.items():
            candidate[video] = self.nms_path(path)

        return candidate

    def fit(self, window=10, score=-1, match=5, seg_len=5):
        self._find_path(window, score)
        candidate = self.connect_path(match)
        labels = ['id', 'query', 'reference', 'score', 'match']
        candidate = [dict(zip(labels, [c[0], (c[1] * seg_len).__dict__, (c[2] * seg_len).__dict__, c[3], c[4]]))
                     for cc in candidate.values() for c in cc]

        candidate = sorted(candidate, key=lambda x: x['score'], reverse=True)

        return candidate

    def _fit(self, window=10, score=-1, match=5, seg_len=5):
        # find linkable nodes
        for time in range(self.query_length):
            for rank in range(self.topk):
                # if self.dist[time,rank]>self.min_score:
                #     if self.numpy:
                #         prev_linkable_nodes = self.find_previous_linkable_nodes(time, rank)
                #     else:
                #         prev_linkable_nodes = self.find_previous_linkable_nodes_naive(time, rank)
                # else:
                #     prev_linkable_nodes=[]
                if self.numpy:
                    prev_linkable_nodes = self.find_previous_linkable_nodes(time, rank, window, score)
                else:
                    prev_linkable_nodes = self.find_previous_linkable_nodes_naive(time, rank, window, score)
                if not len(prev_linkable_nodes):
                    self.paths[time, rank] = [self.dist[time, rank],
                                              1,
                                              time,
                                              self.frame_index[time, rank]]
                else:
                    # priority : count, path length, path score
                    prev_time, prev_rank = max(prev_linkable_nodes, key=lambda x: (self.paths[x[0], x[1], 1],
                                                                                   self.frame_index[time, rank] -
                                                                                   self.paths[x[0], x[1], 3],
                                                                                   self.paths[x[0], x[1], 0]
                                                                                   ))
                    prev_path = self.paths[prev_time, prev_rank]
                    self.paths[time, rank] = [prev_path[0] + self.dist[time, rank],
                                              prev_path[1] + 1,
                                              prev_path[2],
                                              prev_path[3]]

        # connect and filtering paths
        candidate = defaultdict(list)
        for time in reversed(range(self.query_length)):
            for rank in range(self.topk):
                score, count, q_start, r_start = self.paths[time, rank]
                if count >= match:
                    video_idx, frame_idx = self.video_index[time, rank], self.frame_index[time, rank]
                    q = Interval(q_start, time + 1)
                    r = Interval(r_start, frame_idx + 1)
                    path = (video_idx, q, r, score, count)
                    flag = True
                    for n, c in enumerate(candidate[video_idx]):
                        if path[1].is_wrap(c[1]) and path[2].is_wrap(c[2]):
                            candidate[video_idx][n] = path
                            flag = False
                            break
                        elif path[1].is_in(c[1]) and path[2].is_in(c[2]):
                            flag = False
                            break
                    if flag:
                        candidate[video_idx].append(path)

        # remove overlap path
        for video, path in candidate.items():
            candidate[video] = self.nms_path(path)

        # candidate = [[c[0], c[1], c[2], c[3], c[4]] for cc in candidate.values() for c in cc]
        labels = ['id', 'query', 'reference', 'score', 'match']
        candidate = [dict(zip(labels, [c[0], c[1] * seg_len, c[2] * seg_len, c[3], c[4]])) for cc in candidate.values()
                     for c in cc]

        return candidate

    def nms_path(self, path):
        l = len(path)
        path = np.array(sorted(path, key=lambda x: (x[4], x[3], x[2].length, x[1].length), reverse=True))

        keep = np.array([True] * l)
        overlap = np.vectorize(lambda x, a: x.is_overlap(a))
        for i in range(l - 1):
            if keep[i]:
                keep[i + 1:] = keep[i + 1:] & \
                               (~(overlap(path[i + 1:, 1], path[i, 1]) & overlap(path[i + 1:, 2], path[i, 2])))
        path = path.tolist()
        path = [path[n] for n in range(l) if keep[n]]

        return path
