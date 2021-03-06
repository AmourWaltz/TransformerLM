import os
import torch
import torch.utils.data as data
import unicodedata
import time

data_version = 0

if torch.cuda.is_available():
    device = torch.device('cuda')
    pass
else:
    device = torch.device('cpu')
    pass
pass

# <GO>/<SOS>: start of sentence.
SOS = '<s>'
# <EOS>: end of sentence.
EOS = '</s>'
# <UNK>: represent uncommon words.
UNK = '<unk>'
NUM = '<num>'


class Vocabulary(object):
    """
    Vocabulary: establish indexes to words.
    """

    def __init__(self, vocfile, use_num=True):
        super(Vocabulary, self).__init__()
        self.use_num = use_num
        self.word2idx = {}
        self.word_feq = {}
        self.idx2word = dict()
        self.word2idx[SOS] = 0
        self.idx2word[0] = SOS
        self.word2idx[EOS] = 1
        self.idx2word[1] = EOS
        words = open(vocfile, 'r').read().strip().split('\n')
        # Look up the vocabulary as a list.
        # print("vocabulary: ", words)

        for loop_i, word in enumerate(words):
            if data_version == 2:
                num_word = len(str(loop_i)) + 1
                word = word[:-num_word]
                pass
            pass

            # print(word)
            if self.use_num and self.is_number(word):
                word = NUM
                pass
            if word not in self.word2idx and word != UNK:
                # Establish the dictionary.
                idx = len(self.word2idx)
                self.word2idx[word] = idx
                self.idx2word[idx] = word
                pass
            pass
        pass

        self.word2idx[UNK] = len(self.word2idx)
        self.idx2word[len(self.word2idx)] = UNK
        self.vocsize = len(self.word2idx)
        pass

    # Convert word to its index.
    def word2id(self, word):
        if self.use_num and self.is_number(word):
            word = NUM
            pass
        pass

        if word in self.word2idx:
            # self.word_feq[word] += 1
            return self.word2idx[word]
        else:
            # if word == 'email':
            #     self.email += 1
            #     pass
            # elif word == 'website':
            #     self.website += 1
            #     pass
            # elif word == '-em':
            #     self.em += 1
            #     pass
            # pass
            return self.word2idx[UNK]
        pass

    # Convert index to word.
    def id2word(self, idx):
        if idx in self.idx2word:
            return self.idx2word[idx]
        else:
            return UNK

    @staticmethod
    def is_number(word):
        word = word.replace(',', '')  # 10,000 -> 10000
        word = word.replace(':', '')  # 5:30 -> 530
        word = word.replace('-', '')  # 17-08 -> 1708
        word = word.replace('/', '')  # 17/08/1992 -> 17081992
        word = word.replace('th', '')  # 20th -> 20
        word = word.replace('rd', '')  # 93rd -> 20
        word = word.replace('nd', '')  # 22nd -> 20
        word = word.replace('m', '')  # 20m -> 20
        word = word.replace('s', '')  # 20s -> 20
        try:
            float(word)
            return True
        except ValueError:
            pass
        try:
            unicodedata.numeric(word)
            return True
        except (TypeError, ValueError):
            pass
        return False

    def __len__(self):
        return self.vocsize


# Using Dataset to load txt data
class TextDataset(data.Dataset):
    def __init__(self, txtfile, voc):
        """
        :param txtfile: Path of txt.
        :param voc: Established vocabulary.
        """
        self.words, self.ids = self.tokenize(txtfile, voc)
        self.nline = len(self.ids)
        self.n_sents = len(self.ids)
        self.n_words = sum([len(ids) for ids in self.ids])
        self.n_unks = len([index for ids in self.ids for index in ids if index == voc.word2id(UNK)])

    @staticmethod
    # Devide passage into words.
    def tokenize(txtfile, voc):
        assert os.path.exists(txtfile)
        lines = open(txtfile, 'r').readlines()
        words, ids = [], []
        for _, line in enumerate(lines):
            tokens = line.strip().split()
            # print("current sentence: ", tokens)
            if len(tokens) == 0:
                continue
                pass
            pass

            # Convert word sequence into index sequence.
            # Words append a list of a sentence.
            words.append([SOS])
            # print(words)
            ids.append([voc.word2id(SOS)])
            for token in tokens:
                # print("Voc lengths: ", len(voc.idx2word), voc.word2id('wwwwww'))
                if voc.word2id(token) + 1 < len(voc.idx2word):
                    words[-1].append(token)
                    ids[-1].append(voc.word2id(token))
                    pass
                else:
                    words[-1].append(UNK)
                    ids[-1].append(voc.word2id(UNK))
                    # Test on 7.5.
                    # print("word UNK", words[-1])
                    pass
                pass
            pass

            # Ends to each sentence.
            words[-1].append(EOS)
            ids[-1].append(voc.word2id(EOS))
            pass
        pass

        return words, ids

    def __len__(self):
        return self.n_sents

    def __repr__(self):
        return '#Sents=%d, #Words=%d, #UNKs=%d' % (self.n_sents, self.n_words, self.n_unks)

    def __getitem__(self, index):
        return self.ids[index]


# Load datasets and make train-test dataset
class Corpus(object):
    """
    Establish dictionary: map words into index and complete index sequences.
    Split sentences in train valid and test dataset into batches and convert them to index sequences.
    """

    def __init__(self, data_dir, train_batch_size, valid_batch_size, test_batch_size):
        super(Corpus, self).__init__()
        if data_version == 0:
            self.voc = Vocabulary(os.path.join(data_dir, 'voc.txt'))
            self.train_data = TextDataset(os.path.join(data_dir, 'train.txt'), self.voc)
            self.valid_data = TextDataset(os.path.join(data_dir, 'valid.txt'), self.voc)
            self.test_data = TextDataset(os.path.join(data_dir, 'test.txt'), self.voc)
            pass
        elif data_version == 2:
            self.voc = Vocabulary(os.path.join(data_dir, 'words.txt'))
            self.train_data = TextDataset(os.path.join(data_dir, 'fisher.txt'), self.voc)
            self.valid_data = TextDataset(os.path.join(data_dir, 'dev.txt'), self.voc)
            self.test_data = TextDataset(os.path.join(data_dir, 'swbd.txt'), self.voc)
            pass
        pass

        # print("lengths: ", len(self.train_data), len(self.valid_data), len(self.test_data))
        # print(list(map(len, self.train_data.words)))
        train_lens = list(map(len, self.train_data.words))
        valid_lens = list(map(len, self.valid_data.words))
        test_lens = list(map(len, self.valid_data.words))

        # max_length: sentences maximum length to align.
        self.max_length = max(max(train_lens), max(valid_lens), max(test_lens))
        # print(self.voc.id2word(9991))
        self.train_loader = data.DataLoader(self.train_data, batch_size=train_batch_size,
                                            shuffle=True, num_workers=0, collate_fn=collate_fn, drop_last=False)
        self.valid_loader = data.DataLoader(self.valid_data, batch_size=valid_batch_size,
                                            shuffle=True, num_workers=0, collate_fn=collate_fn, drop_last=False)
        self.test_loader = data.DataLoader(self.test_data, batch_size=test_batch_size,
                                           shuffle=True, num_workers=0, collate_fn=collate_fn, drop_last=False)

    def __repr__(self):
        return 'Train: %s\n' % self.train_data + 'Valid: %s\n' % self.valid_data + 'Test: %s\n' % self.test_data


# Merge a list of samples with variable sizes by padding to form a mini-batch of Tensors.
def collate_fn(batch):
    # map(func, list): map list using func.
    # sent_lens = torch.LongTensor(list(map(len, batch)))
    sent_len_list = torch.tensor(list(map(len, batch))).long()
    max_len = sent_len_list.max().numpy()
    batchsize = len(batch)
    # Build a variable identical with sent_batch using new_zeros,
    # global max_length
    sent_batch = sent_len_list.new_zeros((batchsize, max_len))
    # zip(): Pack objects into tuples.
    # Align sentences by padding 0.
    # global max_length
    for idx, (sent, sent_len) in enumerate(zip(batch, sent_len_list)):
        sent_batch[idx, :sent_len] = torch.tensor(sent).long()
        pass
    pass

    # Resort batch by descending sentences length list.
    sent_length, perm_idx = sent_len_list.sort(0, descending=True)
    sent_batch = sent_batch[perm_idx]
    sent_batch = sent_batch.t().contiguous()
    # After transpose and contiguous, operate on dim=0.
    inputs_batch = sent_batch[0: max_len - 1]
    targets_batch = sent_batch[1: max_len]
    # sent_length.sub_(1) # test on 7.5.
    sent_length -= 1
    pass

    return inputs_batch.to(device), targets_batch.to(device), sent_length.to(device)


if __name__ == '__main__':
    time_start = time.time()
    corpus = Corpus('data/ptb', train_batch_size=8, valid_batch_size=16, test_batch_size=1)

    for _, (inputs, targets, sent_lens) in enumerate(corpus.train_loader):
        print("train inputs: ", inputs, inputs.size(), "\n",
              "train targets: ", targets, targets.size(), "\n",
              "train sent_length: ", sent_lens)
        break
        pass
    for _, (inputs, targets, sent_lens) in enumerate(corpus.valid_loader):
        print("valid inputs size: ", inputs.size(), "\n",
              "valid targets size: ", targets.size(), "\n",
              "valid sent_length: ", sent_lens)
        break
        pass
    for _, (inputs, targets, sent_lens) in enumerate(corpus.test_loader):
        print("test inputs size: ", inputs.size(), "\n",
              "test targets size: ", targets.size(), "\n",
              "test sent_length: ", sent_lens)
        break
        pass
    pass
    time_end = time.time()
    print(time_end - time_start)
