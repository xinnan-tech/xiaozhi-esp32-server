package org.example;

import ai.onnxruntime.OrtException;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

/**
 * Silero VAD Detector
 * Real-time voice activity detection
 * 
 * @author VvvvvGH
 */
public class SlieroVadDetector {
    // ONNX model for speech processing
    private final SlieroVadOnnxModel model;
    // Speech start threshold
    private final float startThreshold;
    // Speech end threshold
    private final float endThreshold;
    // Sampling rate
    private final int samplingRate;
    // Minimum silence samples to determine speech end
    private final float minSilenceSamples;
    // Speech padding samples for calculating speech boundaries
    private final float speechPadSamples;
    // Triggered state (whether speech is being detected)
    private boolean triggered;
    // Temporary speech end sample position
    private int tempEnd;
    // Current sample position
    private int currentSample;


    public SlieroVadDetector(String modelPath,
                             float startThreshold,
                             float endThreshold,
                             int samplingRate,
                             int minSilenceDurationMs,
                             int speechPadMs) throws OrtException {
        // Validate sampling rate
        if (samplingRate != 8000 && samplingRate != 16000) {
            throw new IllegalArgumentException("Does not support sampling rates other than [8000, 16000]");
        }

        // Initialize parameters
        this.model = new SlieroVadOnnxModel(modelPath);
        this.startThreshold = startThreshold;
        this.endThreshold = endThreshold;
        this.samplingRate = samplingRate;
        this.minSilenceSamples = samplingRate * minSilenceDurationMs / 1000f;
        this.speechPadSamples = samplingRate * speechPadMs / 1000f;
        // Reset state
        reset();
    }

    /**
     * Reset detector state
     */
    public void reset() {
        model.resetStates();
        triggered = false;
        tempEnd = 0;
        currentSample = 0;
    }

    /**
     * Process audio data and detect speech events
     * 
     * @param data Audio data as byte array
     * @param returnSeconds Whether to return timestamps in seconds
     * @return Speech event (start or end) or empty map if no event
     */
    public Map<String, Double> apply(byte[] data, boolean returnSeconds) {

        // Convert byte array to float array
        float[] audioData = new float[data.length / 2];
        for (int i = 0; i < audioData.length; i++) {
            audioData[i] = ((data[i * 2] & 0xff) | (data[i * 2 + 1] << 8)) / 32767.0f;
        }

        // Get window size from audio data length
        int windowSizeSamples = audioData.length;
        // Update current sample position
        currentSample += windowSizeSamples;

        // Get speech probability from model
        float speechProb = 0;
        try {
            speechProb = model.call(new float[][]{audioData}, samplingRate)[0];
        } catch (OrtException e) {
            throw new RuntimeException(e);
        }

        // Reset temporary end if speech probability exceeds threshold
        if (speechProb >= startThreshold && tempEnd != 0) {
            tempEnd = 0;
        }

        // Detect speech start
        if (speechProb >= startThreshold && !triggered) {
            triggered = true;
            int speechStart = (int) (currentSample - speechPadSamples);
            speechStart = Math.max(speechStart, 0);
            Map<String, Double> result = new HashMap<>();
            // Return in seconds or samples based on returnSeconds parameter
            if (returnSeconds) {
                double speechStartSeconds = speechStart / (double) samplingRate;
                double roundedSpeechStart = BigDecimal.valueOf(speechStartSeconds).setScale(1, RoundingMode.HALF_UP).doubleValue();
                result.put("start", roundedSpeechStart);
            } else {
                result.put("start", (double) speechStart);
            }

            return result;
        }

        // Detect speech end
        if (speechProb < endThreshold && triggered) {
            // Initialize or update temporary end position
            if (tempEnd == 0) {
                tempEnd = currentSample;
            }
            // Wait for minimum silence duration before confirming speech end
            if (currentSample - tempEnd < minSilenceSamples) {
                return Collections.emptyMap();
            } else {
                // Calculate speech end time and reset state
                int speechEnd = (int) (tempEnd + speechPadSamples);
                tempEnd = 0;
                triggered = false;
                Map<String, Double> result = new HashMap<>();

                if (returnSeconds) {
                    double speechEndSeconds = speechEnd / (double) samplingRate;
                    double roundedSpeechEnd = BigDecimal.valueOf(speechEndSeconds).setScale(1, RoundingMode.HALF_UP).doubleValue();
                    result.put("end", roundedSpeechEnd);
                } else {
                    result.put("end", (double) speechEnd);
                }
                return result;
            }
        }

        // No speech event detected
        return Collections.emptyMap();
    }

    public void close() throws OrtException {
        reset();
        model.close();
    }
}
