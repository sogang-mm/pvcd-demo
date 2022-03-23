import numpy as np
import faiss
from pathlib import Path
from search.TemporalNetwork import TemporalNetwork as TN


class Engine:
    def __init__(self, reference, gpu=False):
        self.reference = self.check_available_reference(reference)
        self.index, self.loc_to_ids = self.build_index(gpu=gpu)
        print('Build Engine')
        self.tn_param = {'time_window': 10,
                         'min_match': 5,
                         'min_score': -1,
                         'seg_len': 5}

    def check_available_reference(self, reference):
        reference = [r for r in reference if Path(r['feature']).is_file()]
        return reference

    def build_index(self, gpu=False):
        features = {r['id']: np.load(r['feature']) for r in self.reference}
        _features = np.concatenate([f for f in features.values()])
        index = faiss.IndexFlatIP(_features.shape[1])
        index.add(_features)

        if gpu:
            index = faiss.index_cpu_to_all_gpus(index)

        ids = ([(vid, fid) for vid, f in features.items() for fid in range(f.shape[0])])
        loc_to_id = np.vectorize(lambda x: ids[x])

        return index, loc_to_id

    def search_nearest(self, query, topk):
        vid, fid, dist = self.find_nearest_feature(query, topk)
        return vid, fid, dist

    def find_nearest_feature(self, query, topk=50):
        dist, idx = self.index.search(query, topk)
        vid, fid = self.loc_to_ids(idx)
        return vid, fid, dist

    def temporal_align(self, video_idx, frame_idx, dist, window, score, match):
        result = TN(dist, video_idx, frame_idx).fit(window, score, match)

        return result
