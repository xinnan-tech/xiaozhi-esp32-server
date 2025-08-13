//
// Copyright © 2025 Agora
// This file is part of TEN Framework, an open source project.
// Licensed under the Apache License, Version 2.0, with certain conditions.
// Refer to the "LICENSE" file in the root directory for more information.
//
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <time.h>
#include <inttypes.h>
#include <string.h> // memcmp
#ifdef _WIN32
#include <windows.h>
#endif

#include "ten_vad.h"

#if defined(__APPLE__)
#include <TargetConditionals.h>
#if TARGET_OS_IPHONE
#include "sample_array.h"
#endif
#endif

const int hop_size = 256; // 16 ms per frame

uint64_t get_timestamp_ms()
{
#ifdef _WIN32
  LARGE_INTEGER frequency;
  LARGE_INTEGER counter;
  QueryPerformanceFrequency(&frequency);
  QueryPerformanceCounter(&counter);
  return (uint64_t)(counter.QuadPart * 1000 / frequency.QuadPart);
#else
  struct timespec ts;
  uint64_t millis;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  millis = ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
  return millis;
#endif
}

// define RIFF header
#pragma pack(push, 1)
typedef struct
{
  char chunk_id[4];    // should be "RIFF"
  uint32_t chunk_size; // file total size - 8
  char format[4];      // should be "WAVE"
} riff_header_t;

// define each sub chunk header
typedef struct
{
  char id[4];    // should be "fmt " or "data"
  uint32_t size; // chunk data size
} chunk_header_t;
#pragma pack(pop)

// define WAV file info we care about
typedef struct
{
  uint16_t audio_format;    // audio format (e.g. PCM=1)
  uint16_t num_channels;    // number of channels
  uint32_t sample_rate;     // sample rate
  uint32_t byte_rate;       // byte rate
  uint16_t block_align;     // block align
  uint16_t bits_per_sample; // bits per sample
  uint32_t data_size;       // data size
  long data_offset;         // data offset in file
} wav_info_t;

int read_wav_file(FILE *fp, wav_info_t *info);

int vad_process(int16_t *input_buf, uint32_t frame_num,
                float *out_probs, int32_t *out_flags,
                float *use_time)
{
  printf("tenvadsrc version: %s\n", ten_vad_get_version());
  void *ten_vad_handle = NULL;
  float voice_threshold = 0.5f;
  ten_vad_create(&ten_vad_handle, hop_size, voice_threshold);

  uint64_t start = get_timestamp_ms();
  for (int i = 0; i < frame_num; ++i)
  {
    int16_t *audio_data = input_buf + i * hop_size;
    int res = ten_vad_process(ten_vad_handle, audio_data, hop_size,
                              &out_probs[i], &out_flags[i]);
    if (res == 0)
    {
      printf("[%d] %0.6f, %d\n", i, out_probs[i], out_flags[i]);
    }
    else
    {
      printf("ten_vad_process failed res %d\n", res);
    }
  }
  uint64_t end = get_timestamp_ms();
  *use_time = (float)(end - start);

  ten_vad_destroy(&ten_vad_handle);
  ten_vad_handle = NULL;
  return 0;
}

int test_with_wav(int argc, char *argv[])
{
  if (argc < 3)
  {
    printf("Warning: Test.exe input.wav output.txt\n");
    return 0;
  }
  char *input_file = argv[1];
  char *out_file = argv[2];

  FILE *fp = fopen(input_file, "rb");
  if (fp == NULL)
  {
    printf("Failed to open input file: %s\n", input_file);
    return 1;
  }
  fseek(fp, 0, SEEK_SET);
  wav_info_t info;
  if (read_wav_file(fp, &info) != 0)
  {
    printf("Failed to read WAV file header\n");
    fclose(fp);
    return 1;
  }

  uint32_t byte_num = info.data_size;
  printf("WAV file byte num: %d\n", byte_num);
  char *input_buf = (char *)malloc(byte_num);
  fseek(fp, info.data_offset, SEEK_SET);
  fread(input_buf, 1, byte_num, fp);
  fclose(fp);
  fp = NULL;

  uint32_t sample_num = byte_num / sizeof(int16_t);
  float total_audio_time = (float)sample_num / 16.0;
  printf("total_audio_time: %.2f(ms)\n", total_audio_time);
  uint32_t frame_num = sample_num / hop_size;
  printf("Audio frame Num: %d\n", frame_num);
  float *out_probs = (float *)malloc(frame_num * sizeof(float));
  int32_t *out_flags = (int32_t *)malloc(frame_num * sizeof(int32_t));  // Output flags are binary speech indicators (0 for non-speech signal, 1 for speech signal)
  float use_time = .0;
  vad_process((int16_t *)input_buf, frame_num,
               out_probs, out_flags,
               &use_time);
  float rtf = use_time / total_audio_time;
  printf("Consuming time: %f(ms), audio-time: %.2f(ms), =====> RTF: %0.6f\n",
          use_time, total_audio_time, rtf);

  FILE *fout = fopen(out_file, "w");
  if (fout != NULL)
  {
    for (int i = 0; i < frame_num; i++)
    {
      fprintf(fout, "[%d] %0.6f, %d\n", i, out_probs[i], out_flags[i]);
    }
    fclose(fout);
    fout = NULL;
  }

  free(input_buf);
  free(out_probs);
  free(out_flags);
  return 0;
}

#if TARGET_OS_IPHONE
// Used for iOS APP demo
int test_with_array()
{
  char *input_buf = (char *)sample_array;
  uint32_t byte_num = sizeof(sample_array) / sizeof(sample_array[0]);
  printf("WAV file byte num: %d\n", byte_num);

  uint32_t sample_num = byte_num / sizeof(int16_t);
  float total_audio_time = (float)sample_num / 16.0;
  printf("total_audio_time: %.2f(ms)\n", total_audio_time);
  uint32_t frame_num = sample_num / hop_size;
  printf("Audio frame Num: %d\n", frame_num);
  float *out_probs = (float *)malloc(frame_num * sizeof(float));
  int32_t *out_flags = (int32_t *)malloc(frame_num * sizeof(int32_t));
  float use_time = .0;
  vad_process((int16_t *)input_buf, frame_num,
               out_probs, out_flags,
               &use_time);
  float rtf = use_time / total_audio_time;
  printf("Consuming time: %f(ms), audio-time: %.2f(ms), =====> RTF: %0.6f\n",
          use_time, total_audio_time, rtf);

  return 0;
}
#endif

int main(int argc, char *argv[])
{
#if TARGET_OS_IPHONE
  return test_with_array();
#else
  return test_with_wav(argc, argv);
#endif
}

// function to read WAV file info
int read_wav_file(FILE *fp, wav_info_t *info)
{
  if (fp == NULL || info == NULL)
    return -1;
  // save current file position
  long orig_pos = ftell(fp);
  fseek(fp, 0, SEEK_SET);
  // read RIFF header
  riff_header_t riff;
  if (fread(&riff, sizeof(riff_header_t), 1, fp) != 1)
  {
    fprintf(stderr, "Can not read RIFF head\n");
    fseek(fp, orig_pos, SEEK_SET);
    return -1;
  }
  // verify RIFF/WAVE format
  if (memcmp(riff.chunk_id, "RIFF", 4) != 0 ||
      memcmp(riff.format, "WAVE", 4) != 0)
  {
    fprintf(stderr, "not a valid RIFF/WAVE file\n");
    fseek(fp, orig_pos, SEEK_SET);
    return -1;
  }
  // initialize, mark chunks not found yet
  int fmt_found = 0, data_found = 0;
  memset(info, 0, sizeof(wav_info_t));

  // iterate all chunks
  while (!feof(fp))
  {
    chunk_header_t chunk;
    if (fread(&chunk, sizeof(chunk_header_t), 1, fp) != 1)
    {
      break; // read failed, maybe end of file
    }
    // check if it's fmt chunk
    if (memcmp(chunk.id, "fmt ", 4) == 0)
    {
      // read fmt data
      fmt_found = 1;
      if (chunk.size < 16)
      {
        fprintf(stderr, "fmt chunk size is abnormal\n");
        fseek(fp, orig_pos, SEEK_SET);
        return -1;
      }
      // read fmt parameters
      if (fread(&info->audio_format, 2, 1, fp) != 1 ||
          fread(&info->num_channels, 2, 1, fp) != 1 ||
          fread(&info->sample_rate, 4, 1, fp) != 1 ||
          fread(&info->byte_rate, 4, 1, fp) != 1 ||
          fread(&info->block_align, 2, 1, fp) != 1 ||
          fread(&info->bits_per_sample, 2, 1, fp) != 1)
      {
        fprintf(stderr, "failed to read fmt data\n");
        fseek(fp, orig_pos, SEEK_SET);
        return -1;
      }
      // skip fmt extension data
      if (chunk.size > 16)
      {
        fseek(fp, chunk.size - 16, SEEK_CUR);
      }
    }
    // check if it's data chunk
    else if (memcmp(chunk.id, "data", 4) == 0)
    {
      data_found = 1;
      info->data_size = chunk.size;
      info->data_offset = ftell(fp); // record data start position
      break;                         // found data chunk, can exit loop
    }
    // other chunks, skip
    else
    {
      // consider byte alignment, pad odd size
      fseek(fp, (chunk.size + (chunk.size % 2)), SEEK_CUR);
    }
  }
  // check if necessary chunks are found
  if (!fmt_found)
  {
    fprintf(stderr, "fmt chunk not found\n");
    fseek(fp, orig_pos, SEEK_SET);
    return -1;
  }
  if (!data_found)
  {
    fprintf(stderr, "data chunk not found\n");
    fseek(fp, orig_pos, SEEK_SET);
    return -1;
  }
  // restore original file position
  fseek(fp, orig_pos, SEEK_SET);
  return 0;
}
