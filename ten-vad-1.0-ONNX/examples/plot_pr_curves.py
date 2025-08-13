#
#  Copyright © 2025 Agora
#  This file is part of TEN Framework, an open source project.
#  Licensed under the Apache License, Version 2.0, with certain conditions.
#  Refer to the "LICENSE" file in the root directory for more information.
#
import os, glob, sys, torchaudio
import numpy as np
import scipy.io.wavfile as Wavfile
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix

os.system('git clone https://github.com/snakers4/silero-vad.git')  # Clone the silero-vad repo, using Silero V5
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "./silero-vad/src")))
from silero_vad.utils_vad import VADIterator, init_jit_model

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../include")))
from ten_vad import TenVad

def convert_label_to_framewise(label_file, hop_size):
    frame_duration = hop_size / 16000
    with open(label_file, "r") as f:
        lines = f.readlines()
    content = lines[0].strip().split(",")[1:]
    start = np.array(
        content[::3], dtype=float
    )  # Start point of each audio segment
    end = np.array(
        content[1:][::3], dtype=float
    )  # End point of each audio segment
    lab_manual = np.array(
        content[2:][::3], dtype=int
    )  # label, 0/1 stands for non-speech or speech, respectively
    assert (
        len(start) == len(end) 
        and len(start) == len(lab_manual) 
        and len(end) == len(lab_manual)
    )
    
    num = np.array(
        np.round(((end - start) / frame_duration)), dtype=np.int32
    )  # get number of frames of each audio segment
    label_framewise = np.array([])
    for segment_idx in range(len(num)):
        cur_lab = int(lab_manual[segment_idx])
        num_segment = num[segment_idx]

        if cur_lab == 1:
            vad_result_this_segment = np.ones(num_segment)
        elif cur_lab == 0:
            vad_result_this_segment = np.zeros(num_segment)
        label_framewise = np.append(label_framewise, vad_result_this_segment)
    frame_num = min(
        label_framewise.__len__(), int((end[-1] - start[0]) / frame_duration)
    )
    label_framewise = label_framewise[:frame_num]

    return label_framewise


def read_file(file_path):
    with open(file_path, "r") as f:
        lines = f.readlines()
    lines_arr = np.array([])
    for line in lines:
        lines_arr = np.append(lines_arr, float(line.strip()))

    return lines_arr

def get_precision_recall(VAD_result, label, threshold):
    vad_result_hard = np.where(VAD_result >= threshold, 1, 0)

    # Compute confusion matrix
    TN, FP, FN, TP = confusion_matrix(label, vad_result_hard).ravel()

    # Compute precision, recall, false positive rate and false negative rate
    precision = TP / (TP + FP) if (TP + FP) > 0 else 0
    recall = TP / (TP + FN) if (TP + FN) > 0 else 0
    FPR = FP / (FP + TN) if (FP + TN) > 0 else 0
    FNR = FN / (TP + FN) if (TP + FN) > 0 else 0

    return precision, recall, FPR, FNR

def silero_vad_inference_single_file(wav_path):
    current_directory = os.path.dirname(os.path.abspath(__file__))
    model = init_jit_model(f'{current_directory}/silero-vad/src/silero_vad/data/silero_vad.jit')
    vad_iterator = VADIterator(model)
    window_size_samples = 512
    speech_probs = np.array([])
    
    wav, sr = torchaudio.load(wav_path)
    wav = wav.squeeze(0)
    for i in range(0, len(wav), window_size_samples):
        chunk = wav[i: i+ window_size_samples]
        if len(chunk) < window_size_samples:
            break
        speech_prob = model(chunk, sr).item()
        speech_probs = np.append(speech_probs, speech_prob)
    vad_iterator.reset_states()  # reset model states after each audio
    
    return speech_probs, window_size_samples

def ten_vad_process_wav(ten_vad_instance, wav_path, hop_size=256):
    _, data = Wavfile.read(wav_path)
    num_frames = data.shape[0] // hop_size
    voice_prob_arr = np.array([])
    for i in range(num_frames):
        input_data = data[i * hop_size: (i + 1) * hop_size]
        voice_prob, _ = ten_vad_instance.process(input_data)
        voice_prob_arr = np.append(voice_prob_arr, voice_prob)

    return voice_prob_arr

if __name__ == "__main__":
    # Get the directory of the script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # TEN-VAD-TestSet dir
    test_dir = f"{script_dir}/../testset"

    # Initialization
    hop_size = 256
    threshold = 0.5
    label_all, vad_result_ten_vad_all = np.array([]), np.array([])
    label_hop_512_all, vad_result_silero_vad_all = np.array([]), np.array([])
    wav_list = glob.glob(f"{test_dir}/*.wav")

    # The WebRTC VAD is from the latest version of WebRTC and is not plotted here
    print("Start processing")
    for wav_path in wav_list:
        # Running TEN VAD
        ten_vad_instance = TenVad(hop_size, threshold)
        label_file = wav_path.replace(".wav", ".scv")
        label = convert_label_to_framewise(
            label_file, hop_size=hop_size
        )  # Convert the VAD label to frame-wise one
        vad_result_ten_vad = ten_vad_process_wav(
            ten_vad_instance, wav_path, hop_size=hop_size
        )
        frame_num = min(label.__len__(), vad_result_ten_vad.__len__())
        vad_result_ten_vad_all = np.append(
            vad_result_ten_vad_all, vad_result_ten_vad[1:frame_num]
        )
        label_all = np.append(label_all, label[:frame_num - 1])
        del ten_vad_instance  # To prevent getting different results of each run

        # Running Silero VAD
        label_hop_512 = convert_label_to_framewise(
            label_file, hop_size=512
        )  # Convert the VAD label to frame-wise one for Silero VAD
        vad_result_silero_vad, _ = silero_vad_inference_single_file(wav_path)
        frame_num_silero_vad = min(label_hop_512.__len__(), vad_result_silero_vad.__len__())
        vad_result_silero_vad_all = np.append(vad_result_silero_vad_all, vad_result_silero_vad[:frame_num_silero_vad])
        label_hop_512_all = np.append(label_hop_512_all, label_hop_512[:frame_num_silero_vad])

    # Compute Precision and Recall  
    threshold_arr = np.arange(0, 1.01, 0.01)
    pr_data_arr = np.zeros((threshold_arr.__len__(), 3))
    pr_data_silero_vad_arr = np.zeros((threshold_arr.__len__(), 3))

    for ind, threshold in enumerate(threshold_arr):
        precision, recall, FPR, FNR = get_precision_recall(vad_result_ten_vad_all, label_all, threshold)
        pr_data_arr[ind] = precision, recall, threshold

        precision_silero_vad, recall_silero_vad, FPR_silero_vad, FNR_silero_vad = get_precision_recall(vad_result_silero_vad_all, label_hop_512_all, threshold)
        pr_data_silero_vad_arr[ind] = precision_silero_vad, recall_silero_vad, threshold

    # Plot PR Curve
    print("Plotting PR Curve")
    pr_data_arr_to_plot = pr_data_arr[:-1] 
    plt.plot(
        pr_data_arr_to_plot[:, 1],
        pr_data_arr_to_plot[:, 0],
        color="red",
        label="TEN VAD",
    )  # Precision on y-axis, Recall on x-axis
    pr_data_silero_vad_arr_to_plot = pr_data_silero_vad_arr[:-1]
    plt.plot(
        pr_data_silero_vad_arr_to_plot[:, 1],  # Recall (x-axis)
        pr_data_silero_vad_arr_to_plot[:, 0],  # Precision (y-axis)
        color="blue",
        label="Silero VAD",
    )

    plt.xlabel("Recall", fontsize=14, fontweight="bold", color="black")
    plt.ylabel("Precision", fontsize=14, fontweight="bold", color="black") 
    legend = plt.legend()
    legend.get_texts()[0].set_fontweight("bold")
    legend.get_texts()[1].set_fontweight("bold")
    plt.grid(True)
    plt.xlim(0.65, 1)
    plt.ylim(0.7, 1)
    plt.title(
        "Precision-Recall Curve of TEN VAD on TEN-VAD-TestSet",
        fontsize=12,
        color="black",
        fontweight="bold",
    )
    save_path = f"{script_dir}/PR_Curves.png"
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    print(f"PR Curves png file saved, save path: {save_path}")

    # Save the PR data to txt file
    pr_data_save_path = f"{script_dir}/PR_data_TEN_VAD.txt"
    with open(pr_data_save_path, "w") as f:
        for ind in range(pr_data_arr.shape[0]):
            precision, recall, threshold = (
                pr_data_arr[ind, 0],
                pr_data_arr[ind, 1],
                pr_data_arr[ind, 2],
            )
            f.write(f"{threshold:.2f} {precision:.4f} {recall:.4f}\n")
    print("Processing done!")


