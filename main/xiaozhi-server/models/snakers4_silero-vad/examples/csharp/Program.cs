using System.Text;

namespace VadDotNet;


class Program
{
    private const string MODEL_PATH = "./resources/silero_vad.onnx";
    private const string EXAMPLE_WAV_FILE = "./resources/example.wav";
    private const int SAMPLE_RATE = 16000;
    private const float THRESHOLD = 0.5f;
    private const int MIN_SPEECH_DURATION_MS = 250;
    private const float MAX_SPEECH_DURATION_SECONDS = float.PositiveInfinity;
    private const int MIN_SILENCE_DURATION_MS = 100;
    private const int SPEECH_PAD_MS = 30;

    public static void Main(string[] args)
    {
        
            var vadDetector = new SileroVadDetector(MODEL_PATH, THRESHOLD, SAMPLE_RATE,
                MIN_SPEECH_DURATION_MS, MAX_SPEECH_DURATION_SECONDS, MIN_SILENCE_DURATION_MS, SPEECH_PAD_MS);
            List<SileroSpeechSegment> speechTimeList = vadDetector.GetSpeechSegmentList(new FileInfo(EXAMPLE_WAV_FILE));
            //Console.WriteLine(speechTimeList.ToJson());
            StringBuilder sb = new();
            foreach (var speechSegment in speechTimeList)
            {
                sb.Append($"start second: {speechSegment.StartSecond}, end second: {speechSegment.EndSecond}\n");
                
            }
            Console.WriteLine(sb.ToString());
       
    }
    
    
}
