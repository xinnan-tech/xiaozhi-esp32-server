from tinygrad import nn


class TinySileroVAD:
    def __init__(self):
        """
        from tinygrad.nn.state import safe_load, load_state_dict

        tiny_model = TinySileroVAD()
        state_dict = safe_load('data/silero_vad_16k.safetensors')
        load_state_dict(tiny_model, state_dict)
        """
        self.n_fft = 256
        self.stride = 128
        self.pad = 64
        self.cutoff = int(self.n_fft // 2) + 1
    
        self.stft_conv = nn.Conv1d(1, 258, kernel_size=256, stride=self.stride, padding=0, bias=False)
        self.conv1 = nn.Conv1d(129, 128, kernel_size=3, stride=1, padding=1)
        self.conv2 = nn.Conv1d(128, 64, kernel_size=3, stride=2, padding=1)
        self.conv3 = nn.Conv1d(64, 64, kernel_size=3, stride=2, padding=1)
        self.conv4 = nn.Conv1d(64, 128, kernel_size=3, stride=1, padding=1)

        self.lstm_cell = nn.LSTMCell(128, 128)
        self.final_conv = nn.Conv1d(128, 1, 1)

    def __call__(self, x, state=None):
        """
        # full audio example:
        import torch
        from tinygrad import Tensor

        wav = read_audio(audio_path, sampling_rate=16000).unsqueeze(0)
        num_samples = 512
        context_size = 64
        context = Tensor(np.zeros((1, context_size))).float()
        outs = []
        state = None
        if wav.shape[1] % num_samples:
            pad_num = num_samples - (wav.shape[1] % num_samples)
            wav = torch.nn.functional.pad(wav, (0, pad_num), 'constant', value=0.0)

        wav = torch.nn.functional.pad(wav, (context_size, 0))

        wav = Tensor(wav.numpy()).float()

        for i in tqdm(range(context_size, wav.shape[1], num_samples)):
            wavs_batch = wav[:, i-context_size:i+num_samples]
            out_chunk, state = tiny_model(wavs_batch, state)
            #outs.append(out_chunk.numpy())
            outs.append(out_chunk)

        predict = outs[0].cat(*outs[1:], dim=1).numpy()
        
        """
        if state is not None:
            state = (state[0], state[1])
        x = x.pad((0, self.pad), "reflect").unsqueeze(1)
        x = self.stft_conv(x)
        x = (x[:, :self.cutoff, :]**2 + x[:, self.cutoff:, :]**2).sqrt()
        x = self.conv1(x).relu()
        x = self.conv2(x).relu()
        x = self.conv3(x).relu()
        x = self.conv4(x).relu().squeeze(-1)
        h, c = self.lstm_cell(x, state)
        x = h.unsqueeze(-1)
        state = h.stack(c, dim=0)
        x = x.relu()
        x = self.final_conv(x).sigmoid()
        x = x.squeeze(1).mean(axis=1).unsqueeze(1)
        return x, state
