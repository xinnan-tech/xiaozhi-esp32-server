package org.example;


import ai.onnxruntime.OrtException;

import javax.sound.sampled.AudioInputStream;
import javax.sound.sampled.AudioSystem;
import java.io.File;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

public class SileroVadDetector {
    private final SileroVadOnnxModel model;
    private final float threshold;
    private final float negThreshold;
    private final int samplingRate;
    private final int windowSizeSample;
    private final float minSpeechSamples;
    private final float speechPadSamples;
    private final float maxSpeechSamples;
    private final float minSilenceSamples;
    private final float minSilenceSamplesAtMaxSpeech;
    private int audioLengthSamples;
    private static final float THRESHOLD_GAP = 0.15f;
    private static final Integer SAMPLING_RATE_8K = 8000;
    private static final Integer SAMPLING_RATE_16K = 16000;

    /**
     * Constructor
     * @param onnxModelPath the path of silero-vad onnx model
     * @param threshold threshold for speech start
     * @param samplingRate audio sampling rate, only available for [8k, 16k]
     * @param minSpeechDurationMs Minimum speech length in millis, any speech duration that smaller than this value would not be considered as speech
     * @param maxSpeechDurationSeconds Maximum speech length in millis, recommend to be set as Float.POSITIVE_INFINITY
     * @param minSilenceDurationMs Minimum silence length in millis, any silence duration that smaller than this value would not be considered as silence
     * @param speechPadMs Additional pad millis for speech start and end
     * @throws OrtException
     */
    public SileroVadDetector(String onnxModelPath, float threshold, int samplingRate,
                             int minSpeechDurationMs, float maxSpeechDurationSeconds,
                             int minSilenceDurationMs, int speechPadMs) throws OrtException {
        if (samplingRate != SAMPLING_RATE_8K && samplingRate != SAMPLING_RATE_16K) {
            throw new IllegalArgumentException("Sampling rate not support, only available for [8000, 16000]");
        }
        this.model = new SileroVadOnnxModel(onnxModelPath);
        this.samplingRate = samplingRate;
        this.threshold = threshold;
        this.negThreshold = threshold - THRESHOLD_GAP;
        if (samplingRate == SAMPLING_RATE_16K) {
            this.windowSizeSample = 512;
        } else {
            this.windowSizeSample = 256;
        }
        this.minSpeechSamples = samplingRate * minSpeechDurationMs / 1000f;
        this.speechPadSamples = samplingRate * speechPadMs / 1000f;
        this.maxSpeechSamples = samplingRate * maxSpeechDurationSeconds - windowSizeSample - 2 * speechPadSamples;
        this.minSilenceSamples = samplingRate * minSilenceDurationMs / 1000f;
        this.minSilenceSamplesAtMaxSpeech = samplingRate * 98 / 1000f;
        this.reset();
    }

    /**
     * Method to reset the state
     */
    public void reset() {
        model.resetStates();
    }

    /**
     * Get speech segment list by given wav-format file
     * @param wavFile wav file
     * @return list of speech segment
     */
    public List<SileroSpeechSegment> getSpeechSegmentList(File wavFile) {
        reset();
        try (AudioInputStream audioInputStream =  AudioSystem.getAudioInputStream(wavFile)){
            List<Float> speechProbList = new ArrayList<>();
            this.audioLengthSamples = audioInputStream.available() / 2;
            byte[] data = new byte[this.windowSizeSample * 2];
            int numBytesRead = 0;

            while ((numBytesRead = audioInputStream.read(data)) != -1) {
                if (numBytesRead <= 0) {
                    break;
                }
                // Convert the byte array to a float array
                float[] audioData = new float[data.length / 2];
                for (int i = 0; i < audioData.length; i++) {
                    audioData[i] = ((data[i * 2] & 0xff) | (data[i * 2 + 1] << 8)) / 32767.0f;
                }

                float speechProb = 0;
                try {
                    speechProb = model.call(new float[][]{audioData}, samplingRate)[0];
                    speechProbList.add(speechProb);
                } catch (OrtException e) {
                    throw e;
                }
            }
            return calculateProb(speechProbList);
        } catch (Exception e) {
            throw new RuntimeException("SileroVadDetector getSpeechTimeList with error", e);
        }
    }

    /**
     * Calculate speech segement by probability
     * @param speechProbList speech probability list
     * @return list of speech segment
     */
    private List<SileroSpeechSegment> calculateProb(List<Float> speechProbList) {
        List<SileroSpeechSegment> result = new ArrayList<>();
        boolean triggered = false;
        int tempEnd = 0, prevEnd = 0, nextStart = 0;
        SileroSpeechSegment segment = new SileroSpeechSegment();

        for (int i = 0; i < speechProbList.size(); i++) {
            Float speechProb = speechProbList.get(i);
            if (speechProb >= threshold && (tempEnd != 0)) {
                tempEnd = 0;
                if (nextStart < prevEnd) {
                    nextStart = windowSizeSample * i;
                }
            }

            if (speechProb >= threshold && !triggered) {
                triggered = true;
                segment.setStartOffset(windowSizeSample * i);
                continue;
            }

            if (triggered && (windowSizeSample * i) - segment.getStartOffset() > maxSpeechSamples) {
                if (prevEnd != 0) {
                    segment.setEndOffset(prevEnd);
                    result.add(segment);
                    segment = new SileroSpeechSegment();
                    if (nextStart < prevEnd) {
                        triggered = false;
                    }else {
                        segment.setStartOffset(nextStart);
                    }
                    prevEnd = 0;
                    nextStart = 0;
                    tempEnd = 0;
                }else {
                    segment.setEndOffset(windowSizeSample * i);
                    result.add(segment);
                    segment = new SileroSpeechSegment();
                    prevEnd = 0;
                    nextStart = 0;
                    tempEnd = 0;
                    triggered = false;
                    continue;
                }
            }

            if (speechProb < negThreshold && triggered) {
                if (tempEnd == 0) {
                    tempEnd = windowSizeSample * i;
                }
                if (((windowSizeSample * i) - tempEnd) > minSilenceSamplesAtMaxSpeech) {
                    prevEnd = tempEnd;
                }
                if ((windowSizeSample * i) - tempEnd < minSilenceSamples) {
                    continue;
                }else {
                    segment.setEndOffset(tempEnd);
                    if ((segment.getEndOffset() - segment.getStartOffset()) > minSpeechSamples) {
                        result.add(segment);
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

        if (segment.getStartOffset() != null && (audioLengthSamples - segment.getStartOffset()) > minSpeechSamples) {
            segment.setEndOffset(audioLengthSamples);
            result.add(segment);
        }

        for (int i = 0; i < result.size(); i++) {
            SileroSpeechSegment item = result.get(i);
            if (i == 0) {
                item.setStartOffset((int)(Math.max(0,item.getStartOffset() - speechPadSamples)));
            }
            if (i != result.size() - 1) {
                SileroSpeechSegment nextItem = result.get(i + 1);
                Integer silenceDuration = nextItem.getStartOffset() - item.getEndOffset();
                if(silenceDuration < 2 * speechPadSamples){
                    item.setEndOffset(item.getEndOffset() + (silenceDuration / 2 ));
                    nextItem.setStartOffset(Math.max(0, nextItem.getStartOffset() - (silenceDuration / 2)));
                } else {
                    item.setEndOffset((int)(Math.min(audioLengthSamples, item.getEndOffset() + speechPadSamples)));
                    nextItem.setStartOffset((int)(Math.max(0,nextItem.getStartOffset() - speechPadSamples)));
                }
            }else {
                item.setEndOffset((int)(Math.min(audioLengthSamples, item.getEndOffset() + speechPadSamples)));
            }
        }

        return mergeListAndCalculateSecond(result, samplingRate);
    }

    private List<SileroSpeechSegment> mergeListAndCalculateSecond(List<SileroSpeechSegment> original, Integer samplingRate) {
        List<SileroSpeechSegment> result = new ArrayList<>();
        if (original == null || original.size() == 0) {
            return result;
        }
        Integer left = original.get(0).getStartOffset();
        Integer right = original.get(0).getEndOffset();
        if (original.size() > 1) {
            original.sort(Comparator.comparingLong(SileroSpeechSegment::getStartOffset));
            for (int i = 1; i < original.size(); i++) {
                SileroSpeechSegment segment = original.get(i);

                if (segment.getStartOffset() > right) {
                    result.add(new SileroSpeechSegment(left, right,
                            calculateSecondByOffset(left, samplingRate), calculateSecondByOffset(right, samplingRate)));
                    left = segment.getStartOffset();
                    right = segment.getEndOffset();
                } else {
                    right = Math.max(right, segment.getEndOffset());
                }
            }
            result.add(new SileroSpeechSegment(left, right,
                    calculateSecondByOffset(left, samplingRate), calculateSecondByOffset(right, samplingRate)));
        }else {
            result.add(new SileroSpeechSegment(left, right,
                    calculateSecondByOffset(left, samplingRate), calculateSecondByOffset(right, samplingRate)));
        }
        return result;
    }

    private Float calculateSecondByOffset(Integer offset, Integer samplingRate) {
        float secondValue = offset * 1.0f / samplingRate;
        return (float) Math.floor(secondValue * 1000.0f) / 1000.0f;
    }
}
