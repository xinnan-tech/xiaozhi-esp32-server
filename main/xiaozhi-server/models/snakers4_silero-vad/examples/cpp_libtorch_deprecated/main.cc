#include <iostream>
#include "silero_torch.h"
#include "wav.h"

int main(int argc, char* argv[]) {

	if(argc != 4){
		std::cerr<<"Usage : "<<argv[0]<<" <wav.path> <SampleRate> <Threshold>"<<std::endl;
		std::cerr<<"Usage : "<<argv[0]<<" sample.wav 16000 0.5"<<std::endl;
		return 1;
	}

	std::string wav_path = argv[1];
	float sample_rate = std::stof(argv[2]);
	float threshold = std::stof(argv[3]);


	//Load Model
	std::string model_path = "../../src/silero_vad/data/silero_vad.jit";
	silero::VadIterator vad(model_path);

        vad.threshold=threshold;	//(Default:0.5)
	vad.sample_rate=sample_rate;	//16000Hz,8000Hz. (Default:16000)
        vad.print_as_samples=true;	//if true, it prints time-stamp with samples. otherwise, in seconds
					//(Default:false)

	vad.SetVariables();

	// Read wav
	wav::WavReader wav_reader(wav_path); 
	std::vector<float> input_wav(wav_reader.num_samples());

	for (int i = 0; i < wav_reader.num_samples(); i++)
	{
		input_wav[i] = static_cast<float>(*(wav_reader.data() + i));
	}

	vad.SpeechProbs(input_wav);

	std::vector<silero::SpeechSegment> speeches = vad.GetSpeechTimestamps();
	for(const auto& speech : speeches){
		if(vad.print_as_samples){
			std::cout<<"{'start': "<<static_cast<int>(speech.start)<<", 'end': "<<static_cast<int>(speech.end)<<"}"<<std::endl;
		}
		else{
			std::cout<<"{'start': "<<speech.start<<", 'end': "<<speech.end<<"}"<<std::endl;
		}
	}	


	return 0;
	}


