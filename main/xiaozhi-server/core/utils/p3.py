import struct

def decode_opus_from_file(input_file):
    """
    Decode Opus data from p3 file and return a list of Opus data packets and total duration.
    """
    opus_datas = []
    total_frames = 0
    sample_rate = 16000  # File sample rate
    frame_duration_ms = 60  # Frame duration
    frame_size = int(sample_rate * frame_duration_ms / 1000)

    with open(input_file, 'rb') as f:
        while True:
            # Read header (4 bytes): [1 byte type, 1 byte reserved, 2 bytes length]
            header = f.read(4)
            if not header:
                break

            # Unpack header information
            _, _, data_len = struct.unpack('>BBH', header)

            # Read Opus data according to header specified length
            opus_data = f.read(data_len)
            if len(opus_data) != data_len:
                raise ValueError(f"Data length({len(opus_data)}) mismatch({data_len}) in the file.")

            opus_datas.append(opus_data)
            total_frames += 1

    # Calculate total duration
    total_duration = (total_frames * frame_duration_ms) / 1000.0

    return opus_datas, total_duration

def decode_opus_from_bytes(input_bytes):
    """
    Decode Opus data from p3 binary data and return a list of Opus data packets and total duration.
    """
    import io

    opus_datas = []
    total_frames = 0
    sample_rate = 16000  # File sample rate
    frame_duration_ms = 60  # Frame duration
    frame_size = int(sample_rate * frame_duration_ms / 1000)

    f = io.BytesIO(input_bytes)

    while True:
        header = f.read(4)
        if not header:
            break

        _, _, data_len = struct.unpack('>BBH', header)

        opus_data = f.read(data_len)
        if len(opus_data) != data_len:
            raise ValueError(f"Data length({len(opus_data)}) mismatch({data_len}) in the bytes.")

        opus_datas.append(opus_data)
        total_frames += 1

    total_duration = (total_frames * frame_duration_ms) / 1000.0

    return opus_datas, total_duration
