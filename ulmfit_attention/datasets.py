from fastai.text import *
from hyperspace_explorer.configurables import RegisteredAbstractMeta, Configurable


class Dataset(Configurable, metaclass=RegisteredAbstractMeta, is_registry=True):
    @abc.abstractmethod
    def get_training_sample(self, seed: int) -> TextClasDataBunch:
        """If seed==0, should include the longest text"""
        pass

    @abc.abstractmethod
    def get_test_as_valid(self) -> TextClasDataBunch:
        pass

    @classmethod
    def get_default_config(cls) -> Dict:
        return {}


class IMDB(Dataset):
    def __init__(self, size: int, bs: int, eval_bs: int):
        super().__init__()
        self.size = size
        self.bs = bs
        self.eval_bs = eval_bs
        self.path = untar_data(URLs.IMDB)
        self.vocab_path = self.path / 'tmp_clas' / 'itos.pkl'
        self.vocab = Vocab.load(self.vocab_path)
        self._test_set_cache = self.path / 'test_as_valid.pkl'

    def get_training_sample(self, seed: int) -> TextClasDataBunch:
        default_processors = [OpenFileProcessor(), TokenizeProcessor(), NumericalizeProcessor(vocab=self.vocab)]
        return (TextList(self._sample_paths(seed, include_longest=(seed == 0)), vocab=self.vocab, path=self.path,
                         processor=default_processors)
                .split_none()
                .label_from_folder(classes=['neg', 'pos'])
                .databunch(bs=self.bs))

    def get_test_as_valid(self) -> TextClasDataBunch:
        try:
            ds = load_data(self.path, self._test_set_cache, bs=self.bs)
        except FileNotFoundError:
            print('Loading the test set from source, no cached version found')
            ds = (TextList.from_folder(self.path, vocab=self.vocab)
                  .split_by_folder(valid='test')
                  .label_from_folder(classes=['neg', 'pos'])
                  .databunch(bs=self.bs))
            ds.save(self._test_set_cache)
        return ds

    def _sample_paths(self, seed: int, include_longest: bool = False) -> List[Path]:
        """Balanced sample of the IMDB train set. Include_longest can be used early to ensure OOM wont happen later"""
        s = random.getstate()
        random.seed(seed)
        if include_longest:
            # including biggest files from each class. Not guaranteed to have the most tokens, but should be good enough
            pos_all, neg_all = [
                sorted(list((self.path / 'train' / label).iterdir()), key=lambda x: x.stat().st_size, reverse=True)
                for label in ['pos', 'neg']]
            pos, neg = [[lst[0]] + random.sample(lst, self.size // 2 - 1) for lst in [pos_all, neg_all]]
        else:
            pos, neg = [random.sample(list((self.path / 'train' / label).iterdir()), self.size // 2)
                        for label in ['pos', 'neg']]
        random.setstate(s)
        return pos + neg
