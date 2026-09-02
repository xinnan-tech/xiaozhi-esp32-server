mod silero;
mod utils;
mod vad_iter;

fn main() {
    let model_path = std::env::var("SILERO_MODEL_PATH")
        .unwrap_or_else(|_| String::from("../../src/silero_vad/data/silero_vad.onnx"));
    let audio_path = std::env::args()
        .nth(1)
        .unwrap_or_else(|| String::from("recorder.wav"));
    let mut wav_reader = hound::WavReader::open(audio_path).unwrap();
    let sample_rate = match wav_reader.spec().sample_rate {
        8000 => utils::SampleRate::EightkHz,
        16000 => utils::SampleRate::SixteenkHz,
        _ => panic!("Unsupported sample rate. Expect 8 kHz or 16 kHz."),
    };
    if wav_reader.spec().sample_format != hound::SampleFormat::Int {
        panic!("Unsupported sample format. Expect Int.");
    }
    let content = wav_reader
        .samples()
        .filter_map(|x| x.ok())
        .collect::<Vec<i16>>();
    assert!(!content.is_empty());
    let silero = silero::Silero::new(sample_rate, model_path).unwrap();
    let vad_params = utils::VadParams {
        sample_rate: sample_rate.into(),
        ..Default::default()
    };
    let mut vad_iterator = vad_iter::VadIter::new(silero, vad_params);
    vad_iterator.process(&content).unwrap();
    for timestamp in vad_iterator.speeches() {
        println!("{}", timestamp);
    }
    println!("Finished.");
}
