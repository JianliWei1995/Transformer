import torch
from torch.utils.data import Dataset

from collections import Counter
import typing
from pathlib import Path

from tqdm import tqdm
import pandas as pd
import numpy as np
import random

from torchtext.data.utils import get_tokenizer
from torchtext.vocab import vocab


class IMDBBertDataset(Dataset):
    # Define special tokens as attributes of class
    CLS = '[CLS]'
    PAD = '[PAD]'
    SEP = '[SEP]'
    MASK = '[MASK]'
    UNK = '[UNK]'

    MASK_PECENTAGE = 0.15

    MASKED_INDICES_COLUMN = 'masked_indices'
    TARGET_COLUMN = 'indices'
    NSP_TARGET_COLUMN = 'is_next'
    TOKEN_MASK_COLUMN = 'token_mask'

    OPTIMAL_LENGTH_PERCENTILE = 70

    def __init__(self, path, ds_from=None, ds_to=None, should_include_text=False):
        self.ds = pd.read_csv(path)['review']

        if ds_from is not None or ds_to is not None:
            self.ds = self.ds[ds_from:ds_to]

        self.tokenizer = get_tokenizer('basic_english')
        self.counter = Counter()
        self.vocab = None

        self.optimal_sentence_length = None
        self.should_include_text = should_include_text

        if should_include_text:
            self.columns = [
                'masked_sentence',
                self.MASKED_INDICES_COLUMN,
                'sentence',
                self.TARGET_COLUMN,
                self.TOKEN_MASK_COLUMN,
                self.NSP_TARGET_COLUMN
            ]
        else:
            self.columns = [
                self.MASKED_INDICES_COLUMN,
                self.TARGET_COLUMN,
                self.TOKEN_MASK_COLUMN,
                self.NSP_TARGET_COLUMN
            ]
        self.df = self.prepare_dataset()

    def __len__(self):
        return len(self.df)
    
    def __getitem__(self, idx):
        ...
    
    def prepare_dataset(self) -> pd.DataFrame:
        sentences = []
        nsp = []
        sentence_lens = []

        # Split dataset on sentences
        for review in self.ds:
            review_sentences = review.split('. ')
            sentences += review_sentences
            self._update_length(review_sentences, sentence_lens)
        self.optimal_sentence_length = self._find_optimal_sentence_length(sentence_lens)

        print("Create vocabulary")
        for sentence in tqdm(sentences):
            sen_tokens = self.tokenizer(sentence)
            self.counter.update(sen_tokens)

        self._fill_vocab()
    
        print("preprocessing dataset")
        for review in tqdm(self.ds):
            review_sentences = review.split('. ')
            if len(review_sentences) > 1:
                for i in range(len(review_sentences)-1):
                    # Create True NSP pair
                    first, second = self.tokenizer(review_sentences[i]), self.tokenizer(review_sentences[i+1])
                    nsp.append(self._create_item(first, second, 1))

                    # Create False NSP pair
                    first, second = self._select_false_nsp_sentences(sentences)
                    first, second = self.tokenizer(first), self.tokenizer(second)
                    nsp.append(self._create_item(first, second, 0))
                    
        df = pd.DataFrame(nsp, columns=self.columns)
        return df


    def _update_length(self, sentences: typing.List[str], lengths: typing.List[int]):
        sentences_lengths = [len(sentence.split()) for sentence in sentences]
        return lengths + sentences_lengths
    
    def _find_optimal_sentence_length(self, lengths: typing.List[int]):
        arr = np.array(lengths)
        return int(np.percentile(arr, self.OPTIMAL_LENGTH_PERCENTILE))
    
    def _fill_vocab(self):
        # Create a vocab
        self.vocab = vocab(self.counter, min_freq=2)

        # Insert special tokens, specials = [self.CLS, self.PAD, self.MASK, self.SEP, self.UNK]
        self.vocab.insert_token(self.CLS, 0)
        self.vocab.insert_token(self.PAD, 1)
        self.vocab.insert_token(self.MASK, 2)
        self.vocab.insert_token(self.SEP, 3)
        self.vocab.insert_token(self.UNK, 4)
        self.vocab.set_default_index(4)
    
    def _select_false_nsp_sentences(self, sentences: typing.List[str]):
        '''
        Select two sentences from all sentences but the second is not the next of the first sentence
        '''
        sentence_len = len(sentences)
        sentence_idx, next_sentence_idx = random.randint(0, sentence_len-1), random.randin(0, sentence_len-1)

        while next_sentence_idx==sentence_idx+1:
            next_sentence_idx = random.randint(0, sentence_len-1)
        return sentences[sentence_idx], sentences[next_sentence_idx]

    def _create_item(self):
        return [0,0,0]
    

if __name__ == '_main__':
    print(1)
    BASE_DIR = Path(__file__).resolve().parent.parent

    ds = IMDBBertDataset(
        BASE_DIR.joinpath('data/IMDB Dataset.csv'),
        ds_from=0,
        ds_to=50000,
        should_include_text=True
    )

    print(ds.df)