#[derive(Debug, Clone, Copy)]
pub enum SampleRate {
    EightkHz,
    SixteenkHz,
}

impl From<SampleRate> for i64 {
    fn from(value: SampleRate) -> Self {
        match value {
            SampleRate::EightkHz => 8000,
            SampleRate::SixteenkHz => 16000,
        }
    }
}

impl From<SampleRate> for usize {
    fn from(value: SampleRate) -> Self {
        match value {
            SampleRate::EightkHz => 8000,
            SampleRate::SixteenkHz => 16000,
        }
    }
}

#[derive(Debug)]
pub struct VadParams {
    pub frame_size: usize,
    pub threshold: f32,
    pub min_silence_duration_ms: usize,
    pub speech_pad_ms: usize,
    pub min_speech_duration_ms: usize,
    pub max_speech_duration_s: f32,
    pub sample_rate: usize,
}

impl Default for VadParams {
    fn default() -> Self {
        Self {
            frame_size: 32,  // 32ms for 512 samples at 16kHz
            threshold: 0.5,
            min_silence_duration_ms: 0,
            speech_pad_ms: 64,
            min_speech_duration_ms: 64,
            max_speech_duration_s: f32::INFINITY,
            sample_rate: 16000,
        }
    }
}

#[derive(Debug, Default)]
pub struct TimeStamp {
    pub start: i64,
    pub end: i64,
}

impl std::fmt::Display for TimeStamp {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "[start:{:08}, end:{:08}]", self.start, self.end)
    }
}
