# Pyaudio Streaming Example

This example notebook shows how micophone audio fetched by pyaudio can be processed with Silero-VAD.

It has been designed as a low-level example for binary real-time streaming using only the prediction of the model, processing the binary data and plotting the speech probabilities at the end to visualize it.

Currently, the notebook consits of two examples:
 - One that records audio of a predefined length from the microphone, process it with Silero-VAD, and plots it afterwards.
 - The other one plots the speech probabilities in real-time (using jupyterplot) and records the audio until you press enter.
 
 This example does not work in google colab! For local usage only.

## Example Video for the Real-Time Visualization


https://user-images.githubusercontent.com/8079748/117580455-4622dd00-b0f8-11eb-858d-e6368ed4eada.mp4






