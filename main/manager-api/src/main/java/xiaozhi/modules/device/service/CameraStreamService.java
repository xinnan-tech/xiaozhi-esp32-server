package xiaozhi.modules.device.service;

import java.io.IOException;
import java.io.OutputStream;

public interface CameraStreamService {
    void startStream(String deviceId, Integer fps, Integer quality);
    void stopStream(String deviceId);
    void openMjpegStream(String deviceId, OutputStream os) throws IOException;
}


