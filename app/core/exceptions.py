class ApplicationError(Exception):
    """应用业务异常基类
    
    所有业务异常都应继承此类，并定义 status_code、code、message 三个类属性。
    具体的业务异常应在对应模块的 exceptions.py 中定义。
    """

    status_code: int = 500  # 默认状态码
    code: str = "APPLICATION_ERROR"  # 默认异常code
    message: str = "服务器内部错误"  # 默认异常提示

