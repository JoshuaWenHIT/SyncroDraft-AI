from utils.demo_element_tools import recognize_element

import re

def normalize_text(raw_text: str) -> str:
    """
    输入：原始文本
    输出：修正后的内容
    """
    text = raw_text
    # ---------- 结构修复 1：LaTeX 分式 $\frac{A}{B}$ ----------
    def repl_frac(m):
        top = m.group(1).strip()
        bottom = m.group(2).strip()
        return f"{top}\n{bottom}"

    text = re.sub(
        r"\$?\s*\\frac\{([^{}]+)\}\{([^{}]+)\}\s*\$?",
        repl_frac,
        text
    )

    # ---------- 结构修复 2：数值 + 下划线 + 说明 ----------
    text = re.sub(
        r"""
        (?m)                              # 多行模式
        ^\s*(\d+(?:\.\d+)?)\s*            # 行首数值
        _{2,}\s*$                         # 2个及以上下划线到行尾
        \n\s*([^\n]+?)\s*$                # 下一行任意非空文本
        """,
        r"\1\n\2",
        text,
        flags=re.VERBOSE
    )

    # ---------- 规则 5：上下公差 ----------
    def repl_allowance(m):
        base = m.group(1)
        down = m.group(2)
        up = m.group(3)
        return f"{base}</allow-up>[+{up}]\n</allow-down>[-{down}]"

    text = re.sub(
        r"\$?\s*(\d+(?:\.\d+)?)_\{-([\d.]+)\}\^\{\+([\d.]+)\}\s*\$?",
        repl_allowance,
        text
    )

    def repl_allowance_2line(m):
        base = m.group(1)
        up = m.group(2)
        down = m.group(3)
        return f"{base}</allow-up>[+{up}]\n</allow-down>[-{down}]"

    text = re.sub(
        r"""
        (?m)
        ^\s*(\d+(?:\.\d+)?)\s*            # base
        \+(\d+(?:\.\d+)?)\s*$             # 上公差（同一行）
        \n\s*-\s*(\d+(?:\.\d+)?)\s*$      # 下公差（下一行）
        """,
        repl_allowance_2line,
        text,
        flags=re.VERBOSE
    )

    # ---------- 规则 2：A ±0.15 ----------
    text = re.sub(
        r"([A-Za-z0-9]+)\s*±\s*([\d.]+)",
        r"\1</allow>[±\2]",
        text
    )

    # ---------- 规则 1：[Z] / (Z) → Z ----------
    text = re.sub(r"[\[\(]([^\[\]\(\)]+)[\]\)]", r"\1", text)

    lines = text.splitlines()
    out = []

    # ---------- FCF 特例：位置符 + 直径（无 bases） ----------
    # ---------- FCF 特例：位置符 + 直径（无 bases，增强版） ----------
    leftrightarrow_pat = re.compile(
        r"""
        ^\s*
        (?:
            \$\\Leftrightarrow\$ |
            \\Leftrightarrow     |
            ⇔                    |
            →                    |
            \$?\\rightarrow\$?
        )
        \s*
        (?:
            <Diam>\s*(?P<diam1>[\d.]+) |
            [ØøÓ]\s*(?P<diam2>[\d.]+)  |
            (?P<diam3>[\d.]+)
        )
        \s*$
        """,
        re.VERBOSE
    )

    # FCF 单行匹配：
    # - 直径入口：Ø / ø / <Diam>
    # - M/(M)：可选，但要捕获是否存在
    fcf_pat = re.compile(
        r"""
        ^.*?
        (?:
            [ØøÓ]\s*          # 新增 Ó
            |
            <Diam>\s*
        )
        (?P<diam>[\d.]+)
        \s*
        (?P<mflag>           # M 的多种形式
            \(?M\)?           # M / (M)
            |
            \^\{\s*1\s*\}     # ^{1}
        )?
        \s*
        (?P<bases>[XYZ](?:\s+[XYZ])*)
        \s*\$?\s*$
        """,
        re.VERBOSE
    )

    for line in lines:
        m_lr = leftrightarrow_pat.match(line)
        if m_lr:
            diam = (
                    m_lr.group("diam1")
                    or m_lr.group("diam2")
                    or m_lr.group("diam3")
            )

            out.append("<FCF-Position>")
            out.append(f"</FCF-index>[<Diam>{diam}]")
            continue

        m = fcf_pat.match(line)
        if m:
            diam = m.group("diam")
            mflag = m.group("mflag")
            bases = m.group("bases").split()

            out.append("<FCF-Position>")

            # 是否保留 M
            if mflag:
                out.append(f"</FCF-index>[<Diam>{diam}M]")
            else:
                out.append(f"</FCF-index>[<Diam>{diam}]")

            for b in bases:
                if b in {"X", "Y", "Z"}:
                    out.append(f"</FCF-base>[{b}]")
            continue

        # 非 FCF 行：普通 Ø / ø
        line = re.sub(r"[Øø]\s*([\d.]+)", r"<Diam>\1", line)
        out.append(line)

    text = "\n".join(out)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def process_image_content(image_path, element_type="text", save_dir=None, ocr_model=None):
    """处理图像内容并提取文本

    Args:
        image_path (str): 图像文件路径
        element_type (str): 元素类型 ("text", "table", "formula", "code")
        save_dir (str): 结果保存目录（可选）

    Returns:
        str: 提取的文本内容
    """
    try:
        # 调用recognize_element函数处理图像
        result_text, recognition_result = recognize_element(
            image_path=image_path,
            element_type=element_type,
            save_dir=save_dir,
            ocr_model=ocr_model
        )

        result_text = result_text.replace('[', '').replace(']', '')

        result_text = normalize_text(result_text)

        # 返回识别的文本内容
        return result_text

    except Exception as e:
        print(f"处理图像时出错: {e}")
        return None

# 使用示例
if __name__ == "__main__":
    # 示例1: 处理文本图像
    image_path = r"C:\Users\Administrator\Desktop\CAD\hw-hit\suguguai\images_data\segment_data\arrow_det\arrow_det_output\cropped_objects\736420000_sd_view_1_a_base_0000.jpg"
    text_content = process_image_content(image_path, element_type="text")
    if text_content:
        print("提取的文本内容:")
        print(text_content)
    
