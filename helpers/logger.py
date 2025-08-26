import logging
import os

# Tạo thư mục logs nếu chưa tồn tại
log_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs"
)
os.makedirs(log_dir, exist_ok=True)

# Đường dẫn file log
error_log_path = os.path.join(log_dir, "error.log")

# Tạo logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Đặt mức log tổng thể

# Tạo console handler để hiển thị log trên console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)  # Hiển thị tất cả log từ DEBUG trở lên
console_handler.setFormatter(
    logging.Formatter(
        "%(asctime)s - [%(levelname)s] - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
)

# Tạo file handler để ghi log vào file
file_handler = logging.FileHandler(
    filename=error_log_path,
    mode="a",
    encoding="utf-8",
)
file_handler.setLevel(logging.ERROR)  # Chỉ ghi log từ ERROR trở lên vào file
file_handler.setFormatter(
    logging.Formatter(
        "%(asctime)s - [%(levelname)s] - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
)

# Đảm bảo không thêm nhiều handler nếu file được import nhiều lần
if not logger.handlers:
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
