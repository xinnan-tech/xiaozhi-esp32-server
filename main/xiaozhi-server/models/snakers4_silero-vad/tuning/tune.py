from utils import SileroVadDataset, SileroVadPadder, VADDecoderRNNJIT, train, validate, init_jit_model
from omegaconf import OmegaConf
import torch.nn as nn
import torch


if __name__ == '__main__':
    config = OmegaConf.load('config.yml')

    train_dataset = SileroVadDataset(config, mode='train')
    train_loader = torch.utils.data.DataLoader(train_dataset,
                                               batch_size=config.batch_size,
                                               collate_fn=SileroVadPadder,
                                               num_workers=config.num_workers)

    val_dataset = SileroVadDataset(config, mode='val')
    val_loader = torch.utils.data.DataLoader(val_dataset,
                                             batch_size=config.batch_size,
                                             collate_fn=SileroVadPadder,
                                             num_workers=config.num_workers)

    if config.jit_model_path:
        print(f'Loading model from the local folder: {config.jit_model_path}')
        model = init_jit_model(config.jit_model_path, device=config.device)
    else:
        if config.use_torchhub:
            print('Loading model using torch.hub')
            model, _ = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                      model='silero_vad',
                                      onnx=False,
                                      force_reload=True)
        else:
            print('Loading model using silero-vad library')
            from silero_vad import load_silero_vad
            model = load_silero_vad(onnx=False)

    print('Model loaded')
    model.to(config.device)
    decoder = VADDecoderRNNJIT().to(config.device)
    decoder.load_state_dict(model._model_8k.decoder.state_dict() if config.tune_8k else model._model.decoder.state_dict())
    decoder.train()
    params = decoder.parameters()
    optimizer = torch.optim.Adam(filter(lambda p: p.requires_grad, params),
                                 lr=config.learning_rate)
    criterion = nn.BCELoss(reduction='none')

    best_val_roc = 0
    for i in range(config.num_epochs):
        print(f'Starting epoch {i + 1}')
        train_loss = train(config, train_loader, model, decoder, criterion, optimizer, config.device)
        val_loss, val_roc = validate(config, val_loader, model, decoder, criterion, config.device)
        print(f'Metrics after epoch {i + 1}:\n'
              f'\tTrain loss: {round(train_loss, 3)}\n',
              f'\tValidation loss: {round(val_loss, 3)}\n'
              f'\tValidation ROC-AUC: {round(val_roc, 3)}')

        if val_roc > best_val_roc:
            print('New best ROC-AUC, saving model')
            best_val_roc = val_roc
            if config.tune_8k:
                model._model_8k.decoder.load_state_dict(decoder.state_dict())
            else:
                model._model.decoder.load_state_dict(decoder.state_dict())
            torch.jit.save(model, config.model_save_path)
    print('Done')
