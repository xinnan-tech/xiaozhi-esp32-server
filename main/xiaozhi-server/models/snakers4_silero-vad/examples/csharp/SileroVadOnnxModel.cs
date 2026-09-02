using Microsoft.ML.OnnxRuntime;
using Microsoft.ML.OnnxRuntime.Tensors;

using System;
using System.Collections.Generic;
using System.Linq;

namespace VADdotnet;


public class SileroVadOnnxModel : IDisposable
{
    private readonly InferenceSession session;
    private float[][][] state;
    private float[][] context;
    private int lastSr = 0;
    private int lastBatchSize = 0;
    private static readonly List<int> SAMPLE_RATES = [8000, 16000];

    public SileroVadOnnxModel(string modelPath)
    {
        var sessionOptions = new SessionOptions
        {
            InterOpNumThreads = 1,
            IntraOpNumThreads = 1,
            EnableCpuMemArena = true
        };

        session = new InferenceSession(modelPath, sessionOptions);
        ResetStates();
    }

    public void ResetStates()
    {
        state = new float[2][][];
        state[0] = new float[1][];
        state[1] = new float[1][];
        state[0][0] = new float[128];
        state[1][0] = new float[128];
        context = [];
        lastSr = 0;
        lastBatchSize = 0;
    }

    public void Dispose()
    {
        GC.SuppressFinalize(this);
    }

    public class ValidationResult(float[][] x, int sr)
    {
        public float[][] X { get; } = x;
        public int Sr { get; } = sr;
    }

    private static ValidationResult ValidateInput(float[][] x, int sr)
    {
        if (x.Length == 1)
        {
            x = [x[0]];
        }
        if (x.Length > 2)
        {
            throw new ArgumentException($"Incorrect audio data dimension: {x[0].Length}");
        }

        if (sr != 16000 && (sr % 16000 == 0))
        {
            int step = sr / 16000;
            float[][] reducedX = new float[x.Length][];

            for (int i = 0; i < x.Length; i++)
            {
                float[] current = x[i];
                float[] newArr = new float[(current.Length + step - 1) / step];

                for (int j = 0, index = 0; j < current.Length; j += step, index++)
                {
                    newArr[index] = current[j];
                }

                reducedX[i] = newArr;
            }

            x = reducedX;
            sr = 16000;
        }

        if (!SAMPLE_RATES.Contains(sr))
        {
            throw new ArgumentException($"Only supports sample rates {string.Join(", ", SAMPLE_RATES)} (or multiples of 16000)");
        }

        if (((float)sr) / x[0].Length > 31.25)
        {
            throw new ArgumentException("Input audio is too short");
        }

        return new ValidationResult(x, sr);
    }

    private static float[][] Concatenate(float[][] a, float[][] b)
    {
        if (a.Length != b.Length)
        {
            throw new ArgumentException("The number of rows in both arrays must be the same.");
        }

        int rows = a.Length;
        int colsA = a[0].Length;
        int colsB = b[0].Length;
        float[][] result = new float[rows][];

        for (int i = 0; i < rows; i++)
        {
            result[i] = new float[colsA + colsB];
            Array.Copy(a[i], 0, result[i], 0, colsA);
            Array.Copy(b[i], 0, result[i], colsA, colsB);
        }

        return result;
    }

    private static float[][] GetLastColumns(float[][] array, int contextSize)
    {
        int rows = array.Length;
        int cols = array[0].Length;

        if (contextSize > cols)
        {
            throw new ArgumentException("contextSize cannot be greater than the number of columns in the array.");
        }

        float[][] result = new float[rows][];

        for (int i = 0; i < rows; i++)
        {
            result[i] = new float[contextSize];
            Array.Copy(array[i], cols - contextSize, result[i], 0, contextSize);
        }

        return result;
    }

    public float[] Call(float[][] x, int sr)
    {
        var result = ValidateInput(x, sr);
        x = result.X;
        sr = result.Sr;
        int numberSamples = sr == 16000 ? 512 : 256;

        if (x[0].Length != numberSamples)
        {
            throw new ArgumentException($"Provided number of samples is {x[0].Length} (Supported values: 256 for 8000 sample rate, 512 for 16000)");
        }

        int batchSize = x.Length;
        int contextSize = sr == 16000 ? 64 : 32;

        if (lastBatchSize == 0)
        {
            ResetStates();
        }
        if (lastSr != 0 && lastSr != sr)
        {
            ResetStates();
        }
        if (lastBatchSize != 0 && lastBatchSize != batchSize)
        {
            ResetStates();
        }

        if (context.Length == 0)
        {
            context = new float[batchSize][];
            for (int i = 0; i < batchSize; i++)
            {
                context[i] = new float[contextSize];
            }
        }

        x = Concatenate(context, x);

        var inputs = new List<NamedOnnxValue>
            {
                NamedOnnxValue.CreateFromTensor("input", new DenseTensor<float>(x.SelectMany(a => a).ToArray(), [x.Length, x[0].Length])),
                NamedOnnxValue.CreateFromTensor("sr", new DenseTensor<long>(new[] { (long)sr }, [1])),
                NamedOnnxValue.CreateFromTensor("state", new DenseTensor<float>(state.SelectMany(a => a.SelectMany(b => b)).ToArray(), [state.Length, state[0].Length, state[0][0].Length]))
            };

        using var outputs = session.Run(inputs);
        var output = outputs.First(o => o.Name == "output").AsTensor<float>();
        var newState = outputs.First(o => o.Name == "stateN").AsTensor<float>();

        context = GetLastColumns(x, contextSize);
        lastSr = sr;
        lastBatchSize = batchSize;

        state = new float[newState.Dimensions[0]][][];
        for (int i = 0; i < newState.Dimensions[0]; i++)
        {
            state[i] = new float[newState.Dimensions[1]][];
            for (int j = 0; j < newState.Dimensions[1]; j++)
            {
                state[i][j] = new float[newState.Dimensions[2]];
                for (int k = 0; k < newState.Dimensions[2]; k++)
                {
                    state[i][j][k] = newState[i, j, k];
                }
            }
        }

        return [.. output];
    }
}
