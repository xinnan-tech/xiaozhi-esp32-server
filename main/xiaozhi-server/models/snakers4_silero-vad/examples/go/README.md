## Golang Example

This is a sample program of how to run speech detection using `silero-vad` from Golang (CGO + ONNX Runtime).

### Requirements

- Golang >= v1.21
- ONNX Runtime

### Usage

```sh
go run ./cmd/main.go test.wav
```

> **_Note_**
>
> Make sure you have the ONNX Runtime library and C headers installed in your path.

