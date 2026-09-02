from utils import init_jit_model, predict, calculate_best_thresholds, SileroVadDataset, SileroVadPadder
from omegaconf import OmegaConf
import torch
torch.set_num_threads(1)

if __name__ == '__main__':
    config = OmegaConf.load('config.yml')

    loader = torch.utils.data.DataLoader(SileroVadDataset(config, mode='val'),
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

    print('Making predicts...')
    all_predicts, all_gts = predict(model, loader, config.device, sr=8000 if config.tune_8k else 16000)
    print('Calculating thresholds...')
    best_ths_enter, best_ths_exit, best_acc = calculate_best_thresholds(all_predicts, all_gts)
    print(f'Best threshold: {best_ths_enter}\nBest exit threshold: {best_ths_exit}\nBest accuracy: {best_acc}')
