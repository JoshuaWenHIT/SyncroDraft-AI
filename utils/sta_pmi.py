import json
from datetime import datetime
from typing import Dict, Any, Optional, List

from setuptools._distutils.compat import numpy


class StrictJSONStructure:
    """严格的JSON结构体类（支持校验+固定Key顺序）"""

    # 核心固定Key（必须按此顺序输出）
    CORE_KEYS: List[str] = [
        "uid",  # local pmi id
        "category",  # st(Symmetrical tolerance), at(Asymmetric tolerance), rd(Reference dimension), bd(Basic dimension), cfd(Circular feature dimension), fcf(Feature control frame), dp(Datum plane)
        "content",  # OCR results
        "embedding",  # local feature tensor
    ]
    # 可选扩展Key（附加在核心Key之后，无固定顺序）
    OPTIONAL_KEYS: List[str] = ["ext_data", "tags", "operator"]

    def __init__(
        self, uid: int, category: str, content: str, embedding: numpy.ndarray, **kwargs
    ):

        # 核心字段校验
        self._validate_core_fields(uid, category)

        # 初始化核心字段
        self.uid = uid
        self.category = category

        # 初始化可选扩展字段（仅允许OPTIONAL_KEYS中的Key）
        self.ext_fields: Dict[str, Any] = {}
        for key, value in kwargs.items():
            if key in self.OPTIONAL_KEYS:
                self.ext_fields[key] = value
            else:
                raise ValueError(
                    f"不支持的扩展字段：{key}（仅支持：{self.OPTIONAL_KEYS}）"
                )

    def _validate_core_fields(
        self, uid: int, title: str, category: str, is_valid: bool
    ):
        """核心字段校验"""
        # 校验uid类型
        if not isinstance(uid, int):
            raise TypeError(f"uid必须为整数，当前类型：{type(uid)}")
        # 校验title非空
        if not isinstance(title, str) or len(title.strip()) == 0:
            raise ValueError("title必须为非空字符串")
        # 校验category预定义值
        allowed_categories = ["demo", "prod", "test"]
        if category not in allowed_categories:
            raise ValueError(
                f"category必须为{allowed_categories}之一，当前值：{category}"
            )
        # 校验is_valid类型
        if not isinstance(is_valid, bool):
            raise TypeError(f"is_valid必须为布尔值，当前类型：{type(is_valid)}")

    def to_dict(self, include_optional: bool = True) -> Dict[str, Any]:
        """转换为字典（保证核心Key顺序，可选字段附加在后）"""
        # 核心字段按固定顺序构造
        core_dict = {key: getattr(self, key) for key in self.CORE_KEYS}
        # 时间戳转换为字符串（便于JSON序列化）
        core_dict["timestamp"] = core_dict["timestamp"].strftime("%Y-%m-%d %H:%M:%S")

        # 附加可选字段（如果需要）
        if include_optional:
            core_dict.update(self.ext_fields)

        return core_dict

    def to_json(self, indent: int = 4, ensure_ascii: bool = False) -> str:
        """转换为JSON字符串（保证Key顺序）"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=ensure_ascii)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StrictJSONStructure":
        """从字典反序列化（带校验）"""
        # 提取核心字段
        core_data = {key: data[key] for key in cls.CORE_KEYS if key in data}
        # 时间戳字符串转datetime
        if "timestamp" in core_data and isinstance(core_data["timestamp"], str):
            core_data["timestamp"] = datetime.strptime(
                core_data["timestamp"], "%Y-%m-%d %H:%M:%S"
            )
        # 提取可选字段
        optional_data = {key: data[key] for key in cls.OPTIONAL_KEYS if key in data}
        # 创建实例
        return cls(**core_data, **optional_data)


# ------------------- 进阶版测试 -------------------
if __name__ == "__main__":
    # 1. 创建带扩展字段的实例
    try:
        json_struct = StrictJSONStructure(
            uid=1002,
            title="进阶测试",
            category="prod",
            is_valid=True,
            ext_data={"info": "test"},
            tags=["python", "json"],
            operator="admin",
        )

        # 2. 转换为JSON（核心Key顺序固定，扩展字段附加在后）
        json_str = json_struct.to_json()
        print("进阶版JSON输出：")
        print(json_str)

        # 3. 反序列化
        data_dict = json.loads(json_str)
        new_struct = StrictJSONStructure.from_dict(data_dict)
        print(f"\n反序列化后 - uid: {new_struct.uid}, category: {new_struct.category}")

    except ValueError as e:
        print(f"初始化失败：{e}")
