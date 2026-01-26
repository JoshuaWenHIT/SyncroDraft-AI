import os
import platform
import datetime
import socket
import struct
import binascii
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad  # 补充AES解填充依赖


# 补齐AES密钥/IV到16字节（AES-128），可根据实际需求调整
def pad_key_iv(data, length=16):
    """补齐密钥/IV到指定长度（默认16字节）"""
    if len(data) < length:
        return data.ljust(length, '\0').encode('utf-8')
    return data[:length].encode('utf-8')


def get_time(flag=0):
    datetimenow = datetime.datetime.now()
    date = datetimenow.date().isoformat()
    time = datetimenow.time().strftime('%H-%M-%S-%f')

    if flag == 0:
        return date + "-" + time
    if flag == 1:
        return date
    if flag == 2:
        return time


class Get_License(object):
    def __init__(self):
        super(Get_License, self).__init__()

        self.seperateKey = "JoshuaWen"
        # 修复：补齐AES密钥和IV到16字节（AES-128要求）
        self.aesKey = pad_key_iv("hitict")
        self.aesIv = pad_key_iv("20260116")
        self.aesMode = AES.MODE_CBC

    def getHwAddr(self, ifname=None):
        """
        获取主机物理地址（MAC），自动适配系统和网卡
        """
        try:
            if platform.system() == 'Linux':
                if not ifname:
                    # 优先尝试常见网卡名，可根据实际环境调整
                    ifnames = ['eno1', 'wlp4s0', 'eth0', 'wlan0']
                else:
                    ifnames = [ifname]

                import fcntl
                for name in ifnames:
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        info = fcntl.ioctl(s.fileno(), 0x8927, struct.pack('256s', bytes(name[:15], 'utf-8')))
                        mac = ''.join(['%02x' % char for char in info[18:24]])
                        return mac.lower()  # 统一转为小写，避免大小写不匹配
                    except IOError:
                        continue
                raise IOError("No valid network interface found")

            elif platform.system() == 'Windows':
                import uuid
                # 获取MAC地址并转为小写十六进制，去掉多余前缀
                mac = hex(uuid.getnode())[2:].zfill(12).lower()
                return mac

            else:
                raise NotImplementedError("Unsupported OS")

        except Exception as e:
            print(f"Failed to get MAC address: {e}")
            return ""

    def decrypt(self, hex_text):
        """
        AES解密（CBC模式）
        :param hex_text: 十六进制字符串（加密后的内容）
        :return: 解密后的明文（bytes），失败返回空bytes
        """
        try:
            # 验证输入是否为有效十六进制字符串
            if not isinstance(hex_text, str):
                hex_text = hex_text.decode('utf-8', errors='ignore')

            # 十六进制字符串转字节
            cipher_data = binascii.unhexlify(hex_text.strip())

            # 创建AES解密器（CBC模式需要解填充）
            cryptor = AES.new(self.aesKey, self.aesMode, self.aesIv)
            # 解密并去除PKCS7填充
            plain_data = unpad(cryptor.decrypt(cipher_data), AES.block_size)

            return plain_data

        except Exception as e:
            print(f"Decryption failed: {e}")
            return b""  # 统一返回bytes类型

    def getLicenseInfo(self, filePath=None):
        """
        验证授权文件
        :param filePath: 授权文件路径
        :return: (是否有效, 授权信息)
        """
        # 默认授权文件路径：当前脚本的上一级目录
        if filePath is None:
            # 更稳妥的上一级路径写法（兼容不同系统）
            current_script_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_script_dir)
            filePath = os.path.join(parent_dir, "license.lic")

        # 检查文件是否存在
        if not os.path.isfile(filePath):
            print(f"授权文件不存在：{filePath}，请将license.lic放在当前脚本的上一级目录下")
            return False, b'Invalid'

        # 读取授权文件内容（十六进制字符串）
        try:
            with open(filePath, "r", encoding='utf-8') as licFile:
                encryptText = licFile.read().strip()  # 读为字符串，避免bytes问题
        except Exception as e:
            print(f"Failed to read license file: {e}")
            return False, b'Invalid'

        # 获取本机MAC地址
        host_mac = self.getHwAddr()
        if not host_mac:
            return False, b'Invalid'
        print(f"本机MAC地址：{host_mac}")  # 调试：打印本机MAC

        # 第一步解密授权文件内容（第二层加密的内容）
        decryptText = self.decrypt(encryptText)
        if not decryptText:
            return False, b'Invalid'
        # print(f"第一层解密结果：{decryptText}")  # 调试：打印解密后的拼接字符串

        # 查找分隔符位置（避免decode报错，直接在bytes中查找）
        sep_key_bytes = self.seperateKey.encode('utf-8')
        pos = decryptText.find(sep_key_bytes)
        if pos == -1:
            return False, b'Invalid'

        # 解析授权中的MAC和时间信息（核心修正：去掉多余的binascii.hexlify）
        lic_mac_time_bytes = decryptText[:pos]
        # 错误写法：lic_mac_time = self.decrypt(binascii.hexlify(lic_mac_time_bytes).decode())
        # 正确写法：直接把bytes转字符串（因为这本身就是第一层加密的hex字符串）
        lic_mac_time = self.decrypt(lic_mac_time_bytes.decode())
        if not lic_mac_time:
            return False, b'Invalid'
        # print(f"第二层解密结果（MAC+时间）：{lic_mac_time}")  # 调试：打印MAC+时间

        # 清理授权信息（已去掉rstrip('6')）
        lic_mac_time_str = lic_mac_time.decode('utf-8', errors='ignore')
        lic_parts = lic_mac_time_str.split('-')
        if len(lic_parts) < 4:  # 至少包含MAC-年-月-日
            print(f"授权信息格式错误：{lic_mac_time_str}，需满足MAC-年-月-日")
            return False, b'Invalid'

        # 提取授权MAC和授权时间
        lic_mac = lic_parts[0].strip().lower()
        lic_year, lic_month, lic_day = lic_parts[1], lic_parts[2], lic_parts[3]
        print(f"授权MAC：{lic_mac}，授权时间：{lic_year}-{lic_month}-{lic_day}")  # 调试：打印授权信息

        # 获取当前日期（补零，和授权时间格式对齐）
        now = datetime.datetime.now()
        now_year = str(now.year).zfill(4)
        now_month = str(now.month).zfill(2)
        now_day = str(now.day).zfill(2)
        print(f"当前时间：{now_year}-{now_month}-{now_day}")  # 调试：打印当前时间

        # 验证授权时间（完整的年-月-日判断）
        is_time_valid = False
        if int(now_year) < int(lic_year):
            is_time_valid = True
        elif int(now_year) == int(lic_year):
            if int(now_month) < int(lic_month):
                is_time_valid = True
            elif int(now_month) == int(lic_month):
                if int(now_day) <= int(lic_day):  # 包含当天
                    is_time_valid = True

        # 验证MAC地址和时间
        if is_time_valid and lic_mac == host_mac:
            # 提取授权信息
            licenseStr = decryptText[pos + len(sep_key_bytes):]
            return True, licenseStr
        else:
            print(f"MAC不匹配或授权过期：授权MAC={lic_mac}，本机MAC={host_mac}；时间有效={is_time_valid}")
            return False, b'Invalid'


def lic_match():
    """
    授权验证主函数
    :return: 是否授权成功
    """
    try:
        License = Get_License()
        condition, LicInfo = License.getLicenseInfo()
        if condition and LicInfo == b'Valid':
            print("已授权！")
            return True
        else:
            print('未授权！')
            return False
    except Exception as e:
        print(f"授权验证失败：{e}")
        return False


# 测试调用（仅在直接运行脚本时执行）
if __name__ == "__main__":
    lic_match()