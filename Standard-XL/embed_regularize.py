import numpy as np

import torch

EPS = 1e-12

def embedded_dropout(embed, words, dropout=0.1, scale=None):
  if dropout:
    mask = embed.weight.data.new(embed.weight.size(0), 1).bernoulli_(1 - dropout)
    masked_embed_weight = mask * embed.weight / (1 - dropout)
    if EPS:
        masked_embed_weight.masked_fill_(mask.eq(0), EPS)
  else:
    masked_embed_weight = embed.weight
    # print(masked_embed_weight)
  if scale:
    masked_embed_weight = scale.expand_as(masked_embed_weight) * masked_embed_weight

  X = torch.nn.functional.embedding(words, masked_embed_weight,
    embed.padding_idx, embed.max_norm, embed.norm_type,
    embed.scale_grad_by_freq, embed.sparse
  )
  return X

if __name__ == '__main__':
  V = 50
  h = 4
  bptt = 10
  batch_size = 2

  embed = torch.nn.Embedding(V, h)

  words = np.random.random_integers(low=0, high=V-1, size=(batch_size, bptt))
  words = torch.LongTensor(words)

  origX = embed(words)
  X = embedded_dropout(embed, words)

  print(origX)
  print(X)