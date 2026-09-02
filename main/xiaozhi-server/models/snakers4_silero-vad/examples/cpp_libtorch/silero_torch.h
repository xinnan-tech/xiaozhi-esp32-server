//Author      : Nathan Lee
//Created On  : 2024-11-18
//Description : silero 5.1 system for torch-script(c++).
//Version     : 1.0

#ifndef SILERO_TORCH_H
#define SILERO_TORCH_H

#include <string>
#include <memory>
#include <stdexcept>
#include <iostream>
#include <memory>
#include <vector>
#include <fstream>
#include <chrono>

#include <torch/torch.h>
#include <torch/script.h>


namespace silero{

	struct SpeechSegment{
		int start;
		int end;
	};

	class VadIterator{
		public:

			VadIterator(const std::string &model_path, float threshold = 0.5, int sample_rate = 16000, 
				int window_size_ms = 32, int speech_pad_ms = 30, int min_silence_duration_ms = 100, 
				int min_speech_duration_ms = 250, int max_duration_merge_ms = 300, bool print_as_samples = false);
			~VadIterator(); 


			void SpeechProbs(std::vector<float>& input_wav);
			std::vector<silero::SpeechSegment> GetSpeechTimestamps();
			void SetVariables();

			float threshold;
			int sample_rate;
			int window_size_ms;
			int min_speech_duration_ms;
			int max_duration_merge_ms;
			bool print_as_samples;

		private:
			torch::jit::script::Module model;
			std::vector<float> outputs_prob;
			int min_silence_samples;
			int min_speech_samples;
			int speech_pad_samples;
			int window_size_samples;
			int duration_merge_samples;
			int current_sample = 0;

			int total_sample_size=0;

			int min_silence_duration_ms;
			int speech_pad_ms;
			bool triggered = false;
			int temp_end = 0;

			void init_engine(int window_size_ms);
			void init_torch_model(const std::string& model_path);
			void reset_states();
			std::vector<SpeechSegment> DoVad();
			std::vector<SpeechSegment> mergeSpeeches(const std::vector<SpeechSegment>& speeches, int duration_merge_samples);

	};

}
#endif // SILERO_TORCH_H
