namespace VadDotNet;

public class SileroSpeechSegment
{
    public int? StartOffset { get; set; }
    public int? EndOffset { get; set; }
    public float? StartSecond { get; set; }
    public float? EndSecond { get; set; }

    public SileroSpeechSegment()
    {
    }

    public SileroSpeechSegment(int startOffset, int? endOffset, float? startSecond, float? endSecond)
    {
        StartOffset = startOffset;
        EndOffset = endOffset;
        StartSecond = startSecond;
        EndSecond = endSecond;
    }
}