from django.db import models

class TaskLog(models.Model):
    # 任务的唯一标识符
    task_id = models.CharField(max_length=100, unique=True, db_index=True)
    # 任务状态：running, success, error
    status = models.CharField(max_length=20, default='running')
    # 存放所有的日志文本
    log_content = models.TextField(default='') 
    # 创建时间
    created_at = models.DateTimeField(auto_now_add=True)
    # 任务开始和结束时间
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
     # 👇 新增：存储结果 JSON 文件的路径
    result_file_path = models.CharField(max_length=255, null=True, blank=True)
    # 👇 新增：存储图片结果的 JSON 字符串
    result_images = models.TextField(default='{}') 
     # 👇 新增：Excel 文件路径
    excel_file_path = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        app_label = 'drawing_server'

    def __str__(self):
        return f"{self.task_id} - {self.status}"