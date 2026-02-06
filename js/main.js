document.addEventListener('DOMContentLoaded', () => {
    // ===========================
    // 1. 获取 DOM 元素
    // ===========================
    const inputTab = document.getElementById('inputTab');
    const resultTab = document.getElementById('resultTab');
    const finalTab = document.getElementById('finalTab');

    const inputPage = document.getElementById('inputPage');
    const resultPage = document.getElementById('resultPage');
    const finalViewPage = document.getElementById('finalViewPage');

    const fileInput1 = document.getElementById('imgInput1');
    const fileInput2 = document.getElementById('imgInput2');
    const folderInput1 = document.getElementById('folderInput1');
    const folderInput2 = document.getElementById('folderInput2');
    const fileName1 = document.getElementById('fileName1');
    const fileName2 = document.getElementById('fileName2');
    const startBtn = document.getElementById('startBtn');

    let selectedFiles1 = [];
    let selectedFiles2 = [];

    const previewContainer1 = document.createElement('div');
    previewContainer1.className = 'preview-container';
    document.getElementById('previewMount1').appendChild(previewContainer1);

    const previewContainer2 = document.createElement('div');
    previewContainer2.className = 'preview-container';
    document.getElementById('previewMount2').appendChild(previewContainer2);

    const imageViewerModal = createImageViewerModal();
    document.body.appendChild(imageViewerModal);
    
    //修改：创建 Excel Pdf 查看器模态框
    createPdfViewerModal();
    createExcelViewerModal();


    function switchView(targetTab, targetPage) {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        targetTab.classList.add('active');
        targetPage.classList.add('active');
    }

    inputTab.addEventListener('click', () => switchView(inputTab, inputPage));
    resultTab.addEventListener('click', () => switchView(resultTab, resultPage));
    finalTab.addEventListener('click', () => switchView(finalTab, finalViewPage));

    // ===========================
    // 2. 文件选择逻辑 + 大缩略图（300×200）修改：新加入excel和pdf选择逻辑
    // ===========================
    function handleFileSelect(fileList, textElement, previewContainer, folderNameHint = '') {
        previewContainer.innerHTML = '';
        if (!fileList || fileList.length === 0) {
            textElement.textContent = '未选择文件';
            checkBtn();
            return;
        }

        const files = Array.from(fileList);

        const stats = {
            png: files.filter(f => /\.(png|jpg|jpeg|gif)$/i.test(f.name)).length,
            pdf: files.filter(f => /\.pdf$/i.test(f.name)).length,
            excel: files.filter(f => /\.(xls|xlsx)$/i.test(f.name)).length,
            cad: files.filter(f => /\.(dwg|dxf|dwf)$/i.test(f.name)).length
        };

        let summary = folderNameHint ? `文件夹：${folderNameHint} ｜ ` : '';
        summary += `PNG(${stats.png}) PDF(${stats.pdf}) Excel(${stats.excel}) CAD(${stats.cad})`;
        textElement.textContent = summary;

        // 显示放大 PNG 缩略图 + 完整文件名 改加了excel和pdf
        files.filter(f => /\.(png|jpg|jpeg|gif)$/i.test(f.name)).forEach(file => {
            const reader = new FileReader();
            reader.onload = e => {

                const card = document.createElement('div');
                card.style.width = "300px";
                card.style.margin = "15px";
                card.style.display = "flex";
                card.style.flexDirection = "column";
                card.style.alignItems = "center";

                const img = document.createElement('img');
                img.src = e.target.result;
                img.style.width = '300px';
                img.style.height = '200px';
                img.style.objectFit = 'cover';
                img.style.borderRadius = '6px';
                img.style.cursor = 'pointer';

                img.addEventListener('dblclick', () => window.openImageViewer(e.target.result));

                const label = document.createElement('div');
                label.className = 'thumbnail-label';
                label.textContent = file.name;
                label.style.fontSize = "14px";
                label.style.color = "#fff";
                label.style.textAlign = "center";
                label.style.marginTop = "8px";
                label.style.whiteSpace = "normal";
                label.style.wordBreak = "break-all";

                card.appendChild(img);
                card.appendChild(label);
                previewContainer.appendChild(card);
            };
            reader.readAsDataURL(file);});
        files.filter(f => /\.(xls|xlsx)$/i.test(f.name)).forEach(file => {
  const placeholder = createExcelPlaceholder(file);
  previewContainer.appendChild(placeholder);

  placeholder.addEventListener('click', () => {
    window.openExcelViewer(file);
  });
});

        files.filter(f => /\.pdf$/i.test(f.name)).forEach(file => {
    const placeholder = createPdfPlaceholder(file);
    previewContainer.appendChild(placeholder);

    placeholder.addEventListener('click', () => {
      console.log('PDF clicked:', file.name);
      window.openPdfViewer(file);
    });
  });

  checkBtn();
}
    

    // ===========================
    // 3. PNG 查看器（Pointer Events）
    // ===========================
    function createImageViewerModal() {
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.85);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 9999;
        `;

        const img = document.createElement('img');
        img.style.maxWidth = '90vw';
        img.style.maxHeight = '90vh';
        img.style.objectFit = 'contain';
        img.style.cursor = 'grab';
        img.style.userSelect = 'none';
        img.draggable = false;

        let scale = 1;
        let tx = 0, ty = 0;
        let dragging = false;
        let startX = 0, startY = 0;

        function update() {
            img.style.transform = `translate(${tx}px, ${ty}px) scale(${scale})`;
        }

        modal.addEventListener('wheel', e => {
            e.preventDefault();
            scale = Math.max(0.5, Math.min(scale + (e.deltaY > 0 ? -0.1 : 0.1), 3));
            update();
        }, { passive: false });

        img.addEventListener('pointerdown', e => {
            if (e.button !== 0) return;
            e.preventDefault();

            img.setPointerCapture(e.pointerId);
            dragging = true;
            startX = e.clientX - tx;
            startY = e.clientY - ty;
            img.style.cursor = 'grabbing';
        });

        img.addEventListener('pointermove', e => {
            if (!dragging) return;
            tx = e.clientX - startX;
            ty = e.clientY - startY;
            update();
        });

        img.addEventListener('pointerup', e => {
            dragging = false;
            img.releasePointerCapture(e.pointerId);
            img.style.cursor = 'grab';
        });

        modal.addEventListener('mousedown', e => {
            if (e.target === modal) modal.style.display = 'none';
        });

        modal.appendChild(img);

        window.openImageViewer = (src) => {
            img.src = src;
            scale = 1;
            tx = 0;
            ty = 0;
            update();
            modal.style.display = 'flex';
        };

        return modal;
    }

    // ===========================
    // 4. 绑定事件
    // ===========================
    fileInput1.addEventListener('change', () => {
        folderInput1.value = '';
        selectedFiles1 = fileInput1.files;
        handleFileSelect(selectedFiles1, fileName1, previewContainer1);
    });

    fileInput2.addEventListener('change', () => {
        folderInput2.value = '';
        selectedFiles2 = fileInput2.files;
        handleFileSelect(selectedFiles2, fileName2, previewContainer2);
    });

    folderInput1.addEventListener('change', () => {
        fileInput1.value = '';
        selectedFiles1 = folderInput1.files;
        const name = selectedFiles1[0]?.webkitRelativePath?.split('/')[0] || '';
        handleFileSelect(selectedFiles1, fileName1, previewContainer1, name);
    });

    folderInput2.addEventListener('change', () => {
        fileInput2.value = '';
        selectedFiles2 = folderInput2.files;
        const name = selectedFiles2[0]?.webkitRelativePath?.split('/')[0] || '';
        handleFileSelect(selectedFiles2, fileName2, previewContainer2, name);
    });

    function checkBtn() {
        startBtn.disabled = !(selectedFiles1.length && selectedFiles2.length);
    }
    

    startBtn.addEventListener('click', async (e) => {
        // 1. 【关键】阻止按钮的默认提交行为（防止页面刷新）
        e.preventDefault(); 
        
        console.log("按钮被点击，开始处理...");

        // 2. 简单的校验：确保有文件被选中
        if (fileInput1.files.length === 0 && fileInput2.files.length === 0) {
            alert("请先选择文件！");
            return;
        }

        // 👇 重置卡片状态
        ['card-preprocess', 'card-feature', 'card-diff'].forEach(id => {
            const card = document.getElementById(id);
            if (card) card.classList.add('pending'); // 加上蒙版
        });

        // 3. 【优化体验】添加“加载中”状态，防止用户重复点击，并让用户知道正在处理
        const originalBtnText = startBtn.innerText;
        startBtn.innerText = "正在上传分析...";
        startBtn.disabled = true;

        const formData = new FormData();
        const group1Files = fileInput1.files;
        const group2Files = fileInput2.files;

        for (let i = 0; i < group1Files.length; i++) {
            formData.append('files1', group1Files[i]);
        }
        for (let i = 0; i < group2Files.length; i++) {
            formData.append('files2', group2Files[i]);
        }
        
         // 1. 获取所有统计数值的 span
        const statSpans = document.querySelectorAll('.stat-value');
         // 2. 统一改成 "处理中..." 并加个旋转动画效果（可选）
        statSpans.forEach(span => {
            span.innerText = "处理中...";
            span.style.color = "#666"; // 灰色
        });
        
        // 执行跳转
        switchView(resultTab, resultPage); 
        
        try {
            console.log("正在向 Django 发送请求...");
            const response = await fetch('http://127.0.0.1:8000/api/upload/', {
                method: 'POST',
                body: formData
            });

            console.log("服务器 HTTP 状态码:", response.status);

            if (!response.ok) {
                throw new Error(`HTTP 错误! 状态码: ${response.status}`);
            }

            const result = await response.json();
            console.log('Django 返回的数据:', result);

            // 4. 根据后端返回的实际字段进行判断
            // 请确保后端返回的 JSON 确实包含 { status: 'success' }
            if (result.status === 'success') {
                console.log("状态验证通过，准备跳转...");
                const taskId = result.task_id;
            
            // 存入 LocalStorage (为了刷新不消失)
                localStorage.setItem('current_task_id', taskId);
            // 开始轮询日志
                startLogPolling(taskId);
                
            } else {
                console.warn("后端处理未成功:", result);
                alert('上传成功但处理失败: ' + (result.message || '未知错误'));
            }

            //为了演示，这一行先注释掉
        }/* catch (error) {
            console.error('请求过程中发生错误:', error);
            alert('连接服务器失败，请检查控制台日志。');
        }*/ finally {
            // 5. 无论成功还是失败，都恢复按钮状态
            startBtn.innerText = originalBtnText;
            startBtn.disabled = false;
        }
    });


// ===========================
// 5. 中间结果页面交互（恢复：过程检测四个卡片可点击）
// ===========================
const monitorDashboard = document.getElementById('monitorDashboard');
const monitorDetail = document.getElementById('monitorDetail');
const detailTitle = document.getElementById('detailTitle');
const dynamicDirectory = document.getElementById('dynamicDirectory');
const dynamicContent = document.getElementById('dynamicContent');

// --- 核心：修改 openDetail 函数 ---

window.openDetail = function(type) {
    if (monitorDashboard) monitorDashboard.classList.remove('active');
    if (monitorDetail) monitorDetail.classList.add('active');

    let titleText = "";
    let menuHtml = "";
    let contentHtml = "";

    // 辅助函数：生成详情项
    function addItem(id, title, imgUrl, color='#333') {
        menuHtml += `<li><a href="#${id}">${title}</a></li>`;
        
        let previewHtml = '';
        if (imgUrl) {
             previewHtml = `
                <div class="preview-single">
                  <div class="preview-img-box">
                    <img class="fixed-thumb" src="${imgUrl}" alt="${title}" loading="lazy">
                  </div>
                </div>`;
        } else {
             previewHtml = `<div class="text-placeholder">暂无图片数据</div>`;
        }

        contentHtml += `
            <div id="${id}" class="result-item detail-anchor-item">
              <div class="result-title">${title}</div>
              <div class="black-placeholder" style="background-color:${color}; min-height:200px;">
                ${previewHtml}
              </div>
            </div>`;
    }

    // 👇 这里的逻辑变成了：如果有真实数据，就遍历真实数据；否则显示“暂无数据”或保留原来的测试数据
    const images = globalTaskImages || { preprocess: [], feature: [], diff: [] };

    if (type === 'preprocess') {
        titleText = "三视图与截面图 - 详细数据";
        if (images.preprocess && images.preprocess.length > 0) {
            images.preprocess.forEach((img, index) => {
                // img.name 是文件名，img.url 是图片路径
                // ID 使用 pre-index，标题直接用文件名
                addItem(`pre-${index}`, img.name, img.url);
            });
        } else {
            contentHtml = "<div style='padding:20px'>暂无三视图生成结果</div>";
        }

    } else if (type === 'feature') {
        titleText = "箭头识别 - 详细数据";
        if (images.feature && images.feature.length > 0) {
            images.feature.forEach((img, index) => {
                addItem(`feat-${index}`, img.name, img.url, '#444');
            });
        } else {
            contentHtml = "<div style='padding:20px'>暂无箭头识别结果</div>";
        }

    } else if (type === 'diff') {
        titleText = "参数识别 - 详细数据";
        if (images.diff && images.diff.length > 0) {
            images.diff.forEach((img, index) => {
                addItem(`diff-${index}`, img.name, img.url, '#600');
            });
        } else {
            contentHtml = "<div style='padding:20px'>暂无参数识别结果</div>";
        }

    } else if (type === 'table') {
        titleText = "工件参数";
        // 表格数据通常在 statistics JSON 里，或者你需要解析另一个 JSON
        // 这里暂时保持你原来的静态表格，或者留空
        contentHtml += `<div style='padding:20px'>工件参数表格数据请查看统计报表</div>`;
    } else {
        titleText = "详细数据展示";
    }

    if (detailTitle) detailTitle.textContent = titleText;
    if (dynamicDirectory) dynamicDirectory.innerHTML = menuHtml;
    if (dynamicContent) dynamicContent.innerHTML = contentHtml;
};

window.closeDetail = function() {
    if (monitorDetail) monitorDetail.classList.remove('active');
    if (monitorDashboard) monitorDashboard.classList.add('active');
};

// ===========================
// 6. 目录锚点平滑滚动（恢复）
// ===========================
document.addEventListener('click', function(e) {
    if (e.target && e.target.matches('.directory-list a')) {
        e.preventDefault();
        const href = e.target.getAttribute('href');
        if (!href || !href.startsWith('#')) return;

        const targetId = href.substring(1);
        const targetElement = document.getElementById(targetId);
        if (targetElement) {
            targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }
});
});
document.addEventListener('click', (e) => {
  const img = e.target.closest('.preview-img-box img.fixed-thumb');
  if (!img) return;

  const fullSrc = img.dataset.full || img.src;

  // 调用你已经写好的图片查看器
  openImageViewer(fullSrc);
});
document.addEventListener('click', (e) => {
  const img = e.target.closest('.result-view-img');
  if (!img) return;
  window.openImageViewer(img.src);
});

//修改：增添PDF挂载
function renderPDF(file, mountEl) {
  mountEl.innerHTML = '';

  const reader = new FileReader();
  reader.onload = async function () {
    const pdf = await pdfjsLib.getDocument({ data: reader.result }).promise;
    const page = await pdf.getPage(1); // 先只显示第一页

    const scale = 1.2;
    const viewport = page.getViewport({ scale });

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    canvas.width = viewport.width;
    canvas.height = viewport.height;

    await page.render({
      canvasContext: ctx,
      viewport
    }).promise;

    canvas.style.maxWidth = '100%';
    canvas.style.border = '1px solid #ccc';

    mountEl.appendChild(canvas);
  };

  reader.readAsArrayBuffer(file);
}
//修改：增添pdf查看器
function createPdfPlaceholder(file) {
  const box = document.createElement('div');
  box.className = 'pdf-placeholder';

  box.innerHTML = `
    <div class="pdf-icon">📄</div>
    <div class="pdf-name">${file.name}</div>
    <div class="pdf-hint">点击预览</div>
  `;

  return box;
}
//修改：增添封装的「创建 PDF 预览弹窗」的自定义函数
function createPdfViewerModal() {
  const modal = document.createElement('div');
  modal.style.cssText = `
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.85);
    display: none;
    justify-content: center;
    align-items: center;
    z-index: 10000;
  `;

  const container = document.createElement('div');
  container.style.cssText = `
    background: #fff;
    padding: 16px;
    max-width: 90vw;
    max-height: 90vh;
    overflow: auto;
    border-radius: 8px;
  `;

  const canvas = document.createElement('canvas');
  container.appendChild(canvas);
  modal.appendChild(container);

  modal.addEventListener('click', e => {
    if (e.target === modal) modal.style.display = 'none';
  });

  document.body.appendChild(modal);

  // 暴露全局方法
  window.openPdfViewer = async function (file) {
    modal.style.display = 'flex';

    const buffer = await file.arrayBuffer();
    const pdf = await pdfjsLib.getDocument({ data: buffer }).promise;
    const page = await pdf.getPage(1);

    const scale = 1.5;
    const viewport = page.getViewport({ scale });

    const ctx = canvas.getContext('2d');
    canvas.width = viewport.width;
    canvas.height = viewport.height;

    await page.render({
      canvasContext: ctx,
      viewport
    }).promise;
  };
}
//封装的「创建 excel 预览弹窗」的自定义函数
function createExcelPlaceholder(file) {
  const box = document.createElement('div');
  box.className = 'excel-placeholder';

  box.innerHTML = `
    <div class="excel-icon">📊</div>
    <div class="excel-name">${file.name}</div>
    <div class="excel-hint">点击查看表格</div>
  `;

  return box;
}
function createExcelViewerModal() {
  const modal = document.createElement('div');
  modal.style.cssText = `
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.85);
    display: none;
    justify-content: center;
    align-items: center;
    z-index: 10000;
  `;

  const container = document.createElement('div');
  container.style.cssText = `
    background: #f8f8f8;
    padding: 12px;
    max-width: 95vw;
    max-height: 90vh;
    overflow: auto;
    border-radius: 8px;
  `;

  const canvas = document.createElement('canvas');
  canvas.style.background = '#fff';
  canvas.style.borderRadius = '6px';
  canvas.style.boxShadow = '0 8px 30px rgba(0,0,0,0.25)';
  canvas.style.cursor = 'grab';

  container.appendChild(canvas);
  modal.appendChild(container);

  modal.addEventListener('mousedown', e => {
    if (e.target === modal) modal.style.display = 'none';
  });

  document.body.appendChild(modal);

  // ===========================
  // Excel 打开（Canvas 渲染）
  // ===========================
  window.openExcelViewer = async function (file) {
    modal.style.display = 'flex';

    const buffer = await file.arrayBuffer();
    const workbook = XLSX.read(buffer, { type: 'array' });

    const sheetName = workbook.SheetNames[0];
    const sheet = workbook.Sheets[sheetName];

    const range = XLSX.utils.decode_range(sheet['!ref']);
    const cellW = 120;
    const cellH = 28;

    const cols = range.e.c - range.s.c + 1;
    const rows = range.e.r - range.s.r + 1;

    canvas.width = Math.min(cols * cellW, 6000);
    canvas.height = Math.min(rows * cellH, 6000);

    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.font = '14px system-ui, -apple-system, BlinkMacSystemFont';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = '#000';

    // 画网格 + 内容
    for (let r = range.s.r; r <= range.e.r; r++) {
      for (let c = range.s.c; c <= range.e.c; c++) {
        const cellAddr = XLSX.utils.encode_cell({ r, c });
        const cell = sheet[cellAddr];

        const x = (c - range.s.c) * cellW;
        const y = (r - range.s.r) * cellH;

        ctx.strokeStyle = '#ddd';
        ctx.strokeRect(x, y, cellW, cellH);

        if (cell && cell.v != null) {
          ctx.fillText(
            String(cell.v).slice(0, 50),
            x + 6,
            y + cellH / 2
          );
        }
      }

      // 防止大表卡死
      if ((r - range.s.r) % 20 === 0) {
        await new Promise(r => requestAnimationFrame(r));
      }
    }

    // 初始居中
    container.scrollTop = 0;
    container.scrollLeft = 0;
  };
}

// --- 轮询函数 ---
let logTimer = null; // 全局定时器变量
// 全局变量存储图片结果
let globalTaskImages = null; 
function startLogPolling(taskId) {
    const terminal = document.getElementById('terminal-output');
    const timerDisplay = document.getElementById('timer-display'); // 获取时间显示元素
    const statusDisplay = document.getElementById('status-display'); // 获取状态显示元素
    
    // 清除可能存在的旧定时器
    if (logTimer) clearInterval(logTimer);

    logTimer = setInterval(async () => {
        try {
            const res = await fetch(`http://127.0.0.1:8000/api/get_logs/?task_id=${taskId}`);
            const data = await res.json();

            if (data.status === 'success') {
                // 1. 更新日志文字
                terminal.innerText = data.logs;
                // 自动滚动到底部
                terminal.scrollTop = terminal.scrollHeight;

                // 2. 更新运行时间
                if (data.duration) {
                    timerDisplay.innerText = data.duration;
                }

                // 3. 更新状态文字
                statusDisplay.innerText = data.task_status === 'running' ? '正在计算...' : 
                                          (data.task_status === 'success' ? '计算完成' : '出错');

                // 4. 【新增】更新统计数据 (当后端返回 statistics 字段时)
                if (data.statistics) {
                    const stats = data.statistics;
                    
                    // 辅助函数：安全更新 DOM，防止元素不存在报错
                    const updateEl = (id, value, color) => {
                        const el = document.getElementById(id);
                        if (el) {
                            el.innerText = value;
                            if (color) el.style.color = color; // 恢复颜色
                        }
                    };

                    // 对应 compare.py 中的 summary 字段
                    updateEl('stat-total', stats.total_views); 
                    updateEl('stat-diff-views', stats.views_with_diff, 'orange');
                    updateEl('stat-cross-match', stats.cross_view_matched, 'blue');
                    updateEl('stat-final-a', stats.final_a_only_annotations, 'red');
                    updateEl('stat-final-b', stats.final_b_only_annotations, 'red');
                }

                const excelStatusText = document.getElementById('excel-status-text');
                const excelBtn = document.getElementById('btn-open-excel');

                if (data.excel_path) {
                    currentExcelPath = data.excel_path;
                    
                    // 激活状态
                    excelStatusText.innerText = "报表已生成";
                    excelStatusText.style.color = "green";
                    
                    excelBtn.disabled = false;
                    excelBtn.style.backgroundColor = "#28a745"; // 绿色
                    excelBtn.style.cursor = "pointer";
                } else {
                    // 保持等待状态
                    // 只有任务彻底失败了才显示“生成失败”
                    if (data.task_status === 'error') {
                        excelStatusText.innerText = "生成失败";
                        excelStatusText.style.color = "red";
                    }
                }
                
                // 处理图片结果
                if (data.result_images) {
                    console.log("后端返回的 result_images:", data.result_images);
                    globalTaskImages = data.result_images;

                    // 检查 comparison 字段是否存在且有数据
                    if (globalTaskImages.comparison && globalTaskImages.comparison.length > 0) {
                        console.log(`检测到比对结果 ${globalTaskImages.comparison.length} 张，准备调用更新函数...`);
                        updateComparisonResults(globalTaskImages.comparison);
                    } else {
                        console.warn("result_images 中没有 comparison 字段，或者数组为空！");
                    }
                    // 更新中间的仪表盘卡片 (去除蒙版+显示预览)
                    updateDashboardPreviews(globalTaskImages);
                    
                    // 在这里调用一个函数去更新主界面底部的“比对结果”区域
                    updateComparisonResults(globalTaskImages.comparison);
                } else {
                    console.log("本次轮询暂无 result_images 数据");
                }

                // 5. 如果任务结束，停止轮询
                if (data.task_status !== 'running') {
                    clearInterval(logTimer);
                    
                    // 任务结束时，让时间显示变成绿色（成功）或红色（失败）
                    if (timerDisplay) {
                        timerDisplay.style.color = data.task_status === 'success' ? 'green' : 'red';
                    }
                    console.log("任务结束，状态:", data.task_status);
                }
            }
        } catch (e) {
            console.error("获取日志出错", e);
        }
    }, 1000); // 1秒刷新一次
}

// --- 页面加载时自动恢复日志 ---
window.addEventListener('load', () => {
    const savedTaskId = localStorage.getItem('current_task_id');
    if (savedTaskId) {
        // 只有当我们在结果页时才恢复显示，或者你可以自动跳到结果页
        // 这里假设用户手动点到了结果页，或者你想自动恢复：
        if (resultPage.classList.contains('active')) { // 假设你有active类判断显示
             startLogPolling(savedTaskId);
        }
        // 或者简单粗暴一点，不管在哪个Tab，只要有记录就准备好去查
        // 但建议只有在结果页显示时才轮询，避免资源浪费
    }
});

// --- 新增：更新底部“结果查看”区域的函数 ---
function updateComparisonResults(compImages) {
    console.log("updateComparisonResults 函数开始执行", compImages);
    // 1. 获取 DOM 元素
    const directoryList = document.getElementById('comparison-directory-list');
    const bottomPanel = document.getElementById('comparison-result-container');

    // 👇【调试点 4】检查是否找到了 HTML 元素
    console.log(" DOM 元素查找结果:", { 
        directoryList: directoryList, 
        bottomPanel: bottomPanel 
    });

    // 安全检查：如果页面上没这俩元素，就不跑了
    if (!directoryList || !bottomPanel) return;
    
    // 如果没有数据，就不更新，或者显示暂无数据
    if (!compImages || compImages.length === 0) {
        // bottomPanel.innerHTML = '<div style="padding:20px">暂无对比结果</div>';
        return;
    }

    // 2. 清空旧的静态内容 (那些 示例.png)
    directoryList.innerHTML = '';
    bottomPanel.innerHTML = '';

    // 3. 遍历数据生成新内容
    compImages.forEach((img, index) => {
        // 生成一个唯一的锚点 ID
        const uniqueId = `comp-res-${index}`;
        
        // --- A. 更新目录 ---
        const li = document.createElement('li');
        // href 指向下面图片的 ID，实现锚点跳转
        li.innerHTML = `<a href="#${uniqueId}">${index + 1}. ${img.name}</a>`;
        directoryList.appendChild(li);

        // B. 更新图片区域 (右/下侧详情)
        const div = document.createElement('div');
        div.id = uniqueId; // 锚点 ID
        div.className = 'result-item';
        div.innerHTML = `
            <div class="result-title">${index + 1}. ${img.name}</div>
            <div class="black-placeholder img-viewer" style="height: auto; min-height: 200px;">
                <img src="${img.url}" alt="${img.name}" class="result-view-img" style="max-width: 100%; display: block;">
            </div>
        `;
        bottomPanel.appendChild(div);
         // ...
        console.log(`正在生成第 ${index+1} 张图的 HTML: ${img.name}`);
        // ...
    });
    console.log("界面更新完成");
}

// --- 辅助函数：渲染单个卡片的预览网格 ---
function renderSingleGrid(gridId, images) {
    const gridEl = document.getElementById(gridId);
    if (!gridEl) return;

    // 清空旧内容
    gridEl.innerHTML = '';

    if (!images || images.length === 0) {
        gridEl.innerHTML = '<div style="padding:10px; font-size:12px; color:#999;">无数据</div>';
        return;
    }

    // 逻辑：如果数量 >= 4，只显示前3个 + 一个"..."
    // 否则显示全部
    const showCount = images.length >= 4 ? 3 : images.length;
    
    // 1. 渲染图片
    for (let i = 0; i < showCount; i++) {
        const img = images[i];
        const div = document.createElement('div');
        div.className = 'preview-img-box';
        div.innerHTML = `
            <div class="img-viewer">
                <img src="${img.url}" alt="${img.name}" class="view-img" loading="lazy">
            </div>
        `;
        gridEl.appendChild(div);
    }

    // 2. 如果超过或等于4个，添加省略号块
    if (images.length >= 4) {
        const moreDiv = document.createElement('div');
        moreDiv.className = 'preview-more';
        moreDiv.innerText = '...';
        // 可选：鼠标悬停显示 "共X张"
        moreDiv.title = `共 ${images.length} 张`;
        gridEl.appendChild(moreDiv);
    }
}

// --- 主函数：更新整个仪表盘 (去除蒙版 + 更新图片) ---
function updateDashboardPreviews(taskImages) {
    // 1. 定义映射关系: 后端字段 -> 前端ID
    const mapping = [
        { key: 'preprocess', cardId: 'card-preprocess', gridId: 'grid-preprocess' },
        { key: 'feature',    cardId: 'card-feature',    gridId: 'grid-feature' },
        { key: 'diff',       cardId: 'card-diff',       gridId: 'grid-diff' }
    ];

    mapping.forEach(item => {
        // A. 去除蒙版
        const card = document.getElementById(item.cardId);
        if (card) {
            card.classList.remove('pending'); // 移除蒙版类
        }

        // B. 更新内容
        const images = taskImages[item.key] || []; // 获取对应数组
        renderSingleGrid(item.gridId, images);
    });
}

// 全局变量记录当前是否有 Excel
let currentExcelPath = null;

// 1. 给按钮绑定点击事件 (放在外面，页面加载时执行一次即可)
const excelBtn = document.getElementById('btn-open-excel');
excelBtn.addEventListener('click', async () => {
    // 获取当前 taskId (从 LocalStorage 或全局变量拿)
    const taskId = localStorage.getItem('current_task_id'); 
    
    if (!taskId || excelBtn.disabled) return;

    try {
        excelBtn.innerText = "正在打开...";
        // 请求后端打开文件
        const res = await fetch(`http://127.0.0.1:8000/api/open_excel/?task_id=${taskId}`);
        const data = await res.json();
        
        if (data.status === 'success') {
            excelBtn.innerText = "已打开";
            setTimeout(() => excelBtn.innerText = "打开 Excel 报表", 2000);
        } else {
            alert("打开失败: " + data.message);
            excelBtn.innerText = "打开 Excel 报表";
        }
    } catch (e) {
        console.error(e);
        alert("请求发送失败");
    }
});