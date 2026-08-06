from pathlib import Path

root = Path(__file__).parent

replacements = {
    "正在连接服务器...": "Đang kết nối tới máy chủ...",
    "连接成功，开始聊天吧~😊": "Kết nối thành công, bắt đầu trò chuyện nhé! 😊",
    "Disconnected, see you next time~😊": "Đã ngắt kết nối, hẹn gặp lại nhé 😊",
    "Please fill in OTA server URL": "Vui lòng nhập địa chỉ máy chủ OTA",
    "摄像头容器不存在": "Không tìm thấy vùng hiển thị camera",
    "摄像头已关闭": "Camera đã tắt",
    "摄像头": "Camera",
    "关闭": "Tắt",
    "摄像头启动失败，请检查浏览器权限": "Không thể khởi động camera, vui lòng kiểm tra quyền trình duyệt",
    "摄像头启动失败，可能被浏览器拒绝": "Không thể khởi động camera, có thể trình duyệt đã từ chối quyền",
    "启动摄像头异常": "Lỗi khi khởi động camera",
    "startCamera函数未定义": "Hàm startCamera chưa được định nghĩa",
    "录音中": "Đang ghi âm",
    "录音": "Ghi âm",
    "已连接": "Đã kết nối",
    "离线": "Ngoại tuyến",
    "挂断": "Ngắt kết nối",
    "拨号": "Kết nối",
    "请先连接服务器": "Vui lòng kết nối máy chủ trước",
    "打开/关闭摄像头": "Bật/tắt camera",
    "请先绑定验证码": "Vui lòng liên kết mã xác minh trước",
    "开始录音": "Bắt đầu ghi âm",
    "当前由于是http访问，无法录音，只能用文字交互": "Hiện đang truy cập bằng HTTP nên không thể ghi âm, chỉ có thể nhập văn bản",
    "麦克风不可用": "Micro không khả dụng",
    "模型选择下拉框不存在": "Không tìm thấy danh sách chọn mô hình",
    "已切换到模型": "Đã chuyển sang mô hình",
    "模型切换失败": "Chuyển mô hình thất bại",
    "模型切换错误": "Lỗi khi chuyển mô hình",
    "模型切换出错": "Có lỗi khi chuyển mô hình",
    "Live2D管理器未初始化": "Trình quản lý Live2D chưa được khởi tạo",
    "启用唤醒词时，至少需要填写一个唤醒词。": "Khi bật từ khóa đánh thức, cần nhập ít nhất một từ khóa.",
    "应用中...": "Đang áp dụng...",
    "地址已变更，是否继续？（将断开旧连接并重新连接）": "Địa chỉ đã thay đổi, bạn có muốn tiếp tục không? Kết nối cũ sẽ bị ngắt và kết nối lại.",
    "已取消地址变更。": "Đã hủy thay đổi địa chỉ.",
    "连接新服务器超时": "Kết nối tới máy chủ mới bị quá thời gian",
    "唤醒词配置已保存，唤醒词服务正在重启。": "Đã lưu cấu hình từ khóa đánh thức, dịch vụ đang khởi động lại.",
    "唤醒词已保存。是否现在重启唤醒词服务以立即生效？": "Đã lưu từ khóa đánh thức. Bạn có muốn khởi động lại dịch vụ ngay để áp dụng không?",
    "唤醒词配置已保存，可稍后手动重启服务后生效。": "Đã lưu cấu hình từ khóa đánh thức. Có thể khởi động lại dịch vụ sau để áp dụng.",
    "应用唤醒词失败": "Áp dụng từ khóa đánh thức thất bại",
    "应用唤醒词": "Áp dụng từ khóa đánh thức",
    "请输入OTA服务器地址": "Vui lòng nhập địa chỉ máy chủ OTA",
    "连接中...": "Đang kết nối...",
    "连接失败：请检查设备连接": "Kết nối thất bại: vui lòng kiểm tra thiết bị",
    "连接失败": "Kết nối thất bại",
    "OTA连接失败": "Kết nối OTA thất bại",
    "连接已存在或正在进行，忽略本次拨号请求": "Kết nối đã tồn tại hoặc đang thực hiện, bỏ qua yêu cầu này",
    "页面已连接，忽略自动拨号": "Trang đã kết nối, bỏ qua tự động kết nối",
    "页面正在连接中，忽略重复唤醒": "Trang đang kết nối, bỏ qua đánh thức lặp lại",
    "唤醒触发过于频繁，忽略本次自动拨号": "Kích hoạt đánh thức quá thường xuyên, bỏ qua lần này",
    "检测到唤醒词": "Đã phát hiện từ khóa đánh thức",
    "准备连接服务器": "Đang chuẩn bị kết nối máy chủ",
    "工具名称": "Tên công cụ",
    "新工具": "Công cụ mới",
    "工具描述": "Mô tả công cụ",
    "删除": "Xóa",
    "⚠️ 麦克风不可用，请检查权限设置，只能用文字交互": "⚠️ Không thể sử dụng micro, vui lòng kiểm tra quyền truy cập. Chỉ có thể nhập văn bản.",
    "⚠️ 当前由于是http访问，无法录音，只能用文字交互": "⚠️ Đang truy cập bằng HTTP nên không thể ghi âm, chỉ có thể nhập văn bản.",
}

exts = {".js", ".html", ".css"}

changed = []
for path in root.rglob("*"):
    if path.is_file() and path.suffix.lower() in exts:
        text = path.read_text(encoding="utf-8", errors="ignore")
        old = text
        for a, b in replacements.items():
            text = text.replace(a, b)
        if text != old:
            path.write_text(text, encoding="utf-8")
            changed.append(str(path.relative_to(root)))

print("Đã Việt hóa các file:")
for f in changed:
    print(" -", f)
print("Xong.")