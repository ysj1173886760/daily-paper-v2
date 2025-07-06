import logging


def setup_logger(name="daily-paper", level=logging.INFO):
    """
    设置日志记录器

    Args:
        name (str): 日志记录器名称
        level: 日志级别

    Returns:
        logger: 配置好的日志记录器
    """
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(level)

    logger.handlers = []

    # 创建格式化器
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# 创建默认的日志记录器实例
logger = setup_logger()
