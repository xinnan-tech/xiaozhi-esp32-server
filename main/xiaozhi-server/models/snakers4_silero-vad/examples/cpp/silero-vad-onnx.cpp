#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS
#endif

#include <iostream>
#include <vector>
#include <sstream>
#include <cstring>
#include <limits>
#include <chrono>
#include <iomanip>
#include <memory>
#include <string>
#include <stdexcept>
#include <cstdio>
#include <cstdarg>
#include <cmath>    // for std::rint
#if __cplusplus < 201703L
#include <memory>
#endif

//#define __DEBUG_SPEECH_PROB___

#include "onnxruntime_cxx_api.h"
#include "wav.h" // For reading WAV files

// timestamp_t class: stores the start and end (in samples) of a speech segment.
class timestamp_t {
public:
    int start;
    int end;

    timestamp_t(int start = -1, int end = -1)
        : start(start), end(end) { }

    timestamp_t& operator=(const timestamp_t& a) {
        start = a.start;
        end = a.end;
        return *this;
    }

    bool operator==(const timestamp_t& a) const {
        return (start == a.start && end == a.end);
    }

    // Returns a formatted string of the timestamp.
    std::string c_str() const {
        return format("{start:%08d, end:%08d}", start, end);
    }
private:
    // Helper function for formatting.
    std::string format(const char* fmt, ...) const {
        char buf[256];
        va_list args;
        va_start(args, fmt);
        const auto r = std::vsnprintf(buf, sizeof(buf), fmt, args);
        va_end(args);
        if (r < 0)
            return {};
        const size_t len = r;
        if (len < sizeof(buf))
            return std::string(buf, len);
#if __cplusplus >= 201703L
        std::string s(len, '\0');
        va_start(args, fmt);
        std::vsnprintf(s.data(), len + 1, fmt, args);
        va_end(args);
        return s;
#else
        auto vbuf = std::unique_ptr<char[]>(new char[len + 1]);
        va_start(args, fmt);
        std::vsnprintf(vbuf.get(), len + 1, fmt, args);
        va_end(args);
        return std::string(vbuf.get(), len);
#endif
    }
};

// VadIterator class: uses ONNX Runtime to detect speech segments.
class VadIterator {
private:
    // ONNX Runtime resources
    Ort::Env env;
    Ort::SessionOptions session_options;
    std::shared_ptr<Ort::Session> session = nullptr;
    Ort::AllocatorWithDefaultOptions allocator;
    Ort::MemoryInfo memory_info = Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeCPU);

    // ----- Context-related additions -----
    const int context_samples = 64;  // For 16kHz, 64 samples are added as context.
    std::vector<float> _context;     // Holds the last 64 samples from the previous chunk (initialized to zero).

    // Original window size (e.g., 32ms corresponds to 512 samples)
    int window_size_samples;
    // Effective window size = window_size_samples + context_samples
    int effective_window_size;

    // Additional declaration: samples per millisecond
    int sr_per_ms;

    // ONNX Runtime input/output buffers
    std::vector<Ort::Value> ort_inputs;
    std::vector<const char*> input_node_names = { "input", "state", "sr" };
    std::vector<float> input;
    unsigned int size_state = 2 * 1 * 128;
    std::vector<float> _state;
    std::vector<int64_t> sr;
    int64_t input_node_dims[2] = {};
    const int64_t state_node_dims[3] = { 2, 1, 128 };
    const int64_t sr_node_dims[1] = { 1 };
    std::vector<Ort::Value> ort_outputs;
    std::vector<const char*> output_node_names = { "output", "stateN" };

    // Model configuration parameters
    int sample_rate;
    float threshold;
    int min_silence_samples;
    int min_silence_samples_at_max_speech;
    int min_speech_samples;
    float max_speech_samples;
    int speech_pad_samples;
    int audio_length_samples;

    // State management
    bool triggered = false;
    unsigned int temp_end = 0;
    unsigned int current_sample = 0;
    int prev_end;
    int next_start = 0;
    std::vector<timestamp_t> speeches;
    timestamp_t current_speech;

    // Loads the ONNX model.
    void init_onnx_model(const std::wstring& model_path) {
        init_engine_threads(1, 1);
        session = std::make_shared<Ort::Session>(env, model_path.c_str(), session_options);
    }

    // Initializes threading settings.
    void init_engine_threads(int inter_threads, int intra_threads) {
        session_options.SetIntraOpNumThreads(intra_threads);
        session_options.SetInterOpNumThreads(inter_threads);
        session_options.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);
    }

    // Resets internal state (_state, _context, etc.)
    void reset_states() {
        std::memset(_state.data(), 0, _state.size() * sizeof(float));
        triggered = false;
        temp_end = 0;
        current_sample = 0;
        prev_end = next_start = 0;
        speeches.clear();
        current_speech = timestamp_t();
        std::fill(_context.begin(), _context.end(), 0.0f);
    }

    // Inference: runs inference on one chunk of input data.
    // data_chunk is expected to have window_size_samples samples.
    void predict(const std::vector<float>& data_chunk) {
        // Build new input: first context_samples from _context, followed by the current chunk (window_size_samples).
        std::vector<float> new_data(effective_window_size, 0.0f);
        std::copy(_context.begin(), _context.end(), new_data.begin());
        std::copy(data_chunk.begin(), data_chunk.end(), new_data.begin() + context_samples);
        input = new_data;

        // Create input tensor (input_node_dims[1] is already set to effective_window_size).
        Ort::Value input_ort = Ort::Value::CreateTensor<float>(
            memory_info, input.data(), input.size(), input_node_dims, 2);
        Ort::Value state_ort = Ort::Value::CreateTensor<float>(
            memory_info, _state.data(), _state.size(), state_node_dims, 3);
        Ort::Value sr_ort = Ort::Value::CreateTensor<int64_t>(
            memory_info, sr.data(), sr.size(), sr_node_dims, 1);
        ort_inputs.clear();
        ort_inputs.emplace_back(std::move(input_ort));
        ort_inputs.emplace_back(std::move(state_ort));
        ort_inputs.emplace_back(std::move(sr_ort));

        // Run inference.
        ort_outputs = session->Run(
            Ort::RunOptions{ nullptr },
            input_node_names.data(), ort_inputs.data(), ort_inputs.size(),
            output_node_names.data(), output_node_names.size());

        float speech_prob = ort_outputs[0].GetTensorMutableData<float>()[0];
        float* stateN = ort_outputs[1].GetTensorMutableData<float>();
        std::memcpy(_state.data(), stateN, size_state * sizeof(float));
        current_sample += static_cast<unsigned int>(window_size_samples); // Advance by the original window size.

        // If speech is detected (probability >= threshold)
        if (speech_prob >= threshold) {
#ifdef __DEBUG_SPEECH_PROB___
            float speech = current_sample - window_size_samples;
            printf("{ start: %.3f s (%.3f) %08d}\n", 1.0f * speech / sample_rate, speech_prob, current_sample - window_size_samples);
#endif
            if (temp_end != 0) {
                temp_end = 0;
                if (next_start < prev_end)
                    next_start = current_sample - window_size_samples;
            }
            if (!triggered) {
                triggered = true;
                current_speech.start = current_sample - window_size_samples;
            }
            // Update context: copy the last context_samples from new_data.
            std::copy(new_data.end() - context_samples, new_data.end(), _context.begin());
            return;
        }

        // If the speech segment becomes too long.
        if (triggered && ((current_sample - current_speech.start) > max_speech_samples)) {
            if (prev_end > 0) {
                current_speech.end = prev_end;
                speeches.push_back(current_speech);
                current_speech = timestamp_t();
                if (next_start < prev_end)
                    triggered = false;
                else
                    current_speech.start = next_start;
                prev_end = 0;
                next_start = 0;
                temp_end = 0;
            }
            else {
                current_speech.end = current_sample;
                speeches.push_back(current_speech);
                current_speech = timestamp_t();
                prev_end = 0;
                next_start = 0;
                temp_end = 0;
                triggered = false;
            }
            std::copy(new_data.end() - context_samples, new_data.end(), _context.begin());
            return;
        }

        if ((speech_prob >= (threshold - 0.15)) && (speech_prob < threshold)) {
            // When the speech probability temporarily drops but is still in speech, update context without changing state.
            std::copy(new_data.end() - context_samples, new_data.end(), _context.begin());
            return;
        }

        if (speech_prob < (threshold - 0.15)) {
#ifdef __DEBUG_SPEECH_PROB___
            float speech = current_sample - window_size_samples - speech_pad_samples;
            printf("{ end: %.3f s (%.3f) %08d}\n", 1.0f * speech / sample_rate, speech_prob, current_sample - window_size_samples);
#endif
            if (triggered) {
                if (temp_end == 0)
                    temp_end = current_sample;
                if (current_sample - temp_end > min_silence_samples_at_max_speech)
                    prev_end = temp_end;
                if ((current_sample - temp_end) >= min_silence_samples) {
                    current_speech.end = temp_end;
                    if (current_speech.end - current_speech.start > min_speech_samples) {
                        speeches.push_back(current_speech);
                        current_speech = timestamp_t();
                        prev_end = 0;
                        next_start = 0;
                        temp_end = 0;
                        triggered = false;
                    }
                }
            }
            std::copy(new_data.end() - context_samples, new_data.end(), _context.begin());
            return;
        }
    }

public:
    // Process the entire audio input.
    void process(const std::vector<float>& input_wav) {
        reset_states();
        audio_length_samples = static_cast<int>(input_wav.size());
        // Process audio in chunks of window_size_samples (e.g., 512 samples)
        for (size_t j = 0; j < static_cast<size_t>(audio_length_samples); j += static_cast<size_t>(window_size_samples)) {
            if (j + static_cast<size_t>(window_size_samples) > static_cast<size_t>(audio_length_samples))
                break;
            std::vector<float> chunk(&input_wav[j], &input_wav[j] + window_size_samples);
            predict(chunk);
        }
        if (current_speech.start >= 0) {
            current_speech.end = audio_length_samples;
            speeches.push_back(current_speech);
            current_speech = timestamp_t();
            prev_end = 0;
            next_start = 0;
            temp_end = 0;
            triggered = false;
        }
    }

    // Returns the detected speech timestamps.
    const std::vector<timestamp_t> get_speech_timestamps() const {
        return speeches;
    }

    // Public method to reset the internal state.
    void reset() {
        reset_states();
    }

public:
    // Constructor: sets model path, sample rate, window size (ms), and other parameters.
    // The parameters are set to match the Python version.
    VadIterator(const std::wstring ModelPath,
        int Sample_rate = 16000, int windows_frame_size = 32,
        float Threshold = 0.5, int min_silence_duration_ms = 100,
        int speech_pad_ms = 30, int min_speech_duration_ms = 250,
        float max_speech_duration_s = std::numeric_limits<float>::infinity())
        : sample_rate(Sample_rate), threshold(Threshold), speech_pad_samples(speech_pad_ms), prev_end(0)
    {
        sr_per_ms = sample_rate / 1000;  // e.g., 16000 / 1000 = 16
        window_size_samples = windows_frame_size * sr_per_ms; // e.g., 32ms * 16 = 512 samples
        effective_window_size = window_size_samples + context_samples; // e.g., 512 + 64 = 576 samples
        input_node_dims[0] = 1;
        input_node_dims[1] = effective_window_size;
        _state.resize(size_state);
        sr.resize(1);
        sr[0] = sample_rate;
        _context.assign(context_samples, 0.0f);
        min_speech_samples = sr_per_ms * min_speech_duration_ms;
        max_speech_samples = (sample_rate * max_speech_duration_s - window_size_samples - 2 * speech_pad_samples);
        min_silence_samples = sr_per_ms * min_silence_duration_ms;
        min_silence_samples_at_max_speech = sr_per_ms * 98;
        init_onnx_model(ModelPath);
    }
};

int main() {
    // Read the WAV file (expects 16000 Hz, mono, PCM).
    wav::WavReader wav_reader("audio/recorder.wav"); // File located in the "audio" folder.
    int numSamples = wav_reader.num_samples();
    std::vector<float> input_wav(static_cast<size_t>(numSamples));
    for (size_t i = 0; i < static_cast<size_t>(numSamples); i++) {
        input_wav[i] = static_cast<float>(*(wav_reader.data() + i));
    }

    // Set the ONNX model path (file located in the "model" folder).
    std::wstring model_path = L"model/silero_vad.onnx";

    // Initialize the VadIterator.
    VadIterator vad(model_path);

    // Process the audio.
    vad.process(input_wav);

    // Retrieve the speech timestamps (in samples).
    std::vector<timestamp_t> stamps = vad.get_speech_timestamps();

    // Convert timestamps to seconds and round to one decimal place (for 16000 Hz).
    const float sample_rate_float = 16000.0f;
    for (size_t i = 0; i < stamps.size(); i++) {
        float start_sec = std::rint((stamps[i].start / sample_rate_float) * 10.0f) / 10.0f;
        float end_sec = std::rint((stamps[i].end / sample_rate_float) * 10.0f) / 10.0f;
        std::cout << "Speech detected from "
            << std::fixed << std::setprecision(1) << start_sec
            << " s to "
            << std::fixed << std::setprecision(1) << end_sec
            << " s" << std::endl;
    }

    // Optionally, reset the internal state.
    vad.reset();

    return 0;
}
