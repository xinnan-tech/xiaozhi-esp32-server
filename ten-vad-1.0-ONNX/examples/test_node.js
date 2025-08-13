#!/usr/bin/env node

//
// Copyright © 2025 Agora
// This file is part of TEN Framework, an open source project.
// Licensed under the Apache License, Version 2.0, with certain conditions.
// Refer to the "LICENSE" file in the root directory for more information.
//

/**
 * TEN VAD WebAssembly Node.js Test
 * Simplified and clean version based on main.c
 */

const fs = require('fs');
const path = require('path');

// Configuration
const HOP_SIZE = 256;          // 16ms per frame
const VOICE_THRESHOLD = 0.5;   // Voice detection threshold

// WASM module paths
const WASM_DIR = './../lib/Web';
const WASM_JS_FILE = path.join(WASM_DIR, 'ten_vad.js');
const WASM_BINARY_FILE = path.join(WASM_DIR, 'ten_vad.wasm');

// Global state
let vadModule = null;
let vadHandle = null;
let vadHandlePtr = null;

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function getTimestamp() {
    return Date.now();
}

function addHelperFunctions() {
    if (!vadModule.getValue) {
        vadModule.getValue = function(ptr, type) {
            switch (type) {
                case 'i32': return vadModule.HEAP32[ptr >> 2];
                case 'float': return vadModule.HEAPF32[ptr >> 2];
                default: throw new Error(`Unsupported type: ${type}`);
            }
        };
    }
    
    if (!vadModule.UTF8ToString) {
        vadModule.UTF8ToString = function(ptr) {
            if (!ptr) return '';
            let result = '';
            let i = ptr;
            while (vadModule.HEAPU8[i]) {
                result += String.fromCharCode(vadModule.HEAPU8[i++]);
            }
            return result;
        };
    }
}

// ============================================================================
// AUDIO GENERATION
// ============================================================================

function generateTestAudio(durationMs = 5000) {
    const sampleRate = 16000;
    const totalSamples = Math.floor(durationMs * sampleRate / 1000);
    const audioData = new Int16Array(totalSamples);
    
    console.log(`Generating ${totalSamples} samples for ${durationMs}ms audio...`);
    
    for (let i = 0; i < totalSamples; i++) {
        const t = i / sampleRate;
        let sample = 0;
        
        if (t < 2.0) {
            // Voice frequencies (440Hz + 880Hz)
            sample = Math.sin(2 * Math.PI * 440 * t) * 8000 +
                    Math.sin(2 * Math.PI * 880 * t) * 4000;
        } else if (t < 3.0) {
            // Noise
            sample = (Math.random() - 0.5) * 3000;
        } else if (t < 4.0) {
            // Mixed voice (220Hz + 660Hz)
            sample = Math.sin(2 * Math.PI * 220 * t) * 6000 + 
                    Math.sin(2 * Math.PI * 660 * t) * 3000;
        } else {
            // Silence with minimal noise
            sample = Math.random() * 50;
        }
        
        audioData[i] = Math.max(-32768, Math.min(32767, Math.floor(sample)));
    }
    
    return audioData;
}

// ============================================================================
// VAD OPERATIONS
// ============================================================================

function getVADVersion() {
    if (!vadModule) return "unknown";
    try {
        const versionPtr = vadModule._ten_vad_get_version();
        return vadModule.UTF8ToString(versionPtr);
    } catch (error) {
        return "unknown";
    }
}

function createVADInstance() {
    try {
        vadHandlePtr = vadModule._malloc(4);
        const result = vadModule._ten_vad_create(vadHandlePtr, HOP_SIZE, VOICE_THRESHOLD);
        
        if (result === 0) {
            vadHandle = vadModule.getValue(vadHandlePtr, 'i32');
            return true;
        } else {
            console.error(`VAD creation failed with code: ${result}`);
            vadModule._free(vadHandlePtr);
            return false;
        }
    } catch (error) {
        console.error(`Error creating VAD instance: ${error.message}`);
        return false;
    }
}

function destroyVADInstance() {
    if (vadHandlePtr && vadModule) {
        vadModule._ten_vad_destroy(vadHandlePtr);
        vadModule._free(vadHandlePtr);
        vadHandlePtr = null;
        vadHandle = null;
    }
}

async function processAudio(inputBuf, frameNum, outProbs, outFlags) {
    console.log(`VAD version: ${getVADVersion()}`);
    
    if (!createVADInstance()) {
        return -1;
    }
    
    const startTime = getTimestamp();
    
    for (let i = 0; i < frameNum; i++) {
        const frameStart = i * HOP_SIZE;
        const frameData = inputBuf.slice(frameStart, frameStart + HOP_SIZE);
        
        const audioPtr = vadModule._malloc(HOP_SIZE * 2);
        const probPtr = vadModule._malloc(4);
        const flagPtr = vadModule._malloc(4);
        
        try {
            vadModule.HEAP16.set(frameData, audioPtr / 2);
            
            const result = vadModule._ten_vad_process(
                vadHandle, audioPtr, HOP_SIZE, probPtr, flagPtr
            );
            
            if (result === 0) {
                const probability = vadModule.getValue(probPtr, 'float');
                const flag = vadModule.getValue(flagPtr, 'i32');
                
                outProbs[i] = probability;
                outFlags[i] = flag;
                
                console.log(`[${i}] ${probability.toFixed(6)}, ${flag}`);
            } else {
                console.error(`Frame ${i} processing failed with code: ${result}`);
                outProbs[i] = 0.0;
                outFlags[i] = 0;
            }
        } finally {
            vadModule._free(audioPtr);
            vadModule._free(probPtr);
            vadModule._free(flagPtr);
        }
    }
    
    const endTime = getTimestamp();
    const processingTime = endTime - startTime;
    
    destroyVADInstance();
    return processingTime;
}

// ============================================================================
// RESULT HANDLING
// ============================================================================

function printResults(processingTime, totalAudioTime, outFlags, frameNum) {
    const rtf = processingTime / totalAudioTime;
    const voiceFrames = outFlags.filter(flag => flag === 1).length;
    const voicePercentage = (voiceFrames / frameNum * 100).toFixed(1);
    
    console.log(`\n=== Processing Results ===`);
    console.log(`Time: ${processingTime}ms, Audio: ${totalAudioTime.toFixed(2)}ms, RTF: ${rtf.toFixed(6)}`);
    console.log(`Voice frames: ${voiceFrames}/${frameNum} (${voicePercentage}%)`);
}

function saveResults(outProbs, outFlags, frameNum, filename = 'out.txt') {
    let output = '';
    for (let i = 0; i < frameNum; i++) {
        output += `[${i}] ${outProbs[i].toFixed(6)}, ${outFlags[i]}\n`;
    }
    
    try {
        fs.writeFileSync(filename, output);
        console.log(`Results saved to ${filename}`);
    } catch (error) {
        console.error(`Failed to save results: ${error.message}`);
    }
}

// ============================================================================
// TEST FUNCTIONS
// ============================================================================

async function testWithArray() {
    console.log("=== Array Test ===\n");
    
    const inputBuf = generateTestAudio(5000);
    const byteNum = inputBuf.byteLength;
    const sampleNum = byteNum / 2;
    const totalAudioTime = sampleNum / 16.0;
    const frameNum = Math.floor(sampleNum / HOP_SIZE);
    
    console.log(`Audio info: ${byteNum} bytes, ${frameNum} frames, ${totalAudioTime.toFixed(2)}ms`);
    
    const outProbs = new Float32Array(frameNum);
    const outFlags = new Int32Array(frameNum);
    
    const processingTime = await processAudio(inputBuf, frameNum, outProbs, outFlags);
    
    if (processingTime > 0) {
        printResults(processingTime, totalAudioTime, outFlags, frameNum);
    }
    
    return 0;
}

// WAV File parsing utilities
function parseWAVHeader(buffer) {
    if (buffer.length < 44) {
        throw new Error('Invalid WAV file: too small');
    }
    
    // Check RIFF header
    const riffHeader = buffer.toString('ascii', 0, 4);
    if (riffHeader !== 'RIFF') {
        throw new Error('Invalid WAV file: missing RIFF header');
    }
    
    // Check WAVE format
    const waveHeader = buffer.toString('ascii', 8, 12);
    if (waveHeader !== 'WAVE') {
        throw new Error('Invalid WAV file: not WAVE format');
    }
    
    let offset = 12;
    let dataOffset = -1;
    let dataSize = 0;
    let sampleRate = 0;
    let channels = 0;
    let bitsPerSample = 0;
    
    // Parse chunks
    while (offset < buffer.length - 8) {
        const chunkId = buffer.toString('ascii', offset, offset + 4);
        const chunkSize = buffer.readUInt32LE(offset + 4);
        
        if (chunkId === 'fmt ') {
            // Format chunk
            const audioFormat = buffer.readUInt16LE(offset + 8);
            channels = buffer.readUInt16LE(offset + 10);
            sampleRate = buffer.readUInt32LE(offset + 12);
            bitsPerSample = buffer.readUInt16LE(offset + 22);
            
            if (audioFormat !== 1) {
                throw new Error('Unsupported WAV format: only PCM is supported');
            }
            
            if (bitsPerSample !== 16) {
                throw new Error('Unsupported bit depth: only 16-bit is supported');
            }
        } else if (chunkId === 'data') {
            // Data chunk
            dataOffset = offset + 8;
            dataSize = chunkSize;
            break;
        }
        
        offset += 8 + chunkSize;
        // Align to even byte boundary
        if (chunkSize % 2 === 1) {
            offset++;
        }
    }
    
    if (dataOffset === -1) {
        throw new Error('Invalid WAV file: no data chunk found');
    }
    
    return {
        sampleRate,
        channels,
        bitsPerSample,
        dataOffset,
        dataSize,
        totalSamples: dataSize / (bitsPerSample / 8),
        samplesPerChannel: dataSize / (bitsPerSample / 8) / channels
    };
}

async function testWithWAV(inputFile, outputFile) {
    console.log("=== WAV File Test ===\n");
    
    if (!fs.existsSync(inputFile)) {
        console.error(`Input file not found: ${inputFile}`);
        return 1;
    }
    
    try {
        const buffer = fs.readFileSync(inputFile);
        
        // Parse WAV header properly
        const wavInfo = parseWAVHeader(buffer);
        console.log(`WAV Format: ${wavInfo.channels} channel(s), ${wavInfo.sampleRate}Hz, ${wavInfo.bitsPerSample}-bit`);
        console.log(`Total samples: ${wavInfo.totalSamples}, samples per channel: ${wavInfo.samplesPerChannel}`);
        
        // Validate format requirements
        if (wavInfo.sampleRate !== 16000) {
            console.warn(`Warning: Sample rate is ${wavInfo.sampleRate}Hz, expected 16000Hz`);
        }
        
        if (wavInfo.channels !== 1) {
            console.warn(`Warning: ${wavInfo.channels} channels detected, only first channel will be used`);
        }
        
        // Extract audio data
        const audioBuffer = buffer.slice(wavInfo.dataOffset, wavInfo.dataOffset + wavInfo.dataSize);
        const inputBuf = new Int16Array(audioBuffer.buffer.slice(audioBuffer.byteOffset));
        
        // Calculate correct sample number (for mono audio)
        const sampleNum = wavInfo.channels === 1 ? 
            wavInfo.samplesPerChannel : 
            Math.floor(wavInfo.samplesPerChannel); // Use only first channel if stereo
            
        const totalAudioTime = sampleNum / wavInfo.sampleRate * 1000; // in milliseconds
        const frameNum = Math.floor(sampleNum / HOP_SIZE);
        
        console.log(`Audio info: ${audioBuffer.length} bytes, ${sampleNum} samples, ${frameNum} frames, ${totalAudioTime.toFixed(2)}ms`);
        
        // If stereo, extract only the first channel
        let processedInput = inputBuf;
        if (wavInfo.channels > 1) {
            console.log(`Extracting mono from ${wavInfo.channels} channels...`);
            processedInput = new Int16Array(Math.floor(inputBuf.length / wavInfo.channels));
            for (let i = 0; i < processedInput.length; i++) {
                processedInput[i] = inputBuf[i * wavInfo.channels]; // Take first channel
            }
        }
        
        const outProbs = new Float32Array(frameNum);
        const outFlags = new Int32Array(frameNum);
        
        const processingTime = await processAudio(processedInput, frameNum, outProbs, outFlags);
        
        if (processingTime > 0) {
            printResults(processingTime, totalAudioTime, outFlags, frameNum);
            saveResults(outProbs, outFlags, frameNum, outputFile);
        }
        
        return 0;
    } catch (error) {
        console.error(`Error processing WAV file: ${error.message}`);
        return 1;
    }
}

async function runBenchmark() {
    console.log("=== Performance Benchmark ===\n");
    
    if (!createVADInstance()) return;
    
    const testData = new Int16Array(HOP_SIZE);
    for (let i = 0; i < HOP_SIZE; i++) {
        testData[i] = Math.sin(2 * Math.PI * 440 * i / 16000) * 8000;
    }
    
    const testCases = [100, 1000, 10000];
    
    for (const numFrames of testCases) {
        const audioPtr = vadModule._malloc(HOP_SIZE * 2);
        const probPtr = vadModule._malloc(4);
        const flagPtr = vadModule._malloc(4);
        
        vadModule.HEAP16.set(testData, audioPtr / 2);
        
        const startTime = getTimestamp();
        
        for (let i = 0; i < numFrames; i++) {
            vadModule._ten_vad_process(vadHandle, audioPtr, HOP_SIZE, probPtr, flagPtr);
        }
        
        const endTime = getTimestamp();
        const totalTime = endTime - startTime;
        const avgTime = totalTime / numFrames;
        
        // Calculate RTF (Real-time Factor)
        // Each frame represents 16ms of audio (HOP_SIZE=256 samples at 16kHz)
        const frameAudioTime = (HOP_SIZE / 16000) * 1000; // 16ms
        const totalAudioTime = numFrames * frameAudioTime;
        const rtf = totalTime / totalAudioTime;
        
        console.log(`${numFrames} frames: ${totalTime}ms total, ${avgTime.toFixed(3)}ms/frame, RTF: ${rtf.toFixed(3)}`);
        
        vadModule._free(audioPtr);
        vadModule._free(probPtr);
        vadModule._free(flagPtr);
    }
    
    destroyVADInstance();
}

// ============================================================================
// MODULE INITIALIZATION
// ============================================================================

async function loadModule() {
    try {
        console.log("Loading WebAssembly module...");
        
        if (!fs.existsSync(WASM_JS_FILE)) {
            throw new Error(`ten_vad.js not found at ${WASM_JS_FILE}`);
        }
        
        if (!fs.existsSync(WASM_BINARY_FILE)) {
            throw new Error(`ten_vad.wasm not found at ${WASM_BINARY_FILE}`);
        }
        
        // Read and modify the module file for Node.js compatibility
        const wasmJsContent = fs.readFileSync(WASM_JS_FILE, 'utf8');
        const modifiedContent = wasmJsContent
            .replace(/import\.meta\.url/g, `"${path.resolve(WASM_JS_FILE)}"`)
            .replace(/export default createVADModule;/, 'module.exports = createVADModule;');
        
        // Write temporary file
        const tempPath = './ten_vad_temp.js';
        fs.writeFileSync(tempPath, modifiedContent);
        
        // Load WASM binary
        const wasmBinary = fs.readFileSync(WASM_BINARY_FILE);
        
        // Load module
        const createVADModule = require(path.resolve(tempPath));
        vadModule = await createVADModule({
            wasmBinary: wasmBinary,
            locateFile: (filePath) => filePath.endsWith('.wasm') ? WASM_BINARY_FILE : filePath,
            noInitialRun: false,
            noExitRuntime: true
        });
        
        // Cleanup
        fs.unlinkSync(tempPath);
        
        // Add missing helper functions
        addHelperFunctions();
        
        console.log(`Module loaded successfully. Version: ${getVADVersion()}\n`);
        return true;
        
    } catch (error) {
        console.error(`Failed to load module: ${error.message}`);
        return false;
    }
}

// ============================================================================
// MAIN FUNCTION
// ============================================================================

async function main() {
    const args = process.argv.slice(2);
    
    // Initialize module
    if (!await loadModule()) {
        process.exit(1);
    }
    
    try {
        if (args.length >= 2) {
            // Test with WAV file
            const [inputFile, outputFile] = args;
            console.log(`Input: ${inputFile}, Output: ${outputFile}\n`);
            await testWithWAV(inputFile, outputFile);
        } else {
            // Test with generated array
            await testWithArray();
        }
        await runBenchmark();
        return 0;
    } catch (error) {
        console.error(`Test failed: ${error.message}`);
        return 1;
    }
}

// ============================================================================
// EXECUTION
// ============================================================================

if (require.main === module) {
    main().then(exitCode => {
        process.exit(exitCode);
    }).catch(error => {
        console.error(`Fatal error: ${error.message}`);
        process.exit(1);
    });
}

module.exports = { main, testWithArray, testWithWAV, runBenchmark }; 