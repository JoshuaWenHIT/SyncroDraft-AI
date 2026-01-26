from openpyxl import load_workbook
from openpyxl.drawing.image import Image
from PIL import Image as PILImage, ImageDraw, ImageFont
import os
import platform

def create_watermark_image(text="HIT-ICT", width=1000, height=800,
                          font_size=200, angle=-30):
    # 主背景图
    img = PILImage.new('RGBA', (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # ========== 核心修改1：适配不同系统的字体加载，确保字体生效 ==========
    # 定义字体路径备选列表（解决arial.ttf不存在的问题）
    font_paths = []
    if platform.system() == "Windows":
        font_paths = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/simhei.ttf",  # 黑体（兼容中文）
            "C:/Windows/Fonts/simsun.ttc"   # 宋体
        ]
    elif platform.system() == "macOS":
        font_paths = [
            "/Library/Fonts/Arial.ttf",
            "/Library/Fonts/SimHei.ttf",
            "/System/Library/Fonts/PingFang.ttc"
        ]
    else:  # Linux
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
        ]

    # 加载字体（优先备选列表，失败则用默认）
    font = None
    for font_path in font_paths:
        try:
            font = ImageFont.truetype(font_path, font_size)
            break
        except:
            continue
    if font is None:
        font = ImageFont.load_default(size=font_size)  # 明确指定默认字体大小

    # 步骤1：获取文字的真实尺寸（带安全边距）
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # 步骤2：增加上下左右 padding（防止裁剪）
    padding = 300  # 可根据 font_size 调整，比如 font_size // 3
    padded_width = text_width + padding * 2
    padded_height = text_height + padding * 2

    # 步骤3：创建更大的文字图像
    text_img = PILImage.new('RGBA', (padded_width, padded_height), (255, 255, 255, 0))
    text_draw = ImageDraw.Draw(text_img)

    # 步骤4：将文字绘制在 (padding, padding) 位置，确保完整显示
    text_draw.text((padding, padding), text, fill=(204, 204, 204, 100), font=font)

    # 旋转（填充色设为白色，避免黑边）
    rotated_text = text_img.rotate(angle, expand=True)

    # 居中粘贴到主图
    pos = ((width - rotated_text.width) // 2, (height - rotated_text.height) // 2)
    img.paste(rotated_text, pos)

    temp_path = "watermark_temp.png"
    img.save(temp_path)
    return temp_path

def add_watermark_to_excel(excel_path, watermark_text="CONFIDENTIAL", output_path=None):
    if output_path is None:
        base, ext = os.path.splitext(excel_path)
        output_path = f"{base}_watermarked{ext}"

    # 生成水印图片
    watermark_img_path = create_watermark_image(text=watermark_text)

    # 加载 Excel 文件
    wb = load_workbook(excel_path)
    
    # 在 add_watermark_to_excel 函数中，保存前加：
    for sheet in wb.worksheets:
        img = Image(watermark_img_path)
        img.anchor = 'A1'
        sheet.add_image(img)
        
        # 保护工作表，禁止删除对象
        sheet.protection.set_password("123456")  # 可选密码
        sheet.protection.objects = True   # 锁定所有对象（包括图片）
        sheet.protection.sheet = True     # 锁定工作表结构

    # 保存
    wb.save(output_path)
    print(f"水印已添加，保存为: {output_path}")

    # 清理临时文件
    os.remove(watermark_img_path)


if __name__ == "__main__":
    add_watermark_to_excel("/home/lab1523-4090/JoshuaWen/Code/Drawing-Comparison/test_process/final_results/740601001_sd_merged_X-Y-Z.xlsx", watermark_text="HIT-ICT")