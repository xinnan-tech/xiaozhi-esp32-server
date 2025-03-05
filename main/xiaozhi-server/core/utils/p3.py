import struct

def decode_opus_from_file(input_file):
    """
    从p3文件中解码 Opus 数据，并返回一个 Opus 数据包的列表以及总时长。
    """
    opus_datas = []
    total_frames = 0
    sample_rate = 16000  # 文件采样率
    frame_duration_ms = 60  # 帧时长
    frame_size = int(sample_rate * frame_duration_ms / 1000)

    with open(input_file, 'rb') as f:
        while True:
            # 读取头部（4字节）：[1字节类型，1字节保留，2字节长度]
            header = f.read(4)
            if not header:
                break

            # 解包头部信息
            _, _, data_len = struct.unpack('>BBH', header)

            # 根据头部指定的长度读取 Opus 数据
            opus_data = f.read(data_len)
            if len(opus_data) != data_len:
                raise ValueError(f"Data length({len(opus_data)}) mismatch({data_len}) in the file.")

            opus_datas.append(opus_data)
            total_frames += 1

    # 计算总时长
    total_duration = (total_frames * frame_duration_ms) / 1000.0
    return opus_datas, total_duration