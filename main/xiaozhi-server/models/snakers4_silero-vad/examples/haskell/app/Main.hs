module Main (main) where

import qualified Data.Vector.Storable as Vector
import Data.WAVE
import Data.Function
import Silero

main :: IO ()
main =
  withModel $ \model -> do
    wav <- getWAVEFile "example.wav"
    let samples =
          concat (waveSamples wav)
            & Vector.fromList
            & Vector.map (realToFrac . sampleToDouble)
    let vad =
          (defaultVad model)
            { startThreshold = 0.5
            , endThreshold = 0.35
            }
    segments <- detectSegments vad samples
    print segments