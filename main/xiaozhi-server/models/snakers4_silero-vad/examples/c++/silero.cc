// silero.cc
// Author      : NathanJHLee
// Created On  : 2025-11-10
// Description : silero 6.2 system for onnx-runtime(c++) and torch-script(c++)
// Version     : 1.3

#include "silero.h"


namespace silero {

#ifdef USE_TORCH
	VadIterator::VadIterator(const std::string &model_path,
			float threshold,
			int sample_rate,
			int window_size_ms,
			int speech_pad_ms,
			int min_silence_duration_ms,
			int min_speech_duration_ms,
			int max_duration_merge_ms,
			bool print_as_samples)
		: threshold(threshold), sample_rate(sample_rate), window_size_ms(window_size_ms),
		speech_pad_ms(speech_pad_ms), min_silence_duration_ms(min_silence_duration_ms),
		min_speech_duration_ms(min_speech_duration_ms), max_duration_merge_ms(max_duration_merge_ms),
		print_as_samples(print_as_samples)
	{
		init_torch_model(model_path);
	}

	VadIterator::~VadIterator(){
	}


	void VadIterator::init_torch_model(const std::string& model_path) {
		at::set_num_threads(1);
		model = torch::jit::load(model_path);

		model.eval();
		torch::NoGradGuard no_grad;
		std::cout<<"Silero libtorch-Model loaded successfully"<<std::endl;
	}

	void VadIterator::SpeechProbs(std::vector<float>& input_wav) {
		int num_samples = input_wav.size();
		int num_chunks = num_samples / window_size_samples;
		int remainder_samples = num_samples % window_size_samples;
		total_sample_size += num_samples;

		std::vector<torch::Tensor> chunks;

		for (int i = 0; i < num_chunks; i++) {
			float* chunk_start = input_wav.data() + i * window_size_samples;
			torch::Tensor chunk = torch::from_blob(chunk_start, {1, window_size_samples}, torch::kFloat32);
			chunks.push_back(chunk);

			if (i == num_chunks - 1 && remainder_samples > 0) {
				int remaining_samples = num_samples - num_chunks * window_size_samples;
				float* chunk_start_remainder = input_wav.data() + num_chunks * window_size_samples;
				torch::Tensor remainder_chunk = torch::from_blob(chunk_start_remainder, {1, remaining_samples}, torch::kFloat32);
				torch::Tensor padded_chunk = torch::cat({remainder_chunk, torch::zeros({1, window_size_samples - remaining_samples}, torch::kFloat32)}, 1);
				chunks.push_back(padded_chunk);
			}
		}

		if (!chunks.empty()) {
			std::vector<torch::Tensor> outputs;
			torch::Tensor batched_chunks = torch::stack(chunks);
			for (size_t i = 0; i < chunks.size(); i++) {
				torch::NoGradGuard no_grad;
				std::vector<torch::jit::IValue> inputs;
				inputs.push_back(batched_chunks[i]);
				inputs.push_back(sample_rate);
				torch::Tensor output = model.forward(inputs).toTensor();
				outputs.push_back(output);
			}
			torch::Tensor all_outputs = torch::stack(outputs);
			for (size_t i = 0; i < chunks.size(); i++) {
				float output_f = all_outputs[i].item<float>();
				outputs_prob.push_back(output_f);
				//////To print Probs by libtorch
				//std::cout << "Chunk " << i << " prob: " << output_f<< "\n";
			}
		}
	}


#elif USE_ONNX

        VadIterator::VadIterator(const std::string &model_path, 
			float threshold, 
			int sample_rate, 
			int window_size_ms, 
			int speech_pad_ms, 
			int min_silence_duration_ms, 
			int min_speech_duration_ms, 
			int max_duration_merge_ms, 
			bool print_as_samples)
                :sample_rate(sample_rate), threshold(threshold), window_size_ms(window_size_ms), 
		speech_pad_ms(speech_pad_ms), min_silence_duration_ms(min_silence_duration_ms), 
		min_speech_duration_ms(min_speech_duration_ms), max_duration_merge_ms(max_duration_merge_ms), 
		print_as_samples(print_as_samples),
                env(ORT_LOGGING_LEVEL_ERROR, "Vad"), session_options(), session(nullptr), allocator(), 
		memory_info(Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeCPU)), context_samples(64), 
		_context(64, 0.0f), current_sample(0), size_state(2 * 1 * 128), 
		input_node_names({"input", "state", "sr"}), output_node_names({"output", "stateN"}), 
		state_node_dims{2, 1, 128}, sr_node_dims{1}

        {
                init_onnx_model(model_path);
        }
        VadIterator::~VadIterator(){
        }

        void VadIterator::init_onnx_model(const std::string& model_path) {
                int inter_threads=1;
                int intra_threads=1;
                session_options.SetIntraOpNumThreads(intra_threads);
                session_options.SetInterOpNumThreads(inter_threads);
                session_options.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);
                session = std::make_shared<Ort::Session>(env, model_path.c_str(), session_options);
		std::cout<<"Silero onnx-Model loaded successfully"<<std::endl;
        }

        float VadIterator::predict(const std::vector<float>& data_chunk) {
                // _context와 현재 청크를 결합하여 입력 데이터 구성
                std::vector<float> new_data(effective_window_size, 0.0f);
                std::copy(_context.begin(), _context.end(), new_data.begin());
                std::copy(data_chunk.begin(), data_chunk.end(), new_data.begin() + context_samples);
                input = new_data;

		Ort::Value input_ort = Ort::Value::CreateTensor<float>(
                                memory_info, input.data(), input.size(), input_node_dims, 2);
                Ort::Value state_ort = Ort::Value::CreateTensor<float>(
                                memory_info, _state.data(), _state.size(), state_node_dims, 3);
                Ort::Value sr_ort = Ort::Value::CreateTensor<int64_t>(
                                memory_info, sr.data(), sr.size(), sr_node_dims, 1);
                ort_inputs.clear();
                ort_inputs.push_back(std::move(input_ort));
                ort_inputs.push_back(std::move(state_ort));
                ort_inputs.push_back(std::move(sr_ort));

                ort_outputs = session->Run(
                                Ort::RunOptions{ nullptr },
                                input_node_names.data(), ort_inputs.data(), ort_inputs.size(),
                                output_node_names.data(), output_node_names.size());

                float speech_prob = ort_outputs[0].GetTensorMutableData<float>()[0]; // ONNX 출력: 첫 번째 값이 음성 확률

                float* stateN = ort_outputs[1].GetTensorMutableData<float>(); // 두 번째 출력값: 상태 업데이트
                std::memcpy(_state.data(), stateN, size_state * sizeof(float));

                std::copy(new_data.end() - context_samples, new_data.end(), _context.begin());
                // _context 업데이트: new_data의 마지막 context_samples 유지

                return speech_prob;
        }
        void VadIterator::SpeechProbs(std::vector<float>& input_wav) {
                reset_states();
                total_sample_size = static_cast<int>(input_wav.size());
                for (size_t j = 0; j < static_cast<size_t>(total_sample_size); j += window_size_samples) {
                        if (j + window_size_samples > static_cast<size_t>(total_sample_size))
                                break;
                        std::vector<float> chunk(input_wav.begin() + j, input_wav.begin() + j + window_size_samples);
                        float speech_prob = predict(chunk);
                        outputs_prob.push_back(speech_prob);
                }
        }

#endif

        void VadIterator::reset_states() {
                triggered = false;
                current_sample = 0;
                temp_end = 0;
                outputs_prob.clear();
                total_sample_size = 0;

#ifdef USE_TORCH
                model.run_method("reset_states"); // Reset model states if applicable
#elif USE_ONNX
                std::memset(_state.data(), 0, _state.size() * sizeof(float));
                std::fill(_context.begin(), _context.end(), 0.0f);
#endif
	}

        std::vector<Interval> VadIterator::GetSpeechTimestamps() {
                std::vector<Interval> speeches = DoVad();
                if(!print_as_samples){
                        for (auto& speech : speeches) {
                                speech.start /= sample_rate;
                                speech.end   /= sample_rate;
                        }
                }
                return speeches;
        }

        void VadIterator::SetVariables(){
                // Initialize internal engine parameters
                init_engine(window_size_ms);
        }

        void VadIterator::init_engine(int window_size_ms) {
                min_silence_samples = sample_rate * min_silence_duration_ms / 1000;
                speech_pad_samples = sample_rate * speech_pad_ms / 1000;
                window_size_samples = sample_rate / 1000 * window_size_ms;
                min_speech_samples = sample_rate * min_speech_duration_ms / 1000;
#ifdef USE_ONNX
                //for ONNX
                context_samples=window_size_samples / 8;
		_context.assign(context_samples, 0.0f);

                effective_window_size = window_size_samples + context_samples;  // 예: 512 + 64 = 576 samples
                input_node_dims[0] = 1;
                input_node_dims[1] = effective_window_size;
                _state.resize(size_state);
                sr.resize(1);
                sr[0] = sample_rate;
#endif
	}

	std::vector<Interval> VadIterator::DoVad() {
		std::vector<Interval> speeches;
		for (size_t i = 0; i < outputs_prob.size(); ++i) {
			float speech_prob = outputs_prob[i];
			current_sample += window_size_samples;
			if (speech_prob >= threshold && temp_end != 0) {
				temp_end = 0;
			}

			if (speech_prob >= threshold) {
				if (!triggered) {
					triggered = true;
					Interval segment;
					segment.start = std::max(0, current_sample - speech_pad_samples - window_size_samples);
					speeches.push_back(segment);
				}
			}else {
				if (triggered) {
					if (speech_prob < threshold - 0.15f) {
						if (temp_end == 0) {
							temp_end = current_sample;
						}
						if (current_sample - temp_end >= min_silence_samples) {
							Interval& segment = speeches.back();
							segment.end = temp_end + speech_pad_samples - window_size_samples;
							temp_end = 0;
							triggered = false;
						}
					}
				}
			}


		}

		if (triggered) {
			std::cout<<"Finalizing active speech segment at stream end."<<std::endl;
			Interval& segment = speeches.back();
			segment.end = total_sample_size;
			triggered = false;
		}
		speeches.erase(std::remove_if(speeches.begin(), speeches.end(),
					[this](const Interval& speech) {
					return ((speech.end - this->speech_pad_samples) - (speech.start + this->speech_pad_samples) < min_speech_samples);
					}), speeches.end());

		reset_states();
		return speeches;
	}


	} // namespace silero

