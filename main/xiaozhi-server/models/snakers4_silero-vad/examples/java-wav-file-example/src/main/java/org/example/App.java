package org.example;

import ai.onnxruntime.OrtException;
import java.io.File;
import java.util.List;

public class App {

    private static final String MODEL_PATH = "/path/silero_vad.onnx";
    private static final String EXAMPLE_WAV_FILE = "/path/example.wav";
    private static final int SAMPLE_RATE = 16000;
    private static final float THRESHOLD = 0.5f;
    private static final int MIN_SPEECH_DURATION_MS = 250;
    private static final float MAX_SPEECH_DURATION_SECONDS = Float.POSITIVE_INFINITY;
    private static final int MIN_SILENCE_DURATION_MS = 100;
    private static final int SPEECH_PAD_MS = 30;

    public static void main(String[] args) {
        // Initialize the Voice Activity Detector
        SileroVadDetector vadDetector;
        try {
            vadDetector = new SileroVadDetector(MODEL_PATH, THRESHOLD, SAMPLE_RATE,
                    MIN_SPEECH_DURATION_MS, MAX_SPEECH_DURATION_SECONDS, MIN_SILENCE_DURATION_MS, SPEECH_PAD_MS);
            fromWavFile(vadDetector, new File(EXAMPLE_WAV_FILE));
        } catch (OrtException e) {
            System.err.println("Error initializing the VAD detector: " + e.getMessage());
        }
    }

    public static void fromWavFile(SileroVadDetector vadDetector, File wavFile) {
        List<SileroSpeechSegment> speechTimeList = vadDetector.getSpeechSegmentList(wavFile);
        for (SileroSpeechSegment speechSegment : speechTimeList) {
            System.out.println(String.format("start second: %f, end second: %f",
                    speechSegment.getStartSecond(), speechSegment.getEndSecond()));
        }
    }
}
