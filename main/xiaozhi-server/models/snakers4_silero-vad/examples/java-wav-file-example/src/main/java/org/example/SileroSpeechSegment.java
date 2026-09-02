package org.example;


public class SileroSpeechSegment {
    private Integer startOffset;
    private Integer endOffset;
    private Float startSecond;
    private Float endSecond;

    public SileroSpeechSegment() {
    }

    public SileroSpeechSegment(Integer startOffset, Integer endOffset, Float startSecond, Float endSecond) {
        this.startOffset = startOffset;
        this.endOffset = endOffset;
        this.startSecond = startSecond;
        this.endSecond = endSecond;
    }

    public Integer getStartOffset() {
        return startOffset;
    }

    public Integer getEndOffset() {
        return endOffset;
    }

    public Float getStartSecond() {
        return startSecond;
    }

    public Float getEndSecond() {
        return endSecond;
    }

    public void setStartOffset(Integer startOffset) {
        this.startOffset = startOffset;
    }

    public void setEndOffset(Integer endOffset) {
        this.endOffset = endOffset;
    }

    public void setStartSecond(Float startSecond) {
        this.startSecond = startSecond;
    }

    public void setEndSecond(Float endSecond) {
        this.endSecond = endSecond;
    }
}
