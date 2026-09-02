//Author      : Nathan Lee
//Created On  : 2024-11-18
//Description : silero 5.1 system for torch-script(c++).
//Version     : 1.0


#include "silero_torch.h"

namespace silero {

	VadIterator::VadIterator(const std::string &model_path, float threshold, int sample_rate, int window_size_ms, int speech_pad_ms, int min_silence_duration_ms, int min_speech_duration_ms, int max_duration_merge_ms, bool print_as_samples)
		:sample_rate(sample_rate), threshold(threshold), window_size_ms(window_size_ms), speech_pad_ms(speech_pad_ms), min_silence_duration_ms(min_silence_duration_ms), min_speech_duration_ms(min_speech_duration_ms), max_duration_merge_ms(max_duration_merge_ms), print_as_samples(print_as_samples)
	{
		init_torch_model(model_path);
		//init_engine(window_size_ms);
	}
	VadIterator::~VadIterator(){
	}


	void VadIterator::SpeechProbs(std::vector<float>& input_wav){
		// Set the sample rate (must match the model's expected sample rate)
		// Process the waveform in chunks of 512 samples
		int num_samples = input_wav.size();
		int num_chunks = num_samples / window_size_samples;
		int remainder_samples = num_samples % window_size_samples;

		total_sample_size += num_samples;

		torch::Tensor output;
		std::vector<torch::Tensor> chunks;

		for (int i = 0; i < num_chunks; i++) {

			float* chunk_start = input_wav.data() + i *window_size_samples;
			torch::Tensor chunk = torch::from_blob(chunk_start, {1,window_size_samples}, torch::kFloat32);
			//std::cout<<"chunk size : "<<chunk.sizes()<<std::endl;
			chunks.push_back(chunk);


			if(i==num_chunks-1 && remainder_samples>0){//마지막 chunk && 나머지가 존재
				int remaining_samples = num_samples - num_chunks * window_size_samples;
				//std::cout<<"Remainder size : "<<remaining_samples;
				float* chunk_start_remainder = input_wav.data() + num_chunks *window_size_samples;

				torch::Tensor remainder_chunk = torch::from_blob(chunk_start_remainder, {1,remaining_samples},
						torch::kFloat32);
				// Pad the remainder chunk to match window_size_samples
				torch::Tensor padded_chunk = torch::cat({remainder_chunk, torch::zeros({1, window_size_samples
							- remaining_samples}, torch::kFloat32)}, 1);
				//std::cout<<", padded_chunk size : "<<padded_chunk.size(1)<<std::endl;

				chunks.push_back(padded_chunk);
			}
		}

		if (!chunks.empty()) {

#ifdef USE_BATCH
			torch::Tensor batched_chunks = torch::stack(chunks);  // Stack all chunks into a single tensor
			//batched_chunks = batched_chunks.squeeze(1);
			batched_chunks = torch::cat({batched_chunks.squeeze(1)});

#ifdef USE_GPU
			batched_chunks = batched_chunks.to(at::kCUDA);        // Move the entire batch to GPU once
#endif
			// Prepare input for model
			std::vector<torch::jit::IValue> inputs;
			inputs.push_back(batched_chunks);  // Batch of chunks
			inputs.push_back(sample_rate);     // Assuming sample_rate is a valid input for the model

			// Run inference on the batch
			torch::NoGradGuard no_grad;
			torch::Tensor output = model.forward(inputs).toTensor();
#ifdef USE_GPU
			output = output.to(at::kCPU);      // Move the output back to CPU once
#endif
			// Collect output probabilities
			for (int i = 0; i < chunks.size(); i++) {
				float output_f = output[i].item<float>();
				outputs_prob.push_back(output_f);
				//std::cout << "Chunk " << i << " prob: " << output_f<< "\n";
			}
#else

			std::vector<torch::Tensor> outputs;
			torch::Tensor batched_chunks = torch::stack(chunks);
#ifdef USE_GPU
			batched_chunks = batched_chunks.to(at::kCUDA);
#endif
			for (int i = 0; i < chunks.size(); i++) {
				torch::NoGradGuard no_grad;
				std::vector<torch::jit::IValue> inputs;
				inputs.push_back(batched_chunks[i]);
				inputs.push_back(sample_rate);

				torch::Tensor output = model.forward(inputs).toTensor();
				outputs.push_back(output);
			}
			torch::Tensor all_outputs = torch::stack(outputs);
#ifdef USE_GPU
			all_outputs = all_outputs.to(at::kCPU);
#endif
			for (int i = 0; i < chunks.size(); i++) {
				float output_f = all_outputs[i].item<float>();
				outputs_prob.push_back(output_f);
			}



#endif

		}


	}


	std::vector<SpeechSegment> VadIterator::GetSpeechTimestamps() {
		std::vector<SpeechSegment> speeches = DoVad();

#ifdef USE_BATCH
		//When you use BATCH inference. You would better use 'mergeSpeeches' function to arrage time stamp.
		//It could be better get reasonable output because of distorted probs.
		duration_merge_samples = sample_rate * max_duration_merge_ms / 1000;
		std::vector<SpeechSegment> speeches_merge = mergeSpeeches(speeches, duration_merge_samples);
		if(!print_as_samples){
			for (auto& speech : speeches_merge) { //samples to second
				speech.start /= sample_rate;
				speech.end /= sample_rate;
			}
		}

		return speeches_merge;
#else

		if(!print_as_samples){
			for (auto& speech : speeches) { //samples to second
				speech.start /= sample_rate;
				speech.end /= sample_rate;
			}
		}

		return speeches;

#endif

	}
	void VadIterator::SetVariables(){
		init_engine(window_size_ms);
	}

	void VadIterator::init_engine(int window_size_ms) {
		min_silence_samples = sample_rate * min_silence_duration_ms / 1000;
		speech_pad_samples = sample_rate * speech_pad_ms / 1000;
		window_size_samples = sample_rate / 1000 * window_size_ms;
		min_speech_samples = sample_rate * min_speech_duration_ms / 1000;
	}

	void VadIterator::init_torch_model(const std::string& model_path) {
		at::set_num_threads(1);
		model = torch::jit::load(model_path);

#ifdef USE_GPU
		if (!torch::cuda::is_available()) {
			std::cout<<"CUDA is not available! Please check your GPU settings"<<std::endl;
			throw std::runtime_error("CUDA is not available!");
			model.to(at::Device(at::kCPU));    

		} else {
			std::cout<<"CUDA available! Running on '0'th GPU"<<std::endl;
			model.to(at::Device(at::kCUDA, 0));        //select 0'th machine 
		}
#endif


		model.eval();
		torch::NoGradGuard no_grad;
		std::cout << "Model loaded successfully"<<std::endl;
	}

	void VadIterator::reset_states() {
		triggered = false;
		current_sample = 0;
		temp_end = 0;
		outputs_prob.clear();
		model.run_method("reset_states");
		total_sample_size = 0;
	}

	std::vector<SpeechSegment> VadIterator::DoVad() {
		std::vector<SpeechSegment> speeches;

		for (size_t i = 0; i < outputs_prob.size(); ++i) {
			float speech_prob = outputs_prob[i];
			//std::cout << speech_prob << std::endl;
			//std::cout << "Chunk " << i << " Prob: " << speech_prob << "\n";
			//std::cout << speech_prob << " ";
			current_sample += window_size_samples;

			if (speech_prob >= threshold && temp_end != 0) {
				temp_end = 0;
			}

			if (speech_prob >= threshold && !triggered) {
				triggered = true;
				SpeechSegment segment;
				segment.start = std::max(static_cast<int>(0), current_sample - speech_pad_samples - window_size_samples);
				speeches.push_back(segment);
				continue;
			}

			if (speech_prob < threshold - 0.15f && triggered) {
				if (temp_end == 0) {
					temp_end = current_sample;
				}

				if (current_sample - temp_end < min_silence_samples) {
					continue;
				} else {
					SpeechSegment& segment = speeches.back();
					segment.end = temp_end + speech_pad_samples - window_size_samples;
					temp_end = 0;
					triggered = false;
				}
			}
		}

		if (triggered) { //만약 낮은 확률을 보이다가  마지막프레임 prbos만 딱 확률이 높게 나오면 위에서 triggerd = true 메핑과 동시에  segment start가 돼서 문제가 될것 같은데? start = end 같은값? 후처리가 있으니 문제가 없으려나?
			std::cout<<"when last triggered is keep working until last Probs"<<std::endl;
			SpeechSegment& segment = speeches.back();
			segment.end = total_sample_size;  // 현재 샘플을 마지막 구간의 종료 시간으로 설정
			triggered = false;  // VAD 상태 초기화
		}

		speeches.erase(
                		std::remove_if(
                        speeches.begin(),
                        speeches.end(),
                        [this](const SpeechSegment& speech) {
                        return ((speech.end - this->speech_pad_samples) - (speech.start + this->speech_pad_samples) < min_speech_samples);
			//min_speech_samples is 4000samples(0.25sec)
			//여기서 포인트!! 계산 할때는 start,end sample에'speech_pad_samples' 사이즈를 추가한후 길이를 측정함. 
                        }
                ),
                speeches.end()
              );


		//std::cout<<std::endl;
		//std::cout<<"outputs_prob.size : "<<outputs_prob.size()<<std::endl;

		reset_states();
		return speeches;
	}

	std::vector<SpeechSegment> VadIterator::mergeSpeeches(const std::vector<SpeechSegment>& speeches, int duration_merge_samples) {
		std::vector<SpeechSegment> mergedSpeeches;

		if (speeches.empty()) {
			return mergedSpeeches; // 빈 벡터 반환
		}

		// 첫 번째 구간으로 초기화
		SpeechSegment currentSegment = speeches[0];

		for (size_t i = 1; i < speeches.size(); ++i) {	//첫번째 start,end 정보 건너뛰기. 그래서 i=1부터
			// 두 구간의 차이가 threshold(duration_merge_samples)보다 작은 경우, 합침
			if (speeches[i].start - currentSegment.end < duration_merge_samples) {
				// 현재 구간의 끝점을 업데이트
				currentSegment.end = speeches[i].end;
			} else {
				// 차이가 threshold(duration_merge_samples) 이상이면 현재 구간을 저장하고 새로운 구간 시작
				mergedSpeeches.push_back(currentSegment);
				currentSegment = speeches[i];
			}
		}

		// 마지막 구간 추가
		mergedSpeeches.push_back(currentSegment);

		return mergedSpeeches;
	}

	}
