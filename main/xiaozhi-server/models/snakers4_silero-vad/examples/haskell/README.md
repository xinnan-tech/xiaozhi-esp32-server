# Haskell example

To run the example, make sure you put an ``example.wav`` in this directory, and then run the following:
```bash
stack run
```

The ``example.wav`` file must have the following requirements:
- Must be 16khz sample rate.
- Must be mono channel.
- Must be 16-bit audio.

This uses the [silero-vad](https://hackage.haskell.org/package/silero-vad) package, a haskell implementation based on the C# example.