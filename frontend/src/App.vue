<template>
  <div class="tc-page">
    <header class="tc-header">
      <div>
        <div class="tc-title">Tiny Craft 编辑器</div>
        <div class="tc-subtitle">
          本地优先编辑，仅将文件发送至 API 服务端。
        </div>
      </div>
      <el-tag type="info">MVP</el-tag>
    </header>

    <el-tabs v-model="activeTab" type="card" class="tc-card">
      <el-tab-pane name="image" label="图片编辑">
        <div class="tc-grid">
          <div>
            <el-form label-position="top">
              <el-form-item label="选择图片">
                <div class="tc-actions">
                  <el-button @click="pickImageFile">选择图片</el-button>
                  <el-button @click="triggerImageInput" plain>
                    浏览
                  </el-button>
                  <input
                    ref="imageInputRef"
                    type="file"
                    accept="image/*"
                    class="tc-hidden"
                    @change="onImageFileChange"
                  />
                </div>
                <div class="tc-meta" v-if="image.fileName">
                  {{ image.fileName }}
                </div>
              </el-form-item>

              <el-form-item label="参考图（可选）">
                <div class="tc-actions">
                  <el-button @click="pickReferenceFiles">添加参考图</el-button>
                  <el-button @click="triggerReferenceInput" plain>
                    浏览
                  </el-button>
                  <el-button
                    v-if="image.references.length"
                    plain
                    type="danger"
                    @click="clearReferences"
                  >
                    清空
                  </el-button>
                  <input
                    ref="referenceInputRef"
                    type="file"
                    accept="image/*"
                    multiple
                    class="tc-hidden"
                    @change="onReferenceFileChange"
                  />
                </div>
                <div v-if="image.references.length" class="tc-reference-list">
                  <div
                    v-for="(item, index) in image.references"
                    :key="`${item.name}-${index}`"
                    class="tc-reference-item"
                  >
                    <img :src="item.url" class="tc-reference-thumb" />
                    <div class="tc-reference-label">{{ item.name }}</div>
                    <el-button size="small" @click="removeReference(index)">
                      移除
                    </el-button>
                  </div>
                </div>
                <div class="tc-meta" v-else>最多可添加多张参考图。</div>
              </el-form-item>

              <el-form-item label="修改描述">
                <el-input
                  v-model="image.description"
                  type="textarea"
                  :rows="4"
                  placeholder="描述需要修改的内容"
                />
              </el-form-item>

              <div class="tc-actions">
                <el-button
                  type="primary"
                  @click="submitImageJob"
                  :loading="image.busy"
                >
                  提交修改
                </el-button>
                <el-button @click="resetImage">重置</el-button>
              </div>
            </el-form>
          </div>

          <div>
            <div class="tc-preview">
              <div class="tc-meta">本地预览（拖拽选择区域）</div>
              <div
                v-if="image.previewUrl"
                ref="imageCanvasRef"
                class="tc-image-canvas"
                @pointerdown="startImageSelection"
                @pointermove="moveImageSelection"
                @pointerup="endImageSelection"
                @pointerleave="endImageSelection"
              >
                <img
                  ref="imagePreviewRef"
                  :src="image.previewUrl"
                  class="tc-image-preview"
                  @load="syncImageRect"
                />
                <div
                  v-if="imageSelection.width > 0 && imageSelection.height > 0"
                  class="tc-selection"
                  :style="selectionStyle"
                ></div>
              </div>
              <div v-else class="tc-meta">尚未选择图片。</div>
              <div class="tc-meta" v-if="image.previewUrl">
                选区：x={{ selectionSummary.x }} y={{ selectionSummary.y }}
                w={{ selectionSummary.width }} h={{ selectionSummary.height }}
              </div>
              <el-button
                v-if="image.previewUrl"
                size="small"
                style="margin-top: 8px;"
                @click="clearImageSelection"
              >
                清除选区
              </el-button>
            </div>
            <div v-if="image.jobId" style="margin-top: 16px;">
              <el-progress :percentage="image.progress" />
              <div class="tc-meta">{{ image.message }}</div>
            </div>
            <div v-if="image.resultUrl" style="margin-top: 16px;">
              <el-button type="success" @click="openUrl(image.resultUrl)">
                打开结果
              </el-button>
              <el-button @click="downloadResult(image.resultUrl, image.fileName)">
                下载
              </el-button>
              <img :src="image.resultUrl" class="tc-image-preview" style="margin-top: 12px;" />
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { computed, reactive, ref, onBeforeUnmount } from 'vue';
import { ElMessage } from 'element-plus';

const activeTab = ref('image');
const textInputRef = ref(null);
const imageInputRef = ref(null);
const referenceInputRef = ref(null);
const textAreaRef = ref(null);
const imagePreviewRef = ref(null);
const imageCanvasRef = ref(null);

const text = reactive({
  file: null,
  fileName: '',
  content: '',
  regionStart: 0,
  regionEnd: 0,
  description: '',
  jobId: '',
  progress: 0,
  message: '',
  resultUrl: '',
  resultContent: '',
  busy: false,
  eventSource: null,
});

const image = reactive({
  file: null,
  fileName: '',
  previewUrl: '',
  description: '',
  displayWidth: 0,
  displayHeight: 0,
  naturalWidth: 0,
  naturalHeight: 0,
  references: [],
  jobId: '',
  progress: 0,
  message: '',
  resultUrl: '',
  busy: false,
  eventSource: null,
});

const imageSelection = reactive({
  x: 0,
  y: 0,
  width: 0,
  height: 0,
  startX: 0,
  startY: 0,
  dragging: false,
  pointerId: null,
});

const selectionStyle = computed(() => ({
  left: `${imageSelection.x}px`,
  top: `${imageSelection.y}px`,
  width: `${imageSelection.width}px`,
  height: `${imageSelection.height}px`,
}));

const selectionSummary = computed(() => ({
  x: Math.round(imageSelection.x),
  y: Math.round(imageSelection.y),
  width: Math.round(imageSelection.width),
  height: Math.round(imageSelection.height),
}));

const triggerTextInput = () => textInputRef.value?.click();
const triggerImageInput = () => imageInputRef.value?.click();
const triggerReferenceInput = () => referenceInputRef.value?.click();

const pickTextFile = async () => {
  if (!window.showOpenFilePicker) {
    triggerTextInput();
    return;
  }
  try {
    const [handle] = await window.showOpenFilePicker({
      types: [
        {
          description: 'Text',
          accept: { 'text/plain': ['.txt', '.md', '.json', '.csv', '.log'] },
        },
      ],
    });
    const file = await handle.getFile();
    await loadTextFile(file);
  } catch (error) {
    if (error?.name !== 'AbortError') {
      ElMessage.error('打开文件失败');
    }
  }
};

const pickImageFile = async () => {
  if (!window.showOpenFilePicker) {
    triggerImageInput();
    return;
  }
  try {
    const [handle] = await window.showOpenFilePicker({
      types: [
        {
          description: 'Images',
          accept: { 'image/*': ['.png', '.jpg', '.jpeg', '.webp'] },
        },
      ],
    });
    const file = await handle.getFile();
    await loadImageFile(file);
  } catch (error) {
    if (error?.name !== 'AbortError') {
      ElMessage.error('打开图片失败');
    }
  }
};

const pickReferenceFiles = async () => {
  if (!window.showOpenFilePicker) {
    triggerReferenceInput();
    return;
  }
  try {
    const handles = await window.showOpenFilePicker({
      multiple: true,
      types: [
        {
          description: 'Images',
          accept: { 'image/*': ['.png', '.jpg', '.jpeg', '.webp'] },
        },
      ],
    });
    const files = [];
    for (const handle of handles) {
      files.push(await handle.getFile());
    }
    await loadReferenceFiles(files);
  } catch (error) {
    if (error?.name !== 'AbortError') {
      ElMessage.error('打开参考图失败');
    }
  }
};

const onTextFileChange = async (event) => {
  const file = event.target.files?.[0];
  if (file) {
    await loadTextFile(file);
  }
  event.target.value = '';
};

const onImageFileChange = async (event) => {
  const file = event.target.files?.[0];
  if (file) {
    await loadImageFile(file);
  }
  event.target.value = '';
};

const onReferenceFileChange = async (event) => {
  const files = Array.from(event.target.files || []);
  if (files.length > 0) {
    await loadReferenceFiles(files);
  }
  event.target.value = '';
};

const loadTextFile = async (file) => {
  text.file = file;
  text.fileName = file.name;
  text.content = await file.text();
  text.resultUrl && URL.revokeObjectURL(text.resultUrl);
  text.resultUrl = '';
  text.resultContent = '';
  text.message = '';
  text.progress = 0;
};

const loadImageFile = async (file) => {
  image.file = file;
  image.fileName = file.name;
  if (image.previewUrl) {
    URL.revokeObjectURL(image.previewUrl);
  }
  image.previewUrl = URL.createObjectURL(file);
  clearImageSelection();
  image.resultUrl && URL.revokeObjectURL(image.resultUrl);
  image.resultUrl = '';
  image.message = '';
  image.progress = 0;
};

const loadReferenceFiles = async (files) => {
  const next = [];
  for (const file of files) {
    if (!file.type.startsWith('image/')) {
      ElMessage.warning(`跳过非图片文件: ${file.name}`);
      continue;
    }
    next.push({
      file,
      name: file.name,
      url: URL.createObjectURL(file),
    });
  }
  image.references = [...image.references, ...next];
};

const removeReference = (index) => {
  const item = image.references[index];
  if (item?.url) {
    URL.revokeObjectURL(item.url);
  }
  image.references.splice(index, 1);
};

const clearReferences = () => {
  for (const item of image.references) {
    if (item?.url) {
      URL.revokeObjectURL(item.url);
    }
  }
  image.references = [];
};

const syncImageRect = () => {
  if (!imagePreviewRef.value) {
    return;
  }
  const rect = imagePreviewRef.value.getBoundingClientRect();
  image.displayWidth = rect.width;
  image.displayHeight = rect.height;
  image.naturalWidth = imagePreviewRef.value.naturalWidth || rect.width;
  image.naturalHeight = imagePreviewRef.value.naturalHeight || rect.height;
};

const toRelativePoint = (event) => {
  if (!imagePreviewRef.value) {
    return { x: 0, y: 0 };
  }
  const rect = imagePreviewRef.value.getBoundingClientRect();
  const x = Math.min(Math.max(0, event.clientX - rect.left), rect.width);
  const y = Math.min(Math.max(0, event.clientY - rect.top), rect.height);
  return { x, y };
};

const startImageSelection = (event) => {
  if (event.button !== 0) {
    return;
  }
  if (!image.previewUrl) {
    return;
  }
  event.preventDefault();
  syncImageRect();
  const { x, y } = toRelativePoint(event);
  imageSelection.startX = x;
  imageSelection.startY = y;
  imageSelection.x = x;
  imageSelection.y = y;
  imageSelection.width = 0;
  imageSelection.height = 0;
  imageSelection.dragging = true;
  imageSelection.pointerId = event.pointerId;
  imageCanvasRef.value?.setPointerCapture?.(event.pointerId);
};

const moveImageSelection = (event) => {
  if (!imageSelection.dragging || imageSelection.pointerId !== event.pointerId) {
    return;
  }
  const { x, y } = toRelativePoint(event);
  imageSelection.x = Math.min(imageSelection.startX, x);
  imageSelection.y = Math.min(imageSelection.startY, y);
  imageSelection.width = Math.abs(x - imageSelection.startX);
  imageSelection.height = Math.abs(y - imageSelection.startY);
};

const endImageSelection = (event) => {
  if (!imageSelection.dragging) {
    return;
  }
  if (event && imageSelection.pointerId !== event.pointerId) {
    return;
  }
  imageSelection.dragging = false;
  if (imageSelection.pointerId !== null) {
    imageCanvasRef.value?.releasePointerCapture?.(imageSelection.pointerId);
  }
  imageSelection.pointerId = null;
};

const clearImageSelection = () => {
  imageSelection.x = 0;
  imageSelection.y = 0;
  imageSelection.width = 0;
  imageSelection.height = 0;
  imageSelection.dragging = false;
  imageSelection.pointerId = null;
};

const captureSelection = () => {
  const textarea = textAreaRef.value;
  if (!textarea) {
    return;
  }
  text.regionStart = textarea.selectionStart ?? 0;
  text.regionEnd = textarea.selectionEnd ?? 0;
};

const applySelection = () => captureSelection();

const resetText = () => {
  text.file = null;
  text.fileName = '';
  text.content = '';
  text.regionStart = 0;
  text.regionEnd = 0;
  text.description = '';
  text.jobId = '';
  text.progress = 0;
  text.message = '';
  text.resultContent = '';
  if (text.resultUrl) {
    URL.revokeObjectURL(text.resultUrl);
  }
  text.resultUrl = '';
};

const resetImage = () => {
  image.file = null;
  image.fileName = '';
  image.description = '';
  image.displayWidth = 0;
  image.displayHeight = 0;
  image.naturalWidth = 0;
  image.naturalHeight = 0;
  image.jobId = '';
  image.progress = 0;
  image.message = '';
  if (image.previewUrl) {
    URL.revokeObjectURL(image.previewUrl);
  }
  if (image.resultUrl) {
    URL.revokeObjectURL(image.resultUrl);
  }
  clearReferences();
  image.previewUrl = '';
  image.resultUrl = '';
  clearImageSelection();
};

const submitTextJob = async () => {
  if (!text.file) {
    ElMessage.warning('请先选择文本文件');
    return;
  }
  if (!text.description) {
    ElMessage.warning('请填写描述内容');
    return;
  }
  text.busy = true;
  const formData = new FormData();
  formData.append('file', text.file);
  formData.append('region_start', String(text.regionStart));
  formData.append('region_end', String(text.regionEnd));
  formData.append('description', text.description);
  formData.append('file_name', text.fileName);
  formData.append('mime', text.file.type || 'text/plain');

  try {
    const response = await fetch('/api/jobs', { method: 'POST', body: formData });
    if (!response.ok) {
      const detail = await response.json();
      throw new Error(detail?.detail || '创建任务失败');
    }
    const data = await response.json();
    text.jobId = data.id;
    subscribeToEvents(text, data.id, handleTextCompletion);
  } catch (error) {
    ElMessage.error(error.message);
  } finally {
    text.busy = false;
  }
};

const submitImageJob = async () => {
  if (!image.file) {
    ElMessage.warning('请先选择图片');
    return;
  }
  if (!image.description) {
    ElMessage.warning('请填写描述内容');
    return;
  }
  image.busy = true;
  const formData = new FormData();
  formData.append('image', image.file);
  formData.append('description', image.description);
  if (image.references.length > 0) {
    for (const item of image.references) {
      formData.append('references', item.file);
    }
  }
  if (imageSelection.width > 0 && imageSelection.height > 0) {
    const scaleX = image.naturalWidth / (image.displayWidth || image.naturalWidth || 1);
    const scaleY = image.naturalHeight / (image.displayHeight || image.naturalHeight || 1);
    formData.append('region_x', String(Math.round(imageSelection.x * scaleX)));
    formData.append('region_y', String(Math.round(imageSelection.y * scaleY)));
    formData.append('region_width', String(Math.round(imageSelection.width * scaleX)));
    formData.append('region_height', String(Math.round(imageSelection.height * scaleY)));
  }
  formData.append('file_name', image.fileName);
  formData.append('mime', image.file.type || 'image/png');

  try {
    const response = await fetch('/api/image/jobs', { method: 'POST', body: formData });
    if (!response.ok) {
      const detail = await response.json();
      throw new Error(detail?.detail || '创建图片任务失败');
    }
    const data = await response.json();
    image.jobId = data.id;
    subscribeToEvents(image, data.id, handleImageCompletion);
  } catch (error) {
    ElMessage.error(error.message);
  } finally {
    image.busy = false;
  }
};

const subscribeToEvents = (target, jobId, onComplete) => {
  if (target.eventSource) {
    target.eventSource.close();
  }
  target.progress = 0;
  target.message = 'queued';
  const eventSource = new EventSource(`/api/jobs/${jobId}/events`);
  target.eventSource = eventSource;
  eventSource.onmessage = (event) => {
    const payload = JSON.parse(event.data);
    if (payload.type === 'progress') {
      target.progress = payload.progress ?? 0;
      target.message = payload.message || payload.status;
    } else if (payload.type === 'failed') {
      target.message = payload.message || 'failed';
      target.progress = 100;
      eventSource.close();
    } else if (payload.type === 'completed') {
      target.progress = 100;
      target.message = 'completed';
      eventSource.close();
      onComplete(jobId);
    }
  };
  eventSource.onerror = () => {
    target.message = '连接中断';
  };
};

const handleTextCompletion = async (jobId) => {
  const response = await fetch(`/api/jobs/${jobId}/result/file`);
  if (!response.ok) {
    ElMessage.error('获取结果失败');
    return;
  }
  const blob = await response.blob();
  if (text.resultUrl) {
    URL.revokeObjectURL(text.resultUrl);
  }
  text.resultUrl = URL.createObjectURL(blob);
  text.resultContent = await blob.text();
};

const handleImageCompletion = async (jobId) => {
  const response = await fetch(`/api/jobs/${jobId}/result/file`);
  if (!response.ok) {
    ElMessage.error('获取结果失败');
    return;
  }
  const blob = await response.blob();
  if (image.resultUrl) {
    URL.revokeObjectURL(image.resultUrl);
  }
  image.resultUrl = URL.createObjectURL(blob);
};

const openUrl = (url) => {
  window.open(url, '_blank');
};

const downloadResult = (url, fileName) => {
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName || 'result';
  link.click();
};

onBeforeUnmount(() => {
  if (text.eventSource) {
    text.eventSource.close();
  }
  if (image.eventSource) {
    image.eventSource.close();
  }
  if (image.previewUrl) {
    URL.revokeObjectURL(image.previewUrl);
  }
  if (image.resultUrl) {
    URL.revokeObjectURL(image.resultUrl);
  }
  clearReferences();
});
</script>

<style scoped>
.tc-hidden {
  display: none;
}
</style>
