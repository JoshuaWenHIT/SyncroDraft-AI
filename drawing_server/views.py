import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
# 确保你的脚本路径在 sys.path 中或者在同一个包下
import drawing_comparison 
import threading
import uuid
import datetime
from .models import TaskLog  # 引入Model
from . import log_utils
from django.utils import timezone 
import json
import glob
# from . import drawing_comparison # 确保引入了你的业务模块

# 1. 辅助函数：把秒数转成 "MM:SS" 格式
def format_duration(seconds):
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"

# 扫描函数：根据两个输入文件扫描所有结果
def scan_results(args):
    """
    根据 args 中的两个输入路径，扫描四个结果文件夹。
    """
    base_dir = "./test_process"
    
    # 👇【核心修复 1】指定 Django 的完整地址 (端口 8000)
    # 这样前端在 5500 端口也能访问到 8000 的图片
    django_host = "http://127.0.0.1:8000"
    media_prefix = "/media"
    
    file1_name = os.path.basename(args.image_path1)
    stem1 = os.path.splitext(file1_name)[0]
    
    file2_name = os.path.basename(args.image_path2)
    stem2 = os.path.splitext(file2_name)[0]
    
    targets = [
        (stem1, file1_name), 
        (stem2, file2_name)
    ]

    results = {
        "preprocess": [], "feature": [], "diff": [], "comparison": [] 
    }

    # 路径转 URL 辅助函数
    def to_url(filepath):
        norm_path = filepath.replace("\\", "/")
        if "./test_process" in norm_path:
            clean_path = norm_path.replace("./test_process", "")
        elif "test_process" in norm_path:
            clean_path = norm_path.split("test_process")[-1]
        else:
            clean_path = norm_path

        if not clean_path.startswith("/"):
            clean_path = "/" + clean_path
            
        # 👇 拼接完整 URL: http://127.0.0.1:8000/media/...
        return f"{django_host}{media_prefix}{clean_path}"

    print(f"DEBUG: 开始扫描，目标地址: {django_host}")

    for stem, original_filename in targets:
        # 1. 三视图 (逻辑不变，文件夹就是 stem)
        view_pattern = os.path.join(base_dir, "views_for_detection", stem, "*.png")
        for filepath in glob.glob(view_pattern):
            results["preprocess"].append({
                "name": os.path.basename(filepath),
                "url": to_url(filepath),
                "source": stem
            })

        # --- 👇【核心修复 2】优化匹配逻辑 ---
        # 你的文件名格式是：[前缀]_page_[数字]
        # 我们需要截取 [前缀]，然后找 [前缀]_view_*
        
        # 尝试通过 "_page_" 分割
        if "_page_" in stem:
            # 例如: 736420000_sd_page_1 -> prefix: 736420000_sd
            prefix = stem.split("_page_")[0]
            # 构造新匹配模式: 736420000_sd_view_*.png (匹配 view_1, view_3, view_4 等所有)
            search_pattern_str = f"{prefix}_view_*.png"
        else:
            # 兜底逻辑：如果名字里没有 page，直接用 stem 试试
            search_pattern_str = f"{stem}*.png"

        print(f"DEBUG: [箭头/参数] 原名: {stem}, 搜索模式: {search_pattern_str}")

        # 2. 箭头识别
        arrow_pattern = os.path.join(base_dir, "std_detection", search_pattern_str)
        found_arrows = glob.glob(arrow_pattern)
        print(f"   -> 箭头找到: {len(found_arrows)} 张")
        
        for filepath in found_arrows:
            results["feature"].append({
                "name": os.path.basename(filepath),
                "url": to_url(filepath),
                "source": stem
            })

        # 3. 参数识别
        obb_pattern = os.path.join(base_dir, "obb_detection", search_pattern_str)
        found_obbs = glob.glob(obb_pattern)
        print(f"   -> 参数找到: {len(found_obbs)} 张")
        
        for filepath in found_obbs:
            results["diff"].append({
                "name": os.path.basename(filepath),
                "url": to_url(filepath),
                "source": stem
            })

        # 4. 比对结果
        # 先找完全匹配原名的
        comp_path = os.path.join(base_dir, "annotated_images", original_filename)
        if os.path.exists(comp_path):
            results["comparison"].append({
                "name": original_filename,
                "url": to_url(comp_path),
                "source": stem
            })
        else:
            # 👇【新增】如果找不到原名，试着找带 _merged 后缀的
            # 很多时候业务代码会生成 xxx_merged.png
            print(f"DEBUG: 原名比对图未找到，尝试模糊搜索...")
            fallback_pattern = os.path.join(base_dir, "annotated_images", f"{stem}*.png")
            found_comps = glob.glob(fallback_pattern)
            for fp in found_comps:
                results["comparison"].append({
                    "name": os.path.basename(fp),
                    "url": to_url(fp),
                    "source": stem
                })

    return results

# --- 辅助函数：这是真正跑在后台线程里的逻辑 ---
def _run_task_background(task_id, args):
    try:
        # 定义一个回调函数，传给 drawing_comparison 用
        def db_logger_callback(msg):
            # 获取当前时间
            time_str = datetime.datetime.now().strftime("[%H:%M:%S] ")
            full_msg = time_str + str(msg) + "\n"
            
            # 打印到控制台（方便开发调试）
            print(full_msg.strip())
            
            # 写入数据库
            try:
                # 重新查询对象，避免多线程对象过期
                task = TaskLog.objects.get(task_id=task_id)
                task.log_content += full_msg
                task.save()
            except Exception:
                pass # 忽略写库失败，防止崩坏业务

        # 【关键步骤】初始化全局 Logger
        # 把“对讲机”放进当前线程的口袋里
        log_utils.init_logger(db_logger_callback)

        # 获取文件名 (demo.png)
        filename_with_ext = os.path.basename(args.image_path1)
        # 去掉后缀 (demo)
        filename_no_ext = os.path.splitext(filename_with_ext)[0]
        
        # 构建目标文件夹
        output_dir = "./drawing_server/source/report_json"
        os.makedirs(output_dir, exist_ok=True) # 确保文件夹存在
        
        # 拼接最终报告路径: ./drawing_server/source/report_json/demo_report.json
        report_path = os.path.join(output_dir, f"{filename_no_ext}_report.json")

        # 3. 存入数据库 (让 api_get_logs 以后能找到它)
        task = TaskLog.objects.get(task_id=task_id)
        task.result_file_path = report_path
        task.start_time = timezone.now()
        task.save()

        # 4. 把路径挂载到 args 上，准备传给业务逻辑
        args.output_file = report_path 

        # 👇【关键】任务开始前，记录 start_time
        # 注意：这里重新获取一次对象，防止并发问题
        task = TaskLog.objects.get(task_id=task_id)
        task.start_time = timezone.now()
        task.save()

        # 1. 计算 Excel 路径 (复用你提供的逻辑)
        # ./data/image_data/736420000_sd_page_1.png -> 736420000_sd
        file1_name = os.path.basename(args.image_path1)
        image_prefix = file1_name.split("_")[0] + "_sd"
        
        # 构建最终路径: ./test_process/final_results/xxx_merged.xlsx
        excel_path = os.path.join("./test_process/final_results", f"{image_prefix}_merged.xlsx")

        # 执行业务逻辑
        # 现在不需要传 logger 参数了！
        drawing_comparison.run_compare_logic(args)
         # 👇【修改】调用扫描函数 (传入 args 即可，里面有两个路径)
        scan_data = scan_results(args)

        # 任务成功，标记状态
        task = TaskLog.objects.get(task_id=task_id)
        task.status = 'success'
        task.result_images = json.dumps(scan_data) # 存入 JSON
        # 👇 存入 Excel 路径
        task.excel_file_path = excel_path 
        task.save()

    except Exception as e:
        # 任务失败，记录错误
        task = TaskLog.objects.get(task_id=task_id)
        task.end_time = timezone.now() # 出错也要记录结束时间
        task.log_content += f"\n[ERROR] 发生异常: {str(e)}\n"
        task.status = 'error'
        task.save()
# 定义一个模拟 args 的类
class MockArgs:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

@csrf_exempt
def api_start_comparison(request):
    if request.method == 'POST':
        # 1. 假设前端传来的文件名
        file1 = request.FILES.get('files1')
        file2 = request.FILES.get('files2')
        
        # 2. 保存文件到 ./data/image_data/
        save_dir = "./data/image_data"
        os.makedirs(save_dir, exist_ok=True)
        
        path1 = os.path.join(save_dir, file1.name)
        path2 = os.path.join(save_dir, file2.name)
        
        with open(path1, 'wb+') as f:
            for chunk in file1.chunks(): f.write(chunk)
        with open(path2, 'wb+') as f:
            for chunk in file2.chunks(): f.write(chunk)

        # 3. 构造 MockArgs 传递给模型
        # 这里你可以设置默认值，也可以从 request.POST 获取前端传来的阈值
        args = MockArgs(
            image_path1=path1,
            image_path2=path2,
            output_dir="./test_process",
            batch_predict=1,
            alignment_threshold=0.05,
            similarity_threshold=0.9
        )
        # 4. 生成 Task ID
        task_id = str(uuid.uuid4())

        # 5. 先并在数据库占位
        TaskLog.objects.create(task_id=task_id)

        # 6. 启动后台线程 (必须用线程，否则前端无法轮询)
        t = threading.Thread(target=_run_task_background, args=(task_id, args))
        t.start()

        # 7. 立即返回 task_id 给前端
        return JsonResponse({
            'status': 'success', 
            'message': '任务已启动', 
            'task_id': task_id
        })
    
    return JsonResponse({'status': 'error'})

# --- 前端轮询获取日志 ---
def api_get_logs(request):
    task_id = request.GET.get('task_id')
    try:
        task = TaskLog.objects.get(task_id=task_id)
         # 计算运行时长
        duration_str = "00:00"
        
        if task.start_time:
            # 确定结束点：如果任务完了就用 end_time，还在跑就用当前时间
            end_point = task.end_time if task.end_time else timezone.now()
            # 计算时间差 (秒)
            delta = (end_point - task.start_time).total_seconds()
            duration_str = format_duration(delta)
        
        response_data = {
            'status': 'success',
            'task_status': task.status,
            'logs': task.log_content,
            'duration': duration_str,
            'statistics': None, # 默认为空
            'result_images': None,
            'excel_path': task.excel_file_path, # 把路径传给前端 (虽然前端打不开，但可以用来判断是否生成成功)
        }

         # 👇【新增】如果任务成功，读取 JSON 文件中的 summary
        if task.status == 'success' and task.result_file_path:
            try:
                if os.path.exists(task.result_file_path):
                    with open(task.result_file_path, 'r', encoding='utf-8') as f:
                        report_data = json.load(f)
                        # 只取 summary 部分传给前端，减少流量
                        response_data['statistics'] = report_data.get('summary')
            except Exception as e:
                print(f"读取结果文件失败: {e}")
        
         # 👇【新增2】关键！从数据库读取图片 JSON 并放入响应中
            if task.result_images:
                try:
                    response_data['result_images'] = json.loads(task.result_images)
                except Exception as e:
                    print(f"解析图片JSON失败: {e}")

        return JsonResponse(response_data)

    
    except TaskLog.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': '任务不存在'})

# 3. 👇【新增】打开 Excel 的接口
def api_open_excel(request):
    task_id = request.GET.get('task_id')
    try:
        task = TaskLog.objects.get(task_id=task_id)
        if task.excel_file_path and os.path.exists(task.excel_file_path):
            # 获取绝对路径
            abs_path = os.path.abspath(task.excel_file_path)
            
            # Windows 系统调用默认软件打开
            # 注意：这会在服务器端（也就是演示电脑上）打开
            os.startfile(abs_path) 
            
            return JsonResponse({'status': 'success', 'message': '已在服务器端打开 Excel'})
        else:
            return JsonResponse({'status': 'error', 'message': '文件尚未生成或不存在'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})