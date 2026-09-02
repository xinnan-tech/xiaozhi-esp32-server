using NAudio.Wave;
using VADdotnet;

namespace VadDotNet;

public class SileroVadDetector
{
    private readonly SileroVadOnnxModel _model;
    private readonly float _threshold;
    private readonly float _negThreshold;
    private readonly int _samplingRate;
    private readonly int _windowSizeSample;
    private readonly float _minSpeechSamples;
    private readonly float _speechPadSamples;
    private readonly float _maxSpeechSamples;
    private readonly float _minSilenceSamples;
    private readonly float _minSilenceSamplesAtMaxSpeech;
    private int _audioLengthSamples;
    private const float THRESHOLD_GAP = 0.15f;
    // ReSharper disable once InconsistentNaming
    private const int SAMPLING_RATE_8K = 8000;
    // ReSharper disable once InconsistentNaming
    private const int SAMPLING_RATE_16K = 16000;

    public SileroVadDetector(string onnxModelPath, float threshold, int samplingRate,
        int minSpeechDurationMs, float maxSpeechDurationSeconds,
        int minSilenceDurationMs, int speechPadMs)
    {
        if (samplingRate != SAMPLING_RATE_8K && samplingRate != SAMPLING_RATE_16K)
        {
            throw new ArgumentException("Sampling rate not support, only available for [8000, 16000]");
        }

        this._model = new SileroVadOnnxModel(onnxModelPath);
        this._samplingRate = samplingRate;
        this._threshold = threshold;
        this._negThreshold = threshold - THRESHOLD_GAP;
        this._windowSizeSample = samplingRate == SAMPLING_RATE_16K ? 512 : 256;
        this._minSpeechSamples = samplingRate * minSpeechDurationMs / 1000f;
        this._speechPadSamples = samplingRate * speechPadMs / 1000f;
        this._maxSpeechSamples = samplingRate * maxSpeechDurationSeconds - _windowSizeSample - 2 * _speechPadSamples;
        this._minSilenceSamples = samplingRate * minSilenceDurationMs / 1000f;
        this._minSilenceSamplesAtMaxSpeech = samplingRate * 98 / 1000f;
        this.Reset();
    }

    public void Reset()
    {
        _model.ResetStates();
    }

    public List<SileroSpeechSegment> GetSpeechSegmentList(FileInfo wavFile)
    {
        Reset();

        using var audioFile = new AudioFileReader(wavFile.FullName);
        List<float> speechProbList = [];
        this._audioLengthSamples = (int)(audioFile.Length / 2);
        float[] buffer = new float[this._windowSizeSample];

        while (audioFile.Read(buffer, 0, buffer.Length) > 0)
        {
            float speechProb = _model.Call([buffer], _samplingRate)[0];
            speechProbList.Add(speechProb);
        }

        return CalculateProb(speechProbList);
    }

    private List<SileroSpeechSegment> CalculateProb(List<float> speechProbList)
    {
        List<SileroSpeechSegment> result = [];
        bool triggered = false;
        int tempEnd = 0, prevEnd = 0, nextStart = 0;
        SileroSpeechSegment segment = new();

        for (int i = 0; i < speechProbList.Count; i++)
        {
            float speechProb = speechProbList[i];
            if (speechProb >= _threshold && (tempEnd != 0))
            {
                tempEnd = 0;
                if (nextStart < prevEnd)
                {
                    nextStart = _windowSizeSample * i;
                }
            }

            if (speechProb >= _threshold && !triggered)
            {
                triggered = true;
                segment.StartOffset = _windowSizeSample * i;
                continue;
            }

            if (triggered && (_windowSizeSample * i) - segment.StartOffset > _maxSpeechSamples)
            {
                if (prevEnd != 0)
                {
                    segment.EndOffset = prevEnd;
                    result.Add(segment);
                    segment = new SileroSpeechSegment();
                    if (nextStart < prevEnd)
                    {
                        triggered = false;
                    }
                    else
                    {
                        segment.StartOffset = nextStart;
                    }

                    prevEnd = 0;
                    nextStart = 0;
                    tempEnd = 0;
                }
                else
                {
                    segment.EndOffset = _windowSizeSample * i;
                    result.Add(segment);
                    segment = new SileroSpeechSegment();
                    prevEnd = 0;
                    nextStart = 0;
                    tempEnd = 0;
                    triggered = false;
                    continue;
                }
            }

            if (speechProb < _negThreshold && triggered)
            {
                if (tempEnd == 0)
                {
                    tempEnd = _windowSizeSample * i;
                }

                if (((_windowSizeSample * i) - tempEnd) > _minSilenceSamplesAtMaxSpeech)
                {
                    prevEnd = tempEnd;
                }

                if ((_windowSizeSample * i) - tempEnd < _minSilenceSamples)
                {
                    continue;
                }
                else
                {
                    segment.EndOffset = tempEnd;
                    if ((segment.EndOffset - segment.StartOffset) > _minSpeechSamples)
                    {
                        result.Add(segment);
                    }

                    segment = new SileroSpeechSegment();
                    prevEnd = 0;
                    nextStart = 0;
                    tempEnd = 0;
                    triggered = false;
                    continue;
                }
            }
        }

        if (segment.StartOffset != null && (_audioLengthSamples - segment.StartOffset) > _minSpeechSamples)
        {
            //segment.EndOffset = _audioLengthSamples;
            segment.EndOffset = speechProbList.Count * _windowSizeSample;
            result.Add(segment);
        }

        for (int i = 0; i < result.Count; i++)
        {
            SileroSpeechSegment item = result[i];
            if (i == 0)
            {
                item.StartOffset = (int)Math.Max(0, item.StartOffset.Value - _speechPadSamples);
            }

            if (i != result.Count - 1)
            {
                SileroSpeechSegment nextItem = result[i + 1];
                int silenceDuration = nextItem.StartOffset.Value - item.EndOffset.Value;
                if (silenceDuration < 2 * _speechPadSamples)
                {
                    item.EndOffset += (silenceDuration / 2);
                    nextItem.StartOffset = Math.Max(0, nextItem.StartOffset.Value - (silenceDuration / 2));
                }
                else
                {
                    item.EndOffset = (int)Math.Min(_audioLengthSamples, item.EndOffset.Value + _speechPadSamples);
                    nextItem.StartOffset = (int)Math.Max(0, nextItem.StartOffset.Value - _speechPadSamples);
                }
            }
            else
            {
                item.EndOffset = (int)Math.Min(_audioLengthSamples, item.EndOffset.Value + _speechPadSamples);
            }
        }

        return MergeListAndCalculateSecond(result, _samplingRate);
    }

    private static List<SileroSpeechSegment> MergeListAndCalculateSecond(List<SileroSpeechSegment> original, int samplingRate)
    {
        List<SileroSpeechSegment> result = [];
        if (original == null || original.Count == 0)
        {
            return result;
        }

        int left = original[0].StartOffset.Value;
        int right = original[0].EndOffset.Value;
        if (original.Count > 1)
        {
            original.Sort((a, b) => a.StartOffset.Value.CompareTo(b.StartOffset.Value));
            for (int i = 1; i < original.Count; i++)
            {
                SileroSpeechSegment segment = original[i];
    
                if (segment.StartOffset > right)
                {
                    result.Add(new SileroSpeechSegment(left, right,
                        CalculateSecondByOffset(left, samplingRate), CalculateSecondByOffset(right, samplingRate)));
                    left = segment.StartOffset.Value;
                    right = segment.EndOffset.Value;
                }
                else
                {
                    right = Math.Max(right, segment.EndOffset.Value);
                }
            }

            result.Add(new SileroSpeechSegment(left, right,
                CalculateSecondByOffset(left, samplingRate), CalculateSecondByOffset(right, samplingRate)));
        }
        else
        {
            result.Add(new SileroSpeechSegment(left, right,
                CalculateSecondByOffset(left, samplingRate), CalculateSecondByOffset(right, samplingRate)));
        }

        return result;
    }

    private static float CalculateSecondByOffset(int offset, int samplingRate)
    {
        float secondValue = offset * 1.0f / samplingRate;
        return (float)Math.Floor(secondValue * 1000.0f) / 1000.0f;
    }
}