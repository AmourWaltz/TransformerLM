import mathimport timefrom data import Corpusimport torchimport torch.nn.functional as funcimport torch.optim as optimimport torch.utils.datafrom model import Transformerfrom model import ScheduledOptimif torch.cuda.is_available():    device = torch.device('cuda')    passelse:    device = torch.device('cpu')    passpassPAD = 0epochs = 8log_path = "../data/"log_flag = True# Apply label smoothing if needed.def cal_performance(pred, gold, smoothing=False):    # print(gold.size())    gold = gold.contiguous().view(-1)    voc_size = pred.size()[-1]    # print(voc_size)    pred = pred.contiguous().view(-1, voc_size)    # print(pred.size())    # print(gold)    loss = cal_loss(pred, gold, smoothing)    pred = pred.max(1)[1]    gold = gold.contiguous().view(-1)    non_pad_mask = gold.ne(PAD)    n_correct = pred.eq(gold)    n_correct = n_correct.masked_select(non_pad_mask).sum().item()    return loss, n_correct# Calculate cross entropy loss, apply label smoothing if needed.def cal_loss(pred, gold, smoothing):    if smoothing:        eps = 0.1        n_class = pred.size(1)        one_hot = torch.zeros_like(pred).scatter(1, gold.view(-1, 1), 1)        # torch.cuda.available, cuda cannot convert Tensor to numpy()        if torch.cuda.is_available():            one_hot = one_hot.cpu().numpy() * (1 - eps) + (1 - one_hot.cpu().numpy()) * eps / (n_class - 1)            pass        else:            one_hot = one_hot.numpy() * (1 - eps) + (1 - one_hot.numpy()) * eps / (n_class - 1)            pass        pass        log_prb = func.log_softmax(pred, dim=1)        # print(gold, gold.size())        non_pad_mask = gold.ne(PAD)        # print(non_pad_mask, non_pad_mask.size())        if torch.cuda.is_available():            loss = -(torch.tensor(one_hot).cuda() * log_prb).sum(dim=1)            pass        else:            loss = -(torch.tensor(one_hot) * log_prb).sum(dim=1)            pass        pass        loss = loss.masked_select(non_pad_mask).sum()  # average later        pass    else:        print(pred.size(), gold.size())        loss = func.cross_entropy(pred, gold, ignore_index=PAD, reduction='sum')        pass    pass    return loss# Epoch operation in training phase.def train_epoch(model, training_data, optimizer):    model.train()    total_loss = 0    n_word_total = 0    n_word_correct = 0    for loop_i, (inputs, targets, sent_lens) in enumerate(training_data):        # prepare data        # print("targets size: ", targets.size())        if loop_i % 1000 == 0:            print("train_loop: ", loop_i)            pass        pass        tar_rel = targets.t()        tar_rel = tar_rel[:, 1:]        optimizer.zero_grad()        pred, _, _, _ = model(inputs.t(), sent_lens, targets.t(), sent_lens)        # backward        loss, n_correct = cal_performance(pred[:, 1:, :], tar_rel, smoothing=True)        loss.backward()        # update parameters        optimizer.step_and_update_lr()        # note keeping        total_loss += loss.item()        non_pad_mask = tar_rel.ne(PAD)        n_word = non_pad_mask.sum().item()        n_word_total += n_word        n_word_correct += n_correct        pass    pass    loss_per_word = total_loss / n_word_total    accuracy = n_word_correct / n_word_total    return loss_per_word, accuracy# Epoch operation in evaluation phase.def eval_epoch(model, valid_data):    model.eval()    total_loss = 0    n_word_total = 0    n_word_correct = 0    with torch.no_grad():        for loop_i, (inputs, targets, sent_lens) in enumerate(valid_data):            # prepare data            tar_rel = targets.t()            tar_rel = tar_rel[:, 1:]            # forward            pred, _, _, _ = model(inputs.t(), sent_lens, targets.t(), sent_lens)            loss, n_correct = cal_performance(pred[:, 1:, :], tar_rel, smoothing=True)            # note keeping            total_loss += loss.item()            non_pad_mask = tar_rel.ne(PAD)            n_word = non_pad_mask.sum().item()            n_word_total += n_word            n_word_correct += n_correct            pass        pass    pass    loss_per_word = total_loss / n_word_total    accuracy = n_word_correct / n_word_total    return loss_per_word, accuracy# Training process.def train(model, training_data, validation_data, optimizer):    valid_accus = []    model.to(device)    log_train_file = log_path + 'train.log'    log_valid_file = log_path + 'valid.log'    print('[Info] Training performance will be written to file: {} and {}'.format(        log_train_file, log_valid_file))    with open(log_train_file, 'w') as log_tf, open(log_valid_file, 'w') as log_vf:        log_tf.write('epoch, loss, ppl, accuracy\n')        log_vf.write('epoch, loss, ppl, accuracy\n')        pass    pass    for epoch_i in range(epochs):        print('[ Epoch', epoch_i, ']')        start = time.time()        train_loss, train_accu = train_epoch(model, training_data, optimizer)        print('  - (Training)   ppl: {ppl: 8.5f}, accuracy: {accu:3.3f} %, elapse: {elapse:3.3f} min'.format(            ppl=math.exp(train_loss), accu=100 * train_accu, elapse=(time.time() - start) / 60))        start = time.time()        valid_loss, valid_accu = eval_epoch(model, validation_data)        print('  - (Validation) ppl: {ppl: 8.5f}, accuracy: {accu:3.3f} %, elapse: {elapse:3.3f} min'.format(            ppl=math.exp(valid_loss), accu=100 * valid_accu, elapse=(time.time() - start) / 60))        valid_accus += [valid_accu]        if log_flag:            with open(log_train_file, 'a') as log_tf, open(log_valid_file, 'a') as log_vf:                log_tf.write('{epoch}, {loss: 8.5f}, {ppl: 8.5f}, {accu:3.3f}\n'.format(                    epoch=epoch_i, loss=train_loss, ppl=math.exp(train_loss), accu=100 * train_accu))                log_vf.write('{epoch}, {loss: 8.5f}, {ppl: 8.5f}, {accu:3.3f}\n'.format(                    epoch=epoch_i, loss=valid_loss, ppl=math.exp(valid_loss), accu=100 * valid_accu))                pass            pass        pass    pass    return model# Tesing process.def test(model, test_data):    total_loss = 0    test_word_total = 0    test_word_correct = 0    log_test_file = log_path + 'test.log'    print('[Info] Testing performance will be written to file: {}'.format(log_test_file))    with open(log_test_file, 'w') as log_tf:        log_tf.write('loss, ppl, accuracy\n')        pass    pass    for epoch_i in range(epochs):        with torch.no_grad():            for _, (test_inputs, test_targets, sent_lens) in enumerate(test_data):                # transpose targets dataset and cut first line                gold = test_targets.t()[:, 1:]                pred, _, _, _ = model(test_inputs.t(), sent_lens, test_targets.t(), sent_lens)                loss, n_correct = cal_performance(pred[:, 1:, :], test_targets.t()[:, 1:], smoothing=True)                total_loss += loss.item()                non_pad_mask = gold.ne(PAD)                words = non_pad_mask.sum().item()                test_word_total += words                test_word_correct += n_correct            pass        pass    pass    test_loss = total_loss / test_word_total    test_accu = test_word_correct / test_word_total    print('  - (Testing) ppl: {ppl: 8.5f}, accuracy: {accu:3.3f} %'.format(        ppl=math.exp(test_loss), accu=100 * test_accu))    if log_flag:        with open(log_test_file, 'a') as log_tf:            log_tf.write('{loss: 8.5f}, {ppl: 8.5f}, {accu:3.3f}\n'.format(                 loss=test_loss, ppl=math.exp(test_loss), accu=100 * test_accu))            pass        pass    passdef main():    # Preparing DataLoader.    corpus = Corpus('../data/ptb', train_batch_size=8, valid_batch_size=16, test_batch_size=1)    print("[Info] train length: ", len(corpus.train_data), "\n",          "val length: ", len(corpus.valid_data), "\n",          "test length: ", len(corpus.test_data))    # Loading Dataset and set parameters.    training_data, validation_data, testing_data = corpus.train_loader, corpus.valid_loader, corpus.test_loader    vocab_size = len(corpus.voc)    max_length = corpus.max_length    print("max_length: ", max_length)    num_layers, model_dim, num_heads, ffn_dim, dropout = 6, 512, 8, 2048, 0.2    transformer = Transformer(src_vocab_size=vocab_size, src_max_len=max_length,                              tgt_vocab_size=vocab_size, tgt_max_len=max_length,                              num_layers=num_layers, model_dim=model_dim, num_heads=num_heads,                              ffn_dim=ffn_dim, dropout=dropout).to(device)    optimizer = ScheduledOptim(optim.Adam(        filter(lambda x: x.requires_grad, transformer.parameters()),        betas=(0.9, 0.98), eps=1e-09),        model_dim)    model = train(transformer, training_data, validation_data, optimizer)    test(model, testing_data)    passif __name__ == '__main__':    main()