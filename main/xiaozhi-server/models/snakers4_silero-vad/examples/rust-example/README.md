# Stream example in Rust
Made after [C++ stream example](https://github.com/snakers4/silero-vad/tree/master/examples/cpp)

## Dependencies
- To build Rust crate `ort` you need `cc` installed.

## Usage
Just
```
cargo run
```
If you run example outside of this repo adjust environment variable
```
SILERO_MODEL_PATH=/path/to/silero_vad.onnx cargo run 
```
If you need to test against other wav file, not `recorder.wav`, specify it as the first argument
```
cargo run -- /path/to/audio/file.wav
```